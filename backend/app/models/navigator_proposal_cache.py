from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class NavigatorProposalCache(TimestampMixin, Base):
    """이상향 제안 3안 캐시 — (유저 + 분석 스냅샷)별로 LLM 생성 결과를 보관. [네비게이터]

    같은 스냅샷이면 같은 3안을 재사용한다(refresh 시 덮어씀).
    """

    __tablename__ = "navigator_proposal_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 이 제안이 근거로 삼은 분석 스냅샷 (삭제되면 캐시도 제거)
    source_profile_history_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profile_history.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 생성 상태: pending(백그라운드 생성 중) | ready(완료) | failed(실패)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="ready"
    )
    # ProposalsResponse.proposals (3안 전체: 13축+8축+persona+reasoning) 직렬화본
    # pending 상태에선 아직 없을 수 있어 nullable.
    proposals_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 생성 당시 시청기록 수 (현재 수와 다르면 stale 힌트)
    catalog_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "source_profile_history_id", name="uq_npc_user_snapshot"
        ),
    )
