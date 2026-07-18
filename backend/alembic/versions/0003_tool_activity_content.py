"""saved tool activity content"""
from alembic import op
import sqlalchemy as sa

revision = "0003_tool_activity_content"
down_revision = "0002_saved_reasoning_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assistant_messages", sa.Column("tool_activity_content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assistant_messages", "tool_activity_content")
