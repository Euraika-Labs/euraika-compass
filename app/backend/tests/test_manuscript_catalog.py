import hashlib
import io
import json

import httpx
import pytest
from PIL import Image

from compass.errors import APIError
from compass.manuscript_catalog import fetch_folio, list_folios, list_manuscripts

NASH = "https://cudl.lib.cam.ac.uk/iiif/MS-OR-00233"
NASH_SERVICE = "https://images.lib.cam.ac.uk/iiif/MS-OR-00233-000-00001.jp2"
BEZAE = "https://cudl.lib.cam.ac.uk/iiif/MS-NN-00002-00041"
MET = "https://collectionapi.metmuseum.org/public/collection/v1/objects/454661"
MET_IMAGE = "https://images.metmuseum.org/CRDImages/is/original/DP234018.jpg"


@pytest.fixture
def catalog_transport(monkeypatch):
    from compass import manuscript_catalog

    monkeypatch.setattr(manuscript_catalog, "_CACHE", {})
    client = httpx.AsyncClient
    requests, responses = [], {}

    async def handle(request):
        requests.append(request)
        return responses[str(request.url)]

    def create_client(**kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(manuscript_catalog.httpx, "AsyncClient", create_client)
    return requests, responses


def manifest(*, identity=NASH, page=1, service=NASH_SERVICE, rights=None, folio_rights=None):
    data = {
        "@id": identity.replace("https://", "http://", 1),
        "attribution": "Cambridge University Library. CC BY-NC 4.0.",
        "sequences": [
            {
                "canvases": [
                    {
                        "@id": f"{identity.replace('https://', 'http://', 1)}/canvas/{page}",
                        "label": "1r",
                        "width": 3000,
                        "height": 4500,
                        "images": [{"resource": {"service": {"@id": service}}}],
                        **({"rights": folio_rights} if folio_rights is not None else {}),
                    }
                ]
            }
        ],
    }
    if rights is not None:
        data["rights"] = rights
    return httpx.Response(
        200, content=json.dumps(data).encode(), headers={"Content-Type": "application/ld+json"}
    )


def jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (24, 36), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def met_record(*, public_domain=True, image=MET_IMAGE):
    return httpx.Response(
        200,
        json={
            "objectID": 454661,
            "accessionNumber": "2004.87",
            "isPublicDomain": public_domain,
            "objectURL": "https://www.metmuseum.org/art/collection/search/454661",
            "primaryImage": image,
            "primaryImageSmall": image.replace("/original/", "/web-large/"),
        },
    )


def test_catalog_covers_three_scripts_with_separate_permissions(catalog_transport):
    requests, _ = catalog_transport
    items = list_manuscripts()
    assert {item["language"] for item in items} == {"he", "grc", "ar"}
    assert {item["language"] for item in items if item["use_limits"]["local_ocr"]} == {
        "he",
        "grc",
        "ar",
    }
    assert list_manuscripts("Kennicott", "hebrew")[0]["id"] == "bodleian-kennicott-1"
    assert list_manuscripts("Codex", "arabic") == []
    assert list_manuscripts("naskh", "arabic")[0]["id"] == "met-mamluk-quran"
    assert [item["id"] for item in items if item["use_limits"]["external_processing"]] == [
        "met-tashkent-quran",
        "met-mamluk-quran",
    ]
    assert requests == []


@pytest.mark.asyncio
async def test_cambridge_preview_and_save_use_exact_jpeg_bytes_and_provenance(catalog_transport):
    requests, responses = catalog_transport
    source = manifest()
    data = jpeg()
    preview_url = NASH_SERVICE + "/full/1200,/0/default.jpg"
    save_url = NASH_SERVICE + "/full/2500,/0/default.jpg"
    responses.update(
        {
            NASH: source,
            preview_url: httpx.Response(200, content=data, headers={"Content-Type": "image/jpeg"}),
            save_url: httpx.Response(200, content=data, headers={"Content-Type": "image/jpeg"}),
        }
    )
    result = await list_folios("cambridge-nash")
    assert result["manifest_sha256"] == hashlib.sha256(source.content).hexdigest()
    assert result["manuscript"]["default_folio_id"] == "p0001"
    assert result["items"][0]["source_url"] == "https://cudl.lib.cam.ac.uk/view/MS-OR-00233/1"
    preview = await fetch_folio("cambridge-nash", "p0001", preview=True)
    saved = await fetch_folio("cambridge-nash", "p0001", preview=False)
    assert (preview.image_url, saved.image_url) == (preview_url, save_url)
    assert [str(request.url) for request in requests] == [NASH, preview_url, NASH, save_url]
    assert all(
        "authorization" not in request.headers and "cookie" not in request.headers
        for request in requests
    )
    assert saved.data == data and saved.sha256 == hashlib.sha256(data).hexdigest()
    assert (saved.width, saved.height, saved.media_type) == (24, 36, "image/jpeg")
    assert saved.manuscript["use_limits"] == {
        "preview": True,
        "local_storage": True,
        "local_ocr": True,
        "external_processing": False,
    }


@pytest.mark.asyncio
async def test_bezae_second_volume_reset_keeps_canvas_identity(catalog_transport):
    _, responses = catalog_transport
    responses[BEZAE] = manifest(
        identity=BEZAE,
        page=328,
        service="https://images.lib.cam.ac.uk/iiif/MS-NN-00002-00041-002-00001.jp2",
    )
    result = await list_folios("cambridge-bezae")
    assert [item["id"] for item in result["items"]] == ["p0328"]
    assert result["items"][0]["source_url"].endswith("/MS-NN-00002-00041/328")


@pytest.mark.parametrize(
    "service",
    [
        "http://127.0.0.1/private",
        "https://images.lib.cam.ac.uk.attacker.example/iiif/object.jp2",
        NASH_SERVICE.replace("https://", "http://"),
        NASH_SERVICE + "?override=true",
        NASH_SERVICE.replace("00001.jp2", "00002.jp2"),
        NASH_SERVICE.replace("MS-OR-00233", "MS-NN-00002-00041"),
    ],
)
@pytest.mark.asyncio
async def test_manifest_cannot_redirect_or_reassign_folio_image_service(catalog_transport, service):
    requests, responses = catalog_transport
    responses[NASH] = manifest(service=service)
    with pytest.raises(APIError) as error:
        await fetch_folio("cambridge-nash", "p0001", preview=True)
    assert error.value.code == "manuscript_folios_unavailable"
    assert [str(request.url) for request in requests] == [NASH]


@pytest.mark.asyncio
async def test_vatican_save_policy_and_unknown_ids_block_before_request(catalog_transport):
    requests, _ = catalog_transport
    with pytest.raises(APIError) as save:
        await fetch_folio("vatican-vat-gr-1209", "p0050", preview=False)
    assert save.value.status == 403 and save.value.code == "manuscript_save_restricted"
    with pytest.raises(APIError) as unknown:
        await fetch_folio("https://example.org/manuscript", "p0001", preview=True)
    assert unknown.value.code == "unknown_manuscript"
    with pytest.raises(APIError) as invalid:
        await fetch_folio("cambridge-nash", "../../private", preview=True)
    assert invalid.value.code == "unknown_manuscript_folio"
    assert requests == []


@pytest.mark.parametrize("restriction", ["manifest", "folio"])
@pytest.mark.asyncio
async def test_save_rechecks_current_license_before_image_download(catalog_transport, restriction):
    requests, responses = catalog_transport
    responses[NASH] = manifest()
    initial = await list_folios("cambridge-nash")
    assert initial["items"][0]["use_limits"]["local_storage"] is True
    kwargs = {
        "rights"
        if restriction == "manifest"
        else "folio_rights": "https://rightsstatements.org/vocab/InC/1.0/"
    }
    responses[NASH] = manifest(**kwargs)
    with pytest.raises(APIError) as error:
        await fetch_folio("cambridge-nash", "p0001", preview=False)
    assert error.value.status == 403 and error.value.code == "manuscript_save_restricted"
    assert [str(request.url) for request in requests] == [NASH, NASH]
    current = await list_folios("cambridge-nash")
    assert current["items"][0]["use_limits"]["local_storage"] is False


@pytest.mark.parametrize("public_domain", [False, "true", None])
@pytest.mark.asyncio
async def test_met_requires_affirmative_open_access_record(catalog_transport, public_domain):
    requests, responses = catalog_transport
    responses[MET] = met_record(public_domain=public_domain)
    with pytest.raises(APIError) as error:
        await fetch_folio("met-tashkent-quran", "primary", preview=False)
    assert error.value.code == "manuscript_access_restricted"
    assert [str(request.url) for request in requests] == [MET]


@pytest.mark.asyncio
async def test_met_source_returns_preserved_bytes_with_open_access_permissions(catalog_transport):
    requests, responses = catalog_transport
    data = jpeg()
    responses.update(
        {
            MET: met_record(),
            MET_IMAGE: httpx.Response(200, content=data, headers={"Content-Type": "image/jpeg"}),
        }
    )
    image = await fetch_folio("met-tashkent-quran", "primary", preview=False)
    assert image.data == data and image.manuscript["use_limits"]["external_processing"] is True
    assert [str(request.url) for request in requests] == [MET, MET_IMAGE]


@pytest.mark.asyncio
async def test_preview_rejects_redirects_and_invalid_raster(catalog_transport):
    requests, responses = catalog_transport
    preview_url = NASH_SERVICE + "/full/1200,/0/default.jpg"
    responses[NASH] = manifest()
    responses[preview_url] = httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})
    with pytest.raises(APIError) as redirect:
        await fetch_folio("cambridge-nash", "p0001", preview=True)
    assert redirect.value.code == "manuscript_unavailable"
    assert [str(request.url) for request in requests] == [NASH, preview_url]
    responses[preview_url] = httpx.Response(
        200, content=b"<html>login</html>", headers={"Content-Type": "image/jpeg"}
    )
    with pytest.raises(APIError) as invalid:
        await fetch_folio("cambridge-nash", "p0001", preview=True)
    assert invalid.value.code == "invalid_manuscript_image"


@pytest.mark.asyncio
async def test_image_byte_cap_applies_even_with_incorrect_content_length(
    catalog_transport, monkeypatch
):
    _, responses = catalog_transport
    monkeypatch.setattr("compass.manuscript_catalog._MAX_IMAGE_BYTES", 128)
    responses[NASH] = manifest()
    responses[NASH_SERVICE + "/full/1200,/0/default.jpg"] = httpx.Response(
        200,
        content=jpeg(),
        headers={"Content-Type": "image/jpeg", "Content-Length": "1"},
    )
    with pytest.raises(APIError) as error:
        await fetch_folio("cambridge-nash", "p0001", preview=True)
    assert error.value.status == 413 and error.value.code == "manuscript_resource_too_large"
