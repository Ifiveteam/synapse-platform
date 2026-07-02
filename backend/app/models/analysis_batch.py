from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class AnalysisBatchStatus:
    """배치 생애주기: open → sealed → profiling → done."""

    OPEN = "open"  # 파일 수집 중 (seal 대기)
    SEALED = "sealed"  # 닫힘("다 보냄"). 인덱싱 끝나면 트리거 가능
    PROFILING = "profiling"  # 프로파일러 트리거됨 (중복 발사 방지 상태)
    DONE = "done"  # 분석 완료


class AnalysisBatch(TimestampMixin, Base):
    """분석 요청(클릭) 단위 묶음 — 한 번의 '분석 시작'에 들어온 소스들을 묶는다.

    batch id는 프론트가 클릭당 생성(crypto.randomUUID)해 넘긴다. batch_id 없이 들어온
    소스는 서버가 단일 배치를 자동 생성한다. seal(닫힘)되면 그 배치로 프로파일 1회.
    """

    __tablename__ = "analysis_batch"

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
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=AnalysisBatchStatus.OPEN,
    )

    __table_args__ = (Index("ix_ab_user_created", "user_id", text("created_at DESC")),)
