"""assistant message generation duration"""
from alembic import op
import sqlalchemy as sa

revision = "0005_generation_duration_ms"
down_revision = "0004_work_narration_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assistant_messages", sa.Column("generation_duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("assistant_messages", "generation_duration_ms")
