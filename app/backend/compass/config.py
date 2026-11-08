from pathlib import Path

from platformdirs import user_data_path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COMPASS_", extra="ignore", populate_by_name=True, hide_input_in_errors=True
    )

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    data_dir: Path = Field(
        default_factory=lambda: user_data_path("EuraikaCompass", "EuraikaLabs")
    )
    config_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "config"
    )
    frontend_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "frontend" / "dist"
    )
    local_only: bool = True
    max_upload_bytes: int = 20 * 1024 * 1024
    max_image_pixels: int = 40_000_000

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str | None) -> str | None:
        if not value:
            return None
        url = make_url(value)
        if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL must use PostgreSQL; no SQLite fallback exists")
        return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)

    @field_validator("data_dir", "config_dir", "frontend_dir")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        return value.expanduser().resolve()
