import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Dossier(Base):
    __tablename__ = "dossiers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    question: Mapped[str] = mapped_column(Text, default="", server_default="")
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImageAsset(Base):
    __tablename__ = "image_assets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"))
    filename: Mapped[str] = mapped_column(String(200))
    media_type: Mapped[str] = mapped_column(String(40))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    provenance: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_image_assets_dossier_created", "dossier_id", "created_at"),)


class Transcription(Base):
    __tablename__ = "transcriptions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("image_assets.id", ondelete="RESTRICT"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transcriptions.id"))
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30))
    engine: Mapped[str] = mapped_column(String(100))
    model_id: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(40))
    regions: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    warnings: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    input_region: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_transcriptions_image_created", "image_id", "created_at"),)


class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("image_assets.id", ondelete="RESTRICT"))
    route_id: Mapped[str] = mapped_column(String(100))
    language: Mapped[str | None] = mapped_column(String(40))
    region: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    message: Mapped[str] = mapped_column(Text, default="Waiting for the local job runner.")
    transcription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transcriptions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_transcription_jobs_status_created", "status", "created_at"),)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50))
    provenance: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    use_limits: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Edition(Base):
    __tablename__ = "editions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(300))
    language: Mapped[str] = mapped_column(String(40))
    revision: Mapped[str] = mapped_column(String(100))
    collection_memberships: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")


class Passage(Base):
    __tablename__ = "passages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("editions.id", ondelete="RESTRICT"))
    reference: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    search_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    search_vector: Mapped[object] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', coalesce(search_text, ''))", persisted=True)
    )
    embedding: Mapped[object | None] = mapped_column(Vector(1024))
    embedding_model: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (
        Index("ix_passages_edition_reference", "edition_id", "reference", unique=True),
        Index("ix_passages_search", "search_vector", postgresql_using="gin"),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    dossier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatTurn(Base):
    __tablename__ = "chat_turns"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="RESTRICT"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    grounding: Mapped[dict] = mapped_column(JSONB, default=dict)
    connection_id: Mapped[str] = mapped_column(String(100))
    model_id: Mapped[str] = mapped_column(String(200))
    persona_id: Mapped[str] = mapped_column(String(50))
    language: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_chat_turns_conversation_created", "conversation_id", "created_at"),)
