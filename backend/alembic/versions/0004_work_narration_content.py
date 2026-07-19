"""saved work narration content"""
from alembic import op
import sqlalchemy as sa

revision = "0004_work_narration_content"
down_revision = "0003_tool_activity_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assistant_messages", sa.Column("work_narration_content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assistant_messages", "work_narration_content")
