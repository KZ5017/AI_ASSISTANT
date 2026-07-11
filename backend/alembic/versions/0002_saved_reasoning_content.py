"""saved reasoning content"""
from alembic import op
import sqlalchemy as sa

revision = "0002_saved_reasoning_content"
down_revision = "0001_assistant_chats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assistant_messages", sa.Column("reasoning_content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assistant_messages", "reasoning_content")
