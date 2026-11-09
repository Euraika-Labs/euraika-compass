import hashlib
import io
import time
from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from compass.config import Settings
from compass.errors import APIError
from compass.main import create_app
from compass.models import TranscriptionJob
from compass.routing import require_image_processing

MANUSCRIPT = "fixture-manuscript"
FOLIO = "fixture-folio"
FOLIOS_URL = f"/api/v1/manuscripts/{MANUSCRIPT}/folios"
PREVIEW_URL = f"{FOLIOS_URL}/{FOLIO}/preview"
IMPORT_URL = f"{FOLIOS_URL}/{FOLIO}/import"


@pytest.fixture
def catalog(monkeypatch):
    from compass import manuscript_catalog

    stream = io.BytesIO()
    Image.new("RGB", (64, 32), color="white").save(stream, format="PNG")
    data = stream.getvalue()
    entry = {
        "id": MANUSCRIPT, "title": "Synthetic test fixture", "institution": "Fixture institution",
        "shelfmark": "MS Test. 1", "language": "he", "collections": ["torah", "bible"],
        "catalog_url": "https://example.org/catalog/fixture", "manifest_url": "https://example.org/manifest",
        "date": "Example date", "description": "Fixture for the transport boundary.",
        "attribution": "Fixture attribution", "rights_url": "https://example.org/rights",
        "use_limits": {"preview": True, "local_storage": True, "local_ocr": True, "external_processing": False},
        "default_folio_id": FOLIO,
    }
    folio = {
        "id": FOLIO, "label": "f. 1r", "index": 0, "canvas_id": "https://example.org/canvas/1",
        "width": 640, "height": 320, "source_url": "https://example.org/folio/1",
    }
    fixture = SimpleNamespace(
        manuscript=entry, folio=folio, data=data, media_type="image/png", width=64, height=32,
        sha256=hashlib.sha256(data).hexdigest(), image_url="https://example.org/images/1/full/max/0/default.png",
        manifest_sha256="a" * 64, requests=[], searches=[], check_network_boundary=lambda: None,
    )

    def list_manuscripts(q=None, language=None):
        fixture.searches.append((q, language))
        return [deepcopy(fixture.manuscript)]

    async def list_folios(manuscript_id):
        if manuscript_id != MANUSCRIPT:
            raise APIError(404, "not_found", "Unknown test manuscript.")
        return {"manuscript": deepcopy(fixture.manuscript), "items": [deepcopy(fixture.folio)],
                "manifest_sha256": fixture.manifest_sha256}

    async def fetch_folio(manuscript_id, folio_id, *, preview):
        fixture.requests.append((manuscript_id, folio_id, preview))
        fixture.check_network_boundary()
        if manuscript_id != MANUSCRIPT or folio_id != FOLIO:
            raise APIError(404, "not_found", "Unknown test folio.")
        return fixture

    monkeypatch.setattr(manuscript_catalog, "list_manuscripts", list_manuscripts)
    monkeypatch.setattr(manuscript_catalog, "list_folios", list_folios)
    monkeypatch.setattr(manuscript_catalog, "fetch_folio", fetch_folio)
    return fixture


def test_same_origin_preview_has_no_persistent_copy_and_obeys_source_permissions(tmp_path, catalog):
    application = create_app(Settings(database_url=None, data_dir=tmp_path))
    with TestClient(application, base_url="http://127.0.0.1") as client:
        response = client.get("/api/v1/manuscripts", params={"q": "fixture", "language": "he"})
        assert response.json()["items"][0]["id"] == MANUSCRIPT
        assert catalog.searches == [("fixture", "he")]
        listing = client.get(FOLIOS_URL).json()
        assert listing["manuscript"]["default_folio_id"] == FOLIO
        assert listing["items"][0]["preview_url"] == PREVIEW_URL
        image = client.get(PREVIEW_URL)
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/png"
        assert image.headers["cache-control"] == "private, no-store"
        assert image.content == catalog.data
        assert not (tmp_path / "assets").exists()

        catalog.sha256 = "b" * 64
        assert client.get(PREVIEW_URL).json()["error"]["code"] == "scan_metadata_mismatch"
        catalog.manuscript["use_limits"]["preview"] = False
        assert client.get(FOLIOS_URL).json()["items"][0]["preview_url"] is None
        previous = list(catalog.requests)
        assert client.get(PREVIEW_URL).status_code == 403
        assert catalog.requests == previous


@pytest.mark.postgres
def test_dossier_import_is_idempotent_and_keeps_scan_and_manifest_provenance(postgres_app, catalog):
    client, application, _ = postgres_app

    def no_db_connection_during_fetch():
        assert application.state.database.engine.pool.checkedout() == 0

    catalog.check_network_boundary = no_db_connection_during_fetch
    dossier = client.post("/api/v1/dossiers", json={"title": "Manuscript fixture"}).json()["id"]
    assert client.post(IMPORT_URL, json={"dossier_id": str(uuid4())}).status_code == 404
    assert catalog.requests == []
    assert client.post(IMPORT_URL, json={"dossier_id": dossier, "image_url": "https://example.org/other"}).status_code == 422
    assert catalog.requests == []

    response = client.post(IMPORT_URL, json={"dossier_id": dossier})
    assert response.status_code == 201, response.text
    first = response.json()
    assert first["dossier_id"] == dossier
    assert first["sha256"] == catalog.sha256
    assert first["width"] == 64 and first["height"] == 32
    provenance = first["provenance"]
    assert provenance["manifest_sha256"] == "a" * 64
    assert provenance["canvas_id"] == catalog.folio["canvas_id"]
    assert provenance["canvas_width"] == 640
    assert provenance["image_url"] == catalog.image_url
    assert provenance["image_sha256"] == catalog.sha256
    assert provenance["use_limits"]["external_processing"] is False
    assert provenance["retrieved_at"]
    assert client.get(f"/api/v1/images/{first['id']}/content").content == catalog.data
    repeat = client.post(IMPORT_URL, json={"dossier_id": dossier}).json()
    assert repeat == first

    catalog.manifest_sha256 = "b" * 64
    second = client.post(IMPORT_URL, json={"dossier_id": dossier}).json()
    assert second["id"] != first["id"]
    assert second["sha256"] == first["sha256"]
    attachments = client.get(f"/api/v1/dossiers/{dossier}/images").json()["items"]
    assert {item["provenance"]["manifest_sha256"] for item in attachments} == {"a" * 64, "b" * 64}
    catalog.manuscript["use_limits"]["local_storage"] = False
    previous = list(catalog.requests)
    assert client.post(IMPORT_URL, json={"dossier_id": dossier}).status_code == 403
    assert catalog.requests == previous


@pytest.mark.postgres
def test_manuscript_rights_block_cloud_queue_and_dispatch_while_local_ocr_works(postgres_app, catalog, monkeypatch):
    client, application, registry = postgres_app
    get_route = registry.get_route
    transcribe = registry.transcribe
    dispatched = []

    def route(route_id):
        if route_id == "cloud-test-reader":
            return {**get_route("local-test-reader"), "id": route_id, "provider": "mistral"}
        return get_route(route_id)

    async def tracked_transcribe(route_id, image_path, language):
        dispatched.append(route_id)
        return await transcribe(route_id, image_path, language)

    monkeypatch.setattr(registry, "get_route", route)
    monkeypatch.setattr(registry, "transcribe", tracked_transcribe)
    assert client.patch("/api/v1/chat-settings", json={"local_only": False}).status_code == 200
    assert client.get("/api/v1/models").json()["items"][0]["local"] is True
    dossier = client.post("/api/v1/dossiers", json={"title": "OCR rights fixture"}).json()["id"]
    image = client.post(IMPORT_URL, json={"dossier_id": dossier}).json()
    blocked = client.post("/api/v1/transcription-jobs", json={"image_id": image["id"], "route_id": "cloud-test-reader"})
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "source_cloud_processing_blocked"

    # A queued row still cannot dispatch if the API boundary was bypassed.
    with application.state.database.sessions() as session:
        unsafe = TranscriptionJob(image_id=UUID(image["id"]), route_id="cloud-test-reader")
        session.add(unsafe)
        session.commit()
        unsafe_id = unsafe.id
    client.portal.call(application.state.jobs._run, unsafe_id)
    failed = client.get(f"/api/v1/jobs/{unsafe_id}").json()
    assert failed["status"] == "failed"
    assert "do not permit cloud OCR" in failed["message"]
    assert dispatched == []

    accepted = client.post("/api/v1/transcription-jobs", json={"image_id": image["id"], "route_id": "local-test-reader"})
    assert accepted.status_code == 202, accepted.text
    job_id = accepted.json()["id"]
    for _ in range(50):
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["status"] in {"complete", "failed"}:
            break
        time.sleep(0.02)
    assert job["status"] == "complete", job
    assert dispatched == ["local-test-reader"]


def test_manuscript_processing_requires_explicit_boolean_permission():
    route = {"provider": "mistral", "enabled": True, "configured": True,
             "available": True, "capabilities": ["image_transcription"]}
    require_image_processing(None, route, local_only=False)
    require_image_processing({"use_limits": {"external_processing": True}}, route, local_only=False)
    with pytest.raises(APIError) as error:
        require_image_processing({"use_limits": {"external_processing": "true"}}, route, local_only=False)
    assert error.value.code == "source_cloud_processing_blocked"
    with pytest.raises(APIError) as error:
        require_image_processing({"use_limits": {}}, {**route, "provider": "kraken"}, local_only=False)
    assert error.value.code == "source_local_processing_blocked"
