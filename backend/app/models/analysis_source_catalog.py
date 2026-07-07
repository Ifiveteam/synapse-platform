from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class AnalysisSourceCatalog(Base):
    """소스(파일) ↔ 시청영상(catalog) 다대다 소속.

    창고(user_watch_catalog)는 URL당 1행 정본을 그대로 유지하고, "이 영상이 어느 파일에서
    왔는지"만 이 표에 별도로 쌓는다. 같은 영상이 여러 파일에 겹쳐도 소속 짝이 여러 줄로
    남아(덮어쓰기 없음), 배치별 분석이 서로 뺏지 않는다.
    """

    __tablename__ = "analysis_source_catalog"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    analysis_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_analysis_source.id", ondelete="CASCADE"),
        nullable=False,
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_watch_catalog.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "analysis_source_id", "catalog_id", name="uq_asc_source_catalog"
        ),
        Index("ix_asc_source", "analysis_source_id"),
        Index("ix_asc_catalog", "catalog_id"),
    )
