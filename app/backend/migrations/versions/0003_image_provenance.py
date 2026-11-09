"""Store immutable source information with manuscript image attachments."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0003_image_provenance"
down_revision = "0002_grounded_conversations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("image_assets", sa.Column("provenance", pg.JSONB(none_as_null=True), nullable=True))


def downgrade():
    op.drop_column("image_assets", "provenance")
