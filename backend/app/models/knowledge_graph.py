"""Reporter 지식 그래프 일별 스냅샷 — react-force-graph 바인딩 전용."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixin import TimestampMixin


class KnowledgeGraph(TimestampMixin, Base):
    """일별 교차 도메인 지식 그래프 — B2B API 초고속 조회용.

    아키텍처 결정:
    - ``GlobalTrendsSnapshot`` 은 원시 집계·키워드 맥락(keyword_context_map) 보관.
    - 본 테이블은 ``KnowledgeGraphMapper`` 가 생성한 nodes/links JSON만 저장하여
      프론트엔드가 graph_date 단일 조건으로 즉시 fetch 할 수 있게 한다.
    """

    __tablename__ = "knowledge_graphs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    graph_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        unique=True,
        comment="KST 기준 분석 일자 (일별 UPSERT 키)",
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("global_trends_snapshot.id", ondelete="SET NULL"),
        nullable=True,
        comment="원본 GlobalTrendsSnapshot 참조",
    )
    graph_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment='react-force-graph 표준: {"nodes": [...], "links": [...]}',
    )
    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="node_count·link_count·algorithm 등 메타",
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="그래프 생성 완료 시각",
    )

    __table_args__ = (
        Index("ix_knowledge_graphs_graph_date", text("graph_date DESC")),
        Index(
            "ix_knowledge_graphs_snapshot_id",
            "snapshot_id",
        ),
    )
