from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from compass.errors import APIError


class Database:
    def __init__(self, url: str | None):
        self.engine = (
            create_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=3,
                pool_timeout=5,
                connect_args={"connect_timeout": 5},
                hide_parameters=True,
            )
            if url
            else None
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def ready(self) -> tuple[bool, str]:
        if self.engine is None:
            return False, "PostgreSQL is not configured. Set DATABASE_URL or use the managed launcher."
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                schema = inspect(connection)
                required = {"dossiers", "sources", "editions", "passages", "conversations", "chat_turns", "image_assets"}
                if not required.issubset(schema.get_table_names()) or not any(
                    column["name"] == "provenance" for column in schema.get_columns("image_assets")
                ):
                    return False, "PostgreSQL is reachable; apply Alembic migrations first."
            return True, "PostgreSQL is ready."
        except Exception:
            return False, "PostgreSQL is unavailable. Check its status and migrations."

    def session(self) -> Iterator[Session]:
        if self.engine is None:
            raise APIError(503, "database_unavailable", "PostgreSQL must be configured for this action.")
        with self.sessions() as session:
            yield session

    def dispose(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
