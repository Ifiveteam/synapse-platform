"""Add source_profile_history_id FK to user_ideal_persona (Navigator).

Revision ID: 007_navigator_ideal_source
Revises: 006_extension_auth
Create Date: 2026-06-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "007_navigator_ideal_source"
down_revision: str | Sequence[str] | None = "006_extension_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_ideal_persona",
        sa.Column(
            "source_profile_history_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_uip_source_profile_history",
        "user_ideal_persona",
        "user_profile_history",
        ["source_profile_history_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_uip_source_profile_history",
        "user_ideal_persona",
        type_="foreignkey",
    )
    op.drop_column("user_ideal_persona", "source_profile_history_id")
