"""user_ideal_persona: 이상향 13축(values_temperament) 컬럼 (Navigator).

Revision ID: 011_navigator_ideal_values
Revises: 010_navigator_persona_label
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "011_navigator_ideal_values"
down_revision: str | Sequence[str] | None = "010_navigator_persona_label"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_ideal_persona",
        sa.Column("values_temperament", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_ideal_persona", "values_temperament")
