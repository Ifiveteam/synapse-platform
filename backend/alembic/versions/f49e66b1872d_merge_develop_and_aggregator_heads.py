"""merge develop and aggregator heads

Revision ID: f49e66b1872d
Revises: 019_playlist_last_refreshed_at, 012_add_knowledge_graphs
Create Date: 2026-07-07 16:24:08.063107

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "f49e66b1872d"
down_revision: Union[str, Sequence[str], None] = (
    "019_playlist_last_refreshed_at",
    "012_add_knowledge_graphs",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
