"""Local app lifecycle. Never downloads models or calls inference services."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
RUNTIME = APP / "runtime"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def pg_binary(name: str) -> Path:
    filename = name + (".exe" if os.name == "nt" else "")
    override = os.environ.get("COMPASS_PG_BIN")
    candidates = [Path(override) / filename] if override else []
    candidates += [RUNTIME / "Library" / "bin" / filename, RUNTIME / "bin" / filename]
    found = next((p for p in candidates if p.is_file()), None)
    if found:
        return found
    on_path = shutil.which(name)
    if on_path:
        return Path(on_path)
    raise RuntimeError("PostgreSQL binaries are missing. Run Pinokio Install first.")


def pg_environment() -> dict[str, str]:
    env = os.environ.copy()
    paths = [str(RUNTIME / "Library" / "bin"), str(RUNTIME / "Library" / "lib"), str(RUNTIME / "bin")]
    env["PATH"] = os.pathsep.join(paths + [env.get("PATH", "")])
    return env


def private_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


class ManagedPostgres:
    def __init__(self, data_dir: Path):
        self.root = data_dir.resolve()
        self.cluster = self.root / "postgres"
        self.process: subprocess.Popen | None = None
        self.log = None

    def start(self) -> str:
        import psycopg
        from psycopg.conninfo import make_conninfo
        from sqlalchemy import URL

        self.root.mkdir(parents=True, exist_ok=True)
        state_path = self.root / "managed-postgres.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            state = {"user": "compass", "password": secrets.token_urlsafe(32)}
            private_write(state_path, state)

        if not (self.cluster / "PG_VERSION").exists():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=self.root) as password_file:
                password_file.write(state["password"])
                password_path = Path(password_file.name)
            password_path.chmod(0o600)
            try:
                subprocess.run(
                    [str(pg_binary("initdb")), "-D", str(self.cluster), "-U", state["user"],
                     "--pwfile", str(password_path), "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C"],
                    check=True, env=pg_environment(),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            finally:
                password_path.unlink(missing_ok=True)

        # Only this app's managed cluster is considered. An explicit external DATABASE_URL
        # bypasses this class entirely and is never stopped by the app.
        status = subprocess.run(
            [str(pg_binary("pg_ctl")), "-D", str(self.cluster), "status"],
            check=False, env=pg_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if status.returncode == 0:
            if not state.get("port"):
                raise RuntimeError("Managed cluster is running without a known port; inspect local lifecycle state.")
            port = state["port"]
        else:
            port = free_port()
            state["port"] = port
            private_write(state_path, state)
            self.log = (self.root / "postgres.log").open("a", encoding="utf-8")
            self.process = subprocess.Popen(
                [str(pg_binary("postgres")), "-D", str(self.cluster), "-p", str(port),
                 "-h", "127.0.0.1", "-c", "max_connections=30", "-c", "shared_buffers=64MB"],
                env=pg_environment(), stdout=self.log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

        connection = make_conninfo(host="127.0.0.1", port=port, user=state["user"], password=state["password"], dbname="postgres", connect_timeout=2)
        deadline = time.monotonic() + 30
        while True:
            try:
                with psycopg.connect(connection, autocommit=True) as conn:
                    exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("compass",)).fetchone()
                    if not exists:
                        conn.execute("CREATE DATABASE compass")
                break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline or (self.process and self.process.poll() is not None):
                    raise RuntimeError("Managed PostgreSQL did not become ready; inspect the local postgres.log.") from None
                time.sleep(0.2)
        return URL.create("postgresql+psycopg", username=state["user"], password=state["password"], host="127.0.0.1", port=port, database="compass").render_as_string(hide_password=False)

    def stop(self) -> None:
        try:
            if self.process and self.process.poll() is None:
                try:
                    subprocess.run(
                        [str(pg_binary("pg_ctl")), "-D", str(self.cluster), "-m", "fast", "-w", "stop"],
                        check=True, env=pg_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    self.process.wait(timeout=10)
                except (OSError, RuntimeError, subprocess.SubprocessError):
                    # Fallback is restricted to the child created by this instance.
                    # Never terminate a reused cluster or an external database.
                    if self.process.poll() is None:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                            self.process.wait(timeout=5)
        finally:
            if self.log:
                self.log.close()


def prepare_database(data_dir: Path) -> tuple[str, ManagedPostgres | None]:
    external = os.environ.get("DATABASE_URL")
    managed = None
    try:
        if external:
            url = external
        else:
            managed = ManagedPostgres(data_dir)
            url = managed.start()
        os.environ["DATABASE_URL"] = url
        from alembic import command
        from alembic.config import Config
        config = Config(str(APP / "backend" / "alembic.ini"))
        config.set_main_option("script_location", str(APP / "backend" / "migrations"))
        command.upgrade(config, "head")
        return url, managed
    except BaseException:
        if managed:
            managed.stop()
        raise


def serve(port: int) -> None:
    import uvicorn
    from dotenv import load_dotenv

    from compass.config import Settings

    data_dir = Path(Settings().data_dir)
    load_dotenv(data_dir / "settings.env", override=False)
    data_dir = Path(Settings().data_dir)
    managed = None
    try:
        _, managed = prepare_database(data_dir)
        os.environ.setdefault("COMPASS_FRONTEND_DIR", str(APP / "frontend" / "dist"))
        uvicorn.run("compass.main:app", host="127.0.0.1", port=port, log_level="info", access_log=False)
    finally:
        if managed:
            managed.stop()


def doctor() -> None:
    from compass.config import Settings
    settings = Settings()
    print("Data directory:", settings.data_dir)
    print("Frontend build:", "present" if (APP / "frontend" / "dist" / "index.html").exists() else "missing")
    try:
        print("PostgreSQL:", pg_binary("postgres"))
    except RuntimeError as exc:
        print(str(exc))
    print("Model weights and API credentials are never installed by this command.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["serve", "doctor"])
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    if args.command == "doctor":
        doctor()
    else:
        serve(args.port or int(os.environ.get("PORT", "0")) or free_port())


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        # Deliberately do not print environment, DATABASE_URL or provider responses.
        print(f"Compass startup failed: {type(exc).__name__}. Run doctor and inspect the local lifecycle log.", file=sys.stderr)
        raise SystemExit(1)
