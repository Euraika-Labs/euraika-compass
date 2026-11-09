from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DossierCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    question: Annotated[str, Field(max_length=10_000)] = ""

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A title is required")
        return value.strip()


class DossierPatch(BaseModel):
    expected_revision: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    question: Annotated[str, Field(max_length=10_000)] | None = None
    notes: Annotated[str, Field(max_length=200_000)] | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("A title is required")
        return value.strip() if value else value


class DossierRead(ReadModel):
    id: UUID
    title: str
    question: str
    notes: str
    revision: int
    created_at: datetime
    updated_at: datetime


class ImageRead(ReadModel):
    id: UUID
    dossier_id: UUID
    filename: str
    media_type: str
    width: int
    height: int
    sha256: str
    created_at: datetime
    provenance: dict | None = None


class Region(BaseModel):
    x: Annotated[int, Field(ge=0)]
    y: Annotated[int, Field(ge=0)]
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]


class TranscriptionRequest(BaseModel):
    image_id: UUID
    route_id: Annotated[str, Field(min_length=1, max_length=100)]
    language: Annotated[str, Field(max_length=40)] | None = None
    region: Region | None = None


class ManualTranscription(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=200_000)]
    language: Annotated[str, Field(max_length=40)] | None = None


class RevisionCreate(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=200_000)]


class TranscriptionRead(ReadModel):
    id: UUID
    image_id: UUID
    parent_id: UUID | None
    text: str
    kind: str
    engine: str
    model_id: str | None
    language: str | None
    regions: list[dict]
    warnings: list[str]
    input_region: dict | None
    created_at: datetime


class JobRead(ReadModel):
    id: UUID
    image_id: UUID
    route_id: str
    status: str
    message: str
    created_at: datetime
    updated_at: datetime
    transcription_id: UUID | None


class RoutePatch(BaseModel):
    enabled: bool
