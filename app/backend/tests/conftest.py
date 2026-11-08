import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from compass.adapters.base import AdapterError, TranscriptionResult
from compass.config import Settings
from compass.main import create_app


class ControlledRegistry:
    """A genuine adapter boundary double; never shipped as an application model route."""

    def __init__(self):
        self.enabled = True

    def get_route(self, route_id):
        if route_id != "local-test-reader":
            raise AdapterError("unknown_route", "This route is unknown.")
        return {
            "id": route_id,
            "enabled": self.enabled,
            "configured": True,
            "available": self.enabled,
            "provider": "local",
            "capabilities": ["image_transcription"],
        }

    def list_routes(self):
        return [self.get_route("local-test-reader")]

    async def transcribe(self, route_id, image_path, language=None):
        self.get_route(route_id)
        assert image_path.is_file()
        return TranscriptionResult(
            text="Visible test text [?]",
            engine="test-boundary",
            model_id="local-test-reader",
            regions=[],
            warnings=["This is a deterministic adapter boundary test."],
        )


@pytest.fixture
def postgres_app(tmp_path, monkeypatch):
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL integration tests.")
    normalized = Settings(database_url=raw_url).database_url
    parsed = make_url(normalized)
    if not parsed.database or not parsed.database.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must name a dedicated database ending in _test.")
    schema = "compass_test_" + uuid.uuid4().hex
    owner = create_engine(normalized, hide_parameters=True)
    with owner.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = parsed.update_query_dict({"options": f"-csearch_path={schema},public"}).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", scoped)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    application = None
    try:
        command.upgrade(config, "head")
        registry = ControlledRegistry()
        application = create_app(Settings(database_url=scoped, data_dir=tmp_path), registry=registry)
        with TestClient(application, base_url="http://127.0.0.1") as client:
            yield client, application, registry
    finally:
        if application is not None:
            application.state.database.dispose()
        with owner.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        owner.dispose()
