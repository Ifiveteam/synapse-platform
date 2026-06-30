"""merge drive_folder + scrap_embeddings

Revision ID: 006_merge_heads
Revises: 004_scrap_embeddings, 005_analysis_stage
Create Date: 2026-06-30 16:51:59.385737

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "006_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "004_scrap_embeddings",
    "005_analysis_stage",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
