"""Run tests against an isolated managed PostgreSQL test database, never SQLite."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
from manage import APP, ManagedPostgres
from platformdirs import user_cache_path
from sqlalchemy.engine import make_url


def main() -> int:
    existing = os.environ.get("TEST_DATABASE_URL")
    if existing:
        if not (make_url(existing).database or "").endswith("_test"):
            raise RuntimeError("Use a dedicated database with a name ending in _test.")
        return subprocess.run([sys.executable, "-m", "pytest"], cwd=APP / "backend", check=False).returncode
    root = Path(os.environ.get("COMPASS_TEST_DATA_DIR", user_cache_path("EuraikaCompass", "EuraikaLabs") / "postgres-tests"))
    managed = ManagedPostgres(root)
    try:
        url = make_url(managed.start())
        with psycopg.connect(url.set(drivername="postgresql").render_as_string(hide_password=False), autocommit=True) as conn:
            if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("compass_test",)).fetchone():
                conn.execute("CREATE DATABASE compass_test")
        env = os.environ.copy()
        env["TEST_DATABASE_URL"] = url.set(database="compass_test").render_as_string(hide_password=False)
        env["COMPASS_LOCAL_ONLY"] = "true"
        return subprocess.run([sys.executable, "-m", "pytest"], cwd=APP / "backend", env=env, check=False).returncode
    finally:
        managed.stop()


if __name__ == "__main__":
    raise SystemExit(main())
