"""Saved conversations and immutable source snapshots for each answer."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002_grounded_conversations"
down_revision = "0001_personal_workbench"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("dossier_id", pg.UUID(as_uuid=True), sa.ForeignKey("dossiers.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "chat_turns",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", pg.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations", pg.JSONB(), nullable=False),
        sa.Column("warnings", pg.JSONB(), nullable=False),
        sa.Column("grounding", pg.JSONB(), nullable=False),
        sa.Column("connection_id", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("persona_id", sa.String(50), nullable=False),
        sa.Column("language", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_turns_conversation_created", "chat_turns", ["conversation_id", "created_at"])


def downgrade():
    op.drop_index("ix_chat_turns_conversation_created", table_name="chat_turns")
    op.drop_table("chat_turns")
    op.drop_table("conversations")
