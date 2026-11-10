from fastapi.testclient import TestClient

from compass.config import Settings
from compass.main import create_app


class EmptyRegistry:
    def list_routes(self):
        return []


def client(tmp_path):
    return TestClient(
        create_app(Settings(database_url=None, data_dir=tmp_path), registry=EmptyRegistry()),
        base_url="http://127.0.0.1",
    )


def test_shell_without_database_is_honest_and_has_no_sqlite_fallback(tmp_path):
    with client(tmp_path) as api:
        health = api.get("/api/v1/health").json()
        assert health["status"] == "degraded"
        assert not health["database"]["ready"]
        assert not health["features"]["grounded_chat"]
        response = api.post("/api/v1/dossiers", json={"title": "My research"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"
        assert api.get("/api/v1/models").json() == {"items": []}


def test_cross_origin_and_dns_rebinding_host_are_rejected(tmp_path):
    with client(tmp_path) as api:
        response = api.post("/api/v1/dossiers", headers={"origin": "https://example.com"}, json={"title": "x"})
        assert response.status_code == 403
        assert api.get("/api/v1/health", headers={"host": "evil.example"}).status_code == 400
        assert api.get("/api/v1/health", headers={"origin": "http://localhost:5173"}).status_code == 200


def test_generation_is_explicitly_unimplemented_not_a_fake_answer(tmp_path):
    with client(tmp_path) as api:
        response = api.post("/api/v1/research-runs", json={"message": "What is written here?"})
        assert response.status_code == 501
        assert response.json()["error"]["code"] == "not_implemented"


def test_chat_requires_storage_and_a_selected_connection(tmp_path):
    with client(tmp_path) as api:
        response = api.post("/api/v1/chat", json={"message": "What is written here?", "connection_id": "missing"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"


def test_persona_catalog_keeps_chat_profiles_and_advertises_roundtable_specialists(tmp_path):
    with client(tmp_path) as api:
        profiles = api.get("/api/v1/personas").json()["items"]
        assert {item["id"] for item in profiles if not item.get("roundtable_only")} == {
            "supportive", "wisdom", "textual", "comparative", "critical",
        }
        assert {item["id"] for item in profiles if item.get("roundtable_only")} == {
            "historical", "philology", "manuscripts", "literary", "reception", "source_verification",
        }
        assert len({item["description"] for item in profiles}) == len(profiles) == 11
        specialist = api.post("/api/v1/chat", json={
            "message": "What does this wording mean?", "connection_id": "unused", "persona_id": "philology",
        })
        assert specialist.status_code == 422


def test_api_fallback_does_not_serve_index_as_success(tmp_path):
    with client(tmp_path) as api:
        assert api.get("/api/v1/unknown").status_code == 404


def test_invalid_image_id_is_rejected_before_any_database_query(tmp_path):
    application = create_app(
        Settings(database_url="postgresql://test@127.0.0.1:1/compass_test", data_dir=tmp_path),
        registry=EmptyRegistry(),
    )
    with TestClient(application, base_url="http://127.0.0.1") as api:
        assert api.get("/api/v1/images/not-a-uuid/content").status_code == 422


def test_upload_request_limit_applies_before_database_and_to_chunked_body(tmp_path):
    application = create_app(
        Settings(database_url=None, data_dir=tmp_path, max_upload_bytes=1024),
        registry=EmptyRegistry(),
    )
    with TestClient(application, base_url="http://127.0.0.1") as api:
        response = api.post("/api/v1/images", content=b"x" * 100_000)
        assert response.status_code == 413
        boundary = "compass-test-boundary"

        def body():
            yield f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="x.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
            for _part in range(100):
                yield b"x" * 1024
            yield f'\r\n--{boundary}--\r\n'.encode()

        response = api.post(
            "/api/v1/images",
            content=body(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        assert response.status_code == 413
