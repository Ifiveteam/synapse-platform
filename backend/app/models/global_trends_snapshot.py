"""어그리게이터 거시 트렌드 일별 스냅샷 — 완전 비식별 집계 전용."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class GlobalTrendsSnapshot(Base):
    """배치가 생성한 거시 트렌드 집계 스냅샷.

    user_id 등 개인식별 컬럼을 두지 않으며, 플랫폼 전체를 뭉뚱그린 통계만 저장한다.
    """

    __tablename__ = "global_trends_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="분석 기준 시각 (배치 스냅샷 기준일)",
    )

    top_domains: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="도메인별 user_count·total_duration·main_category 집계",
    )
    top_scrap_categories: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="스크랩 내부 카테고리 순위 통계",
    )
    external_market_keywords: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="네이버 데이터랩·구글 RSS 등 외부 시장 키워드 세트",
    )
    global_8_axis_avg: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "2 에이전트 8축 평균: exploration, analytical, creativity, "
            "execution, achievement_drive, autonomy, sociality, sensitivity"
        ),
    )
    cross_domain_insights: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="6대 도메인 교차 분석·LLM 인사이트",
    )
    trending_keywords: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="NLP 명사 추출·7일 이동평균 대비 급상승 키워드 랭킹",
    )
    keyword_context_map: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="에이전트 소스별 동시 출현 키워드 맥락·도메인 가중치",
    )
    semantic_links: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment=(
            "당일 키워드 semantic edges: "
            "[{source,target,similarity,link_type,left_hint,right_hint}]"
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_gts_snapshot_created",
            text("snapshot_date DESC"),
            text("created_at DESC"),
        ),
    )
