"""Initial PostgreSQL workbench, source and image-reading schema."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

revision = "0001_personal_workbench"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "dossiers",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("question", sa.Text(), server_default="", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "image_assets",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("dossier_id", pg.UUID(as_uuid=True), sa.ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("media_type", sa.String(40), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_image_assets_sha256", "image_assets", ["sha256"])
    op.create_index("ix_image_assets_dossier_created", "image_assets", ["dossier_id", "created_at"])
    op.create_table(
        "transcriptions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_id", pg.UUID(as_uuid=True), sa.ForeignKey("image_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("parent_id", pg.UUID(as_uuid=True), sa.ForeignKey("transcriptions.id")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("engine", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(200)),
        sa.Column("language", sa.String(40)),
        sa.Column("regions", pg.JSONB(), server_default="[]", nullable=False),
        sa.Column("warnings", pg.JSONB(), server_default="[]", nullable=False),
        sa.Column("input_region", pg.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transcriptions_image_created", "transcriptions", ["image_id", "created_at"])
    op.create_table(
        "transcription_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_id", pg.UUID(as_uuid=True), sa.ForeignKey("image_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("route_id", sa.String(100), nullable=False),
        sa.Column("language", sa.String(40)),
        sa.Column("region", pg.JSONB()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("transcription_id", pg.UUID(as_uuid=True), sa.ForeignKey("transcriptions.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transcription_jobs_status_created", "transcription_jobs", ["status", "created_at"])
    op.create_table(
        "sources",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("provenance", pg.JSONB(), server_default="{}", nullable=False),
        sa.Column("use_limits", pg.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "editions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("language", sa.String(40), nullable=False),
        sa.Column("revision", sa.String(100), nullable=False),
        sa.Column("collection_memberships", pg.JSONB(), server_default="[]", nullable=False),
    )
    op.create_table(
        "passages",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("edition_id", pg.UUID(as_uuid=True), sa.ForeignKey("editions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), server_default="", nullable=False),
        sa.Column("search_vector", pg.TSVECTOR(), sa.Computed("to_tsvector('simple', coalesce(search_text, ''))", persisted=True), nullable=False),
        sa.Column("embedding", Vector(1024)),
        sa.Column("embedding_model", sa.String(200)),
    )
    op.create_index("ix_passages_edition_reference", "passages", ["edition_id", "reference"], unique=True)
    op.create_index("ix_passages_search", "passages", ["search_vector"], postgresql_using="gin")


def downgrade():
    for name in ["passages", "editions", "sources", "transcription_jobs", "transcriptions", "image_assets", "dossiers"]:
        op.drop_table(name)
    # The vector extension may be used by other schemas; do not drop it implicitly.
