from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class NavigatorPlaylist(TimestampMixin, Base):
    """이상향 기반 YouTube 재생목록. 이상향(user_ideal_persona) 1개에 N개. [네비게이터]

    계획: docs/navigator/PLAN_youtube_playlist.md
    """

    __tablename__ = "navigator_playlist"

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
    ideal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_ideal_persona.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 생성 상태 — pending(백그라운드 생성중) / ready(완료) / failed
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'ready'")
    )
    # YouTube 저장 상태 — none / saving / saved / failed
    save_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'none'")
    )
    # 자동 갱신 주기 — none / weekly / monthly (스케줄러가 주기 도래 시 재생성)
    refresh_period: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'none'")
    )
    # 마지막 (재)생성 시각 — 스케줄러 주기 도래 판정용 (생성·재생성마다 갱신)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 자동 "{persona_label} #N", 사용자 수정 가능
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 재생목록 총평 (LLM 큐레이션 summary)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 보여줄 영상 10개
    items_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # 발굴·선택한 채널 [{channel_id, title}] — re-RSS 무쿼터 보충 소스
    channels_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # 미리 뽑아둔 여분 영상(즉시 교체용)
    reservoir_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 실제 YouTube에 저장된 재생목록 id (Phase B, 저장 후 채워짐)
    youtube_playlist_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_np_user_ideal", "user_id", "ideal_id"),)
