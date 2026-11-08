import io
import time

import pytest
from PIL import Image
from sqlalchemy import text

pytestmark = pytest.mark.postgres


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(output, format="PNG")
    return output.getvalue()


def create_image(client):
    dossier = client.post("/api/v1/dossiers", json={"title": "A real dossier", "question": "Read this photo"}).json()
    data = image_bytes()
    response = client.post(
        "/api/v1/images",
        data={"dossier_id": dossier["id"]},
        files={"file": ("../../original.png", data, "image/png")},
    )
    assert response.status_code == 201
    return dossier, response.json(), data


def test_dossier_conflict_image_original_and_immutable_readings(postgres_app):
    client, app, _registry = postgres_app
    assert client.get("/api/v1/health").json()["database"]["ready"]
    dossier, image, original = create_image(client)
    assert image["filename"] == "original.png"
    assert (image["width"], image["height"]) == (40, 30)
    assert client.get(f"/api/v1/images/{image['id']}/content").content == original
    updated = client.patch(
        f"/api/v1/dossiers/{dossier['id']}", json={"notes": "My own observation", "expected_revision": 1}
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    conflict = client.patch(
        f"/api/v1/dossiers/{dossier['id']}", json={"notes": "stale", "expected_revision": 1}
    )
    assert conflict.status_code == 409
    assert client.get(f"/api/v1/dossiers/{dossier['id']}").json()["notes"] == "My own observation"
    reading = client.post(
        f"/api/v1/images/{image['id']}/transcriptions", json={"text": "אבג [?]", "language": "he"}
    )
    assert reading.status_code == 201
    assert reading.json()["parent_id"] is None
    revised = client.post(
        f"/api/v1/transcriptions/{reading.json()['id']}/revisions", json={"text": "אבגד"}
    )
    assert revised.status_code == 201
    assert revised.json()["parent_id"] == reading.json()["id"]
    all_readings = client.get(f"/api/v1/images/{image['id']}/transcriptions").json()["items"]
    assert [item["text"] for item in all_readings] == ["אבג [?]", "אבגד"]
    assert client.get(f"/api/v1/images/{image['id']}/content").content == original
    # A second import refers to the same immutable bytes rather than a new disk copy.
    again = client.post("/api/v1/images", data={"dossier_id": dossier["id"]}, files={"file": ("copy.png", original, "image/png")})
    assert again.status_code == 201
    assert again.json()["sha256"] == image["sha256"]
    assert len([path for path in app.state.blobs.root.rglob("*") if path.is_file()]) == 1


def test_job_records_adapter_proposal_and_image_scope(postgres_app):
    client, _app, _registry = postgres_app
    _dossier, image, _original = create_image(client)
    response = client.post(
        "/api/v1/transcription-jobs",
        json={"image_id": image["id"], "route_id": "local-test-reader", "region": {"x": 2, "y": 3, "width": 20, "height": 10}},
    )
    assert response.status_code == 202
    job = response.json()
    for _attempt in range(100):
        job = client.get(f"/api/v1/jobs/{job['id']}").json()
        if job["status"] in {"complete", "failed"}:
            break
        time.sleep(0.02)
    assert job["status"] == "complete"
    readings = client.get(f"/api/v1/images/{image['id']}/transcriptions").json()["items"]
    assert len(readings) == 1
    assert readings[0]["kind"] == "automatic"
    assert readings[0]["text"] == "Visible test text [?]"
    assert readings[0]["input_region"] == {"x": 2, "y": 3, "width": 20, "height": 10}
    assert "not reviewed" in readings[0]["warnings"][0]
    assert "event: job" in client.get(f"/api/v1/jobs/{job['id']}/events").text


def test_real_pgvector_and_full_text_schema(postgres_app):
    _client, app, _registry = postgres_app
    with app.state.database.engine.connect() as connection:
        assert connection.execute(text("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector")).scalar() == 1
        assert connection.execute(text("SELECT to_tsvector('simple','alpha beta') @@ plainto_tsquery('simple','alpha')")).scalar()


def test_unavailable_route_and_outside_region_do_not_create_fake_jobs(postgres_app):
    client, app, registry = postgres_app
    _dossier, image, _original = create_image(client)
    registry.enabled = False
    response = client.post("/api/v1/transcription-jobs", json={"image_id": image["id"], "route_id": "local-test-reader"})
    assert response.status_code == 409
    registry.enabled = True
    response = client.post(
        "/api/v1/transcription-jobs",
        json={"image_id": image["id"], "route_id": "local-test-reader", "region": {"x": 39, "y": 0, "width": 10, "height": 1}},
    )
    assert response.status_code == 422
    with app.state.database.engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM transcription_jobs")).scalar() == 0
