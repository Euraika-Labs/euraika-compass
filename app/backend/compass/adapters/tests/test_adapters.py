import asyncio
import base64
import io
import json
import runpy
import sys
from pathlib import Path

import httpx
import pytest
from PIL import Image

from compass.adapters.base import AdapterError
from compass.adapters.http_readers import (
    image_data_url,
    local_base_url,
    transcribe_kraken_http,
    transcribe_mistral,
    transcribe_qwen,
)
from compass.adapters.kraken_reader import parse_alto
from compass.adapters.registry import ModelRegistry
from compass.adapters.routing import select_route

CONFIG = Path(__file__).resolve().parents[4] / "config" / "models.json"


def image_fixture(path: Path, image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (3, 2), color="white").save(output, format=image_format)
    data = output.getvalue()
    path.write_bytes(data)
    return data


def test_hash_named_original_uses_actual_png_bytes_without_changing_them(tmp_path):
    original = tmp_path / ("a" * 64)
    expected = image_fixture(original)
    encoded = image_data_url(original)
    header, payload = encoded.split(",", 1)
    assert header == "data:image/png;base64"
    assert base64.b64decode(payload) == expected == original.read_bytes()


def test_misleading_filename_cannot_change_actual_jpeg_media_type(tmp_path):
    original = tmp_path / "misleading.png"
    expected = image_fixture(original, "JPEG")
    header, payload = image_data_url(original).split(",", 1)
    assert header == "data:image/jpeg;base64"
    assert base64.b64decode(payload) == expected == original.read_bytes()


def test_catalog_discovery_does_not_activate_services_or_expose_secrets():
    registry = ModelRegistry(CONFIG, environ={"MISTRAL_API_KEY": "private-test-key"})
    routes = registry.list_routes()
    assert len(routes) >= 7
    assert registry.get_route("kraken-medium")["available"] is False
    cloud = registry.get_route("mistral-ocr")
    assert cloud["configured"] is True
    assert cloud["enabled"] is False
    assert cloud["available"] is False
    assert "private-test-key" not in json.dumps(routes)
    assert "api_key" not in cloud


def test_enabled_choice_is_persisted_without_credentials(tmp_path):
    state = tmp_path / "settings" / "routes.json"
    registry = ModelRegistry(CONFIG, state, environ={"MISTRAL_API_KEY": "not-for-disk"})
    registry.set_enabled("mistral-ocr", True)
    assert "not-for-disk" not in state.read_text()
    loaded = ModelRegistry(CONFIG, state, environ={})
    assert loaded.get_route("mistral-ocr")["enabled"] is True
    assert loaded.get_route("mistral-ocr")["available"] is False
    assert json.loads(state.read_text()) == {"routes": {"mistral-ocr": {"enabled": True}}}


def test_local_only_blocks_even_an_enabled_key_configured_cloud_route(tmp_path):
    registry = ModelRegistry(CONFIG, environ={"MISTRAL_API_KEY": "test"})
    registry.set_enabled("mistral-ocr", True)
    assert registry.get_route("mistral-ocr")["status"] == "local_only"
    with pytest.raises(AdapterError) as error:
        asyncio.run(registry.transcribe("mistral-ocr", tmp_path / "not-sent.png"))
    assert error.value.code == "local_only"


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/v1",
        "http://127.0.0.1.attacker.example/v1",
        "http://secret@localhost:8080/v1",
        "http://localhost/v1?key=secret",
        "file:///tmp/model",
    ],
)
def test_local_endpoint_cannot_be_an_external_or_credential_url(value):
    with pytest.raises(AdapterError) as error:
        local_base_url(value)
    assert error.value.code == "invalid_local_endpoint"


def test_unknown_route_and_planned_adapter_have_explicit_errors():
    registry = ModelRegistry(CONFIG, environ={"COMPASS_LOCAL_ONLY": "false"})
    with pytest.raises(AdapterError) as error:
        registry.get_route("not-in-the-catalog")
    assert error.value.code == "unknown_route"
    route = registry.set_enabled("openai-astra-vision", True)
    assert route["status"] == "not_implemented"
    assert route["available"] is False


def test_pin_blocks_visible_or_invisible_automatic_replacement():
    routes = [
        {
            "id": "first",
            "enabled": True,
            "available": False,
            "provider": "kraken",
            "capabilities": ["image_transcription"],
        },
        {
            "id": "second",
            "enabled": True,
            "available": True,
            "provider": "llama.cpp",
            "capabilities": ["image_transcription"],
        },
    ]
    with pytest.raises(AdapterError) as error:
        select_route(routes, "first", pinned=True, fallback_ids=("second",))
    assert error.value.code == "pinned_route_unavailable"
    assert select_route(routes, "first", pinned=False, fallback_ids=("second",)) == "second"
    assert select_route(routes, "second", pinned=True) == "second"


def test_fallback_cannot_activate_a_remote_or_unapproved_model():
    routes = [
        {
            "id": "first",
            "enabled": True,
            "available": False,
            "provider": "kraken",
            "capabilities": ["image_transcription"],
        },
        {
            "id": "remote",
            "enabled": True,
            "available": True,
            "provider": "mistral",
            "capabilities": ["image_transcription"],
        },
    ]
    with pytest.raises(AdapterError):
        select_route(routes, "first", pinned=False, fallback_ids=("remote",), local_only=True)
    with pytest.raises(AdapterError):
        select_route(
            routes,
            "first",
            pinned=False,
            fallback_ids=(),
            local_only=False,
            external_processing_allowed=True,
        )
    assert (
        select_route(
            routes,
            "first",
            pinned=False,
            fallback_ids=("remote",),
            local_only=False,
            external_processing_allowed=True,
        )
        == "remote"
    )


def test_alto_keeps_observed_lines_and_real_boxes_without_fake_confidence():
    reading = parse_alto(
        """<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#"><Layout><Page>
      <TextLine HPOS="12" VPOS="30" WIDTH="120" HEIGHT="20"><String CONTENT="alpha"/><SP/><String CONTENT="[?]"/></TextLine>
      <TextLine><String CONTENT="beta"/></TextLine>
    </Page></Layout></alto>""",
        "test-model",
    )
    assert reading.text == "alpha [?]\nbeta"
    assert len(reading.regions) == 1
    assert reading.regions[0]["bbox"] == {"x": 12, "y": 30, "width": 120, "height": 20}
    assert "confidence" not in reading.regions[0]
    assert reading.warnings


def test_alto_rejects_external_entity_markup():
    with pytest.raises(AdapterError):
        parse_alto('<!DOCTYPE alto [<!ENTITY secret SYSTEM "file:///private">]><alto/>', "test")


def test_qwen_request_uses_selected_pixels_and_returns_no_invented_boxes(tmp_path):
    image = tmp_path / "crop.png"
    image_fixture(image)
    seen = []

    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        assert request.url.host == "127.0.0.1"
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "alpha [?]"}}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await transcribe_qwen(
                image, "Qwen3.8-27B", "http://127.0.0.1:8081/v1", client=client
            )

    result = asyncio.run(run())
    assert result.text == "alpha [?]"
    assert result.regions == []
    content = seen[0]["messages"][0]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert "Do not fill gaps" in content[0]["text"]


def test_mistral_preserves_provider_block_geometry_and_safe_access_error(tmp_path):
    image = tmp_path / "crop.png"
    image_fixture(image)

    def respond(request):
        assert request.headers["Authorization"] == "Bearer private-test-key"
        assert json.loads(request.content)["include_blocks"] is True
        return httpx.Response(
            200,
            json={
                "pages": [
                    {
                        "markdown": "reading",
                        "dimensions": {"width": 1000, "height": 500},
                        "blocks": [
                            {
                                "type": "text",
                                "content": "reading",
                                "top_left_x": 10,
                                "top_left_y": 20,
                                "bottom_right_x": 50,
                                "bottom_right_y": 40,
                            }
                        ],
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await transcribe_mistral(
                image, "mistral-ocr-4-1", "private-test-key", client=client
            )

    result = asyncio.run(run())
    assert result.text == "reading"
    assert result.regions[0]["coordinate_system"] == "provider_page_pixels"
    assert result.regions[0]["page_width"] == 1000
    assert "confidence" not in result.regions[0]

    async def denied():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, text="private-test-key")
            )
        ) as client:
            return await transcribe_mistral(
                image, "mistral-ocr-4-1", "private-test-key", client=client
            )

    with pytest.raises(AdapterError) as error:
        asyncio.run(denied())
    assert error.value.code == "provider_access_denied"
    assert "private-test-key" not in str(error.value)


def test_http_htr_bridge_sends_image_bytes_and_profile_not_native_paths(tmp_path):
    image = tmp_path / "crop.png"
    image_fixture(image)
    seen = []

    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        assert request.url.path == "/transcribe"
        return httpx.Response(
            200,
            json={
                "text": "reading [?]",
                "engine": "kraken",
                "model_id": "test-model",
                "regions": [],
                "warnings": [],
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await transcribe_kraken_http(
                image, "test-model", "kraken-medium", "http://127.0.0.1:8766", client=client
            )

    result = asyncio.run(run())
    assert result.text == "reading [?]"
    assert set(seen[0]) == {"profile_id", "image_data", "language"}
    assert str(image) not in json.dumps(seen)


def test_htr_bridge_rejects_external_endpoint_and_does_not_require_windows_weight_paths():
    configured = ModelRegistry(
        CONFIG, environ={"COMPASS_KRAKEN_WORKER_URL": "http://127.0.0.1:8766"}
    )
    assert configured.get_route("kraken-medium")["configured"] is True
    invalid = ModelRegistry(CONFIG, environ={"COMPASS_KRAKEN_WORKER_URL": "https://remote.example"})
    assert invalid.get_route("kraken-medium")["available"] is False


def test_sidecar_refuses_external_origin_unknown_fields_and_invalid_images(tmp_path):
    from fastapi.testclient import TestClient

    worker = CONFIG.parents[0].parent / "workers" / "kraken" / "serve.py"
    create_app = runpy.run_path(str(worker))["create_app"]
    model = tmp_path / "weights.safetensors"
    model.write_bytes(b"not-loaded-test-fixture")
    values = {
        "COMPASS_KRAKEN_EXECUTABLE": sys.executable,
        "COMPASS_KRAKEN_MEDIUM_MODEL": str(model),
        "COMPASS_KRAKEN_SEGMENTATION_MODEL": str(model),
    }
    with TestClient(create_app(values)) as client:
        assert client.get("/health").status_code == 200
        payload = {
            "profile_id": "kraken-medium",
            "image_data": "data:image/png;base64,bm90LWEtcG5n",
        }
        assert (
            client.post(
                "/transcribe", json=payload, headers={"Origin": "https://unrelated.example"}
            ).status_code
            == 403
        )
        assert (
            client.post("/transcribe", json={**payload, "model_path": "arbitrary"}).status_code
            == 422
        )
        invalid = client.post("/transcribe", json=payload)
        assert invalid.status_code == 422
        assert "bm90LWEtcG5n" not in invalid.text
        assert (
            client.post(
                "/transcribe", json=payload, headers={"Content-Length": str(38 * 1024 * 1024)}
            ).status_code
            == 413
        )
        assert (
            client.post("/transcribe", json={**payload, "profile_id": "not-cataloged"}).status_code
            == 409
        )
