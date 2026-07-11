"""분석 상세 페이지 채팅을 "이 분석 하나"로 한정할 때 쓸 시청 데이터 범위 계산.

배치(업로드 파일) 연결이 남아있는 분석은 그 배치에 실제로 속한 catalog 행 id를
정확히 찾아 그것만 쓴다(exact). 연결이 없는(배치 스코프 도입 전) 옛날 분석은
스냅샷 날짜 기준 기간 근사치로 범위를 잡는다(approx) — 둘 다 아니면 스코프 없음.

주의: 날짜 기간(window)만으로 필터링하면, 서로 다른 두 분석의 시청 기간이
겹칠 때(예: 두 배치가 60일 안에 모두 들어있는 경우) 다른 분석의 영상이 섞여
들어온다 — 그래서 배치 연결이 있으면 반드시 정확한 catalog id 목록을 쓴다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.shared.analysis_window import WATCH_CATALOG_WINDOW_DAYS
from app.models.analysis_source_catalog import AnalysisSourceCatalog
from app.models.user_analysis_source import UserAnalysisSource
from app.models.user_profile_history import UserProfileHistory

WatchWindow = tuple[datetime, datetime]


@dataclass(frozen=True)
class AnalysisScope:
    """catalog_ids가 있으면 그것만 정확히 사용하고, 없으면 window(기간)로 근사한다.

    snapshot_date는 LLM의 "오늘 날짜" 기준점을 이 분석 시점으로 바꿔치기하는 데 쓴다 —
    안 그러면 "지난 일주일" 같은 상대 날짜 표현을 실제 오늘 기준으로 해석해서,
    이 분석의 조회 범위(과거)와 어긋나는 문제가 생긴다.
    """

    catalog_ids: list[uuid.UUID] | None = None
    window: WatchWindow | None = None
    snapshot_date: datetime | None = None


async def resolve_analysis_scope(
    db: AsyncSession, user_id: uuid.UUID, analysis_id: str
) -> AnalysisScope | None:
    """analysis_id(스냅샷)에 해당하는 시청 데이터 범위를 계산합니다.

    스냅샷을 못 찾으면 None을 반환합니다 (스코프 없음 — 기존처럼 전체 데이터 사용).
    """
    try:
        snapshot_uuid = uuid.UUID(str(analysis_id))
    except ValueError:
        return None

    snapshot = (
        await db.execute(
            select(UserProfileHistory).where(
                UserProfileHistory.id == snapshot_uuid,
                UserProfileHistory.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if snapshot is None:
        return None

    if snapshot.batch_id is not None:
        source_ids_subq = select(UserAnalysisSource.id).where(
            UserAnalysisSource.batch_id == snapshot.batch_id
        )
        catalog_ids = (
            (
                await db.execute(
                    select(AnalysisSourceCatalog.catalog_id)
                    .where(
                        AnalysisSourceCatalog.analysis_source_id.in_(source_ids_subq)
                    )
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        if catalog_ids:
            return AnalysisScope(
                catalog_ids=list(catalog_ids), snapshot_date=snapshot.snapshot_date
            )

    # 배치 연결이 없거나(옛날 분석) 배치에 실제 catalog가 없으면 스냅샷 날짜로 근사.
    anchor = snapshot.snapshot_date
    start = anchor - timedelta(days=WATCH_CATALOG_WINDOW_DAYS)
    return AnalysisScope(window=(start, anchor), snapshot_date=anchor)
