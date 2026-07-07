"""지식 그래프 시뮬레이터 — 기간·도메인·스코어 필터 On-the-fly 재연산."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.reporter.graph_mapper import KnowledgeGraphMapper
from app.repositories import reporter_repository
from app.schemas.reporter import GraphSimulatorRequest, GraphSimulatorResponse


class GraphSimulatorService:
    """B2B 인터랙티브 그래프 시뮬레이터 비즈니스 로직."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        graph_mapper: KnowledgeGraphMapper | None = None,
    ) -> None:
        self._session = session
        self._graph_mapper = graph_mapper or KnowledgeGraphMapper()

    async def simulate(self, request: GraphSimulatorRequest) -> GraphSimulatorResponse:
        """요청 필터에 맞는 custom nodes/links 그래프를 실시간 생성한다."""
        self._validate_date_range(request.start_date, request.end_date)

        rows = await reporter_repository.fetch_simulation_rollup_rows(
            self._session,
            request.start_date,
            request.end_date,
        )
        if not rows:
            return GraphSimulatorResponse(
                nodes=[],
                links=[],
                meta={
                    "snapshot_count": 0,
                    "start_date": request.start_date.isoformat(),
                    "end_date": request.end_date.isoformat(),
                },
            )

        snapshot = reporter_repository.build_simulation_snapshot(
            rows,
            top_keywords_limit=request.top_keywords_limit,
            min_score_threshold=request.min_score_threshold,
        )
        if snapshot is None:
            return GraphSimulatorResponse(
                nodes=[], links=[], meta={"snapshot_count": 0}
            )

        graph_data, meta = self._graph_mapper.map_simulation(
            snapshot,
            keyword_map={
                "target_date": (
                    f"{request.start_date.isoformat()}..{request.end_date.isoformat()}"
                ),
                "contexts": snapshot.keyword_context_map.get("contexts", []),  # type: ignore[typeddict-item]
                "keyword_domain_weights": snapshot.keyword_context_map.get(
                    "keyword_domain_weights",
                    {},
                ),  # type: ignore[typeddict-item]
            },
            target_domains=request.target_domains,
            min_score_threshold=request.min_score_threshold,
            top_n=request.top_keywords_limit,
        )
        meta.update(
            {
                "snapshot_count": snapshot.snapshot_count,
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
            }
        )
        return GraphSimulatorResponse(
            nodes=graph_data.get("nodes", []),  # type: ignore[arg-type]
            links=graph_data.get("links", []),  # type: ignore[arg-type]
            meta=meta,
        )

    @staticmethod
    def _validate_date_range(start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date는 end_date보다 클 수 없습니다.",
            )
        span_days = (end_date - start_date).days + 1
        if span_days > reporter_repository.MAX_SIMULATOR_RANGE_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"조회 기간은 최대 {reporter_repository.MAX_SIMULATOR_RANGE_DAYS}일까지 "
                    "허용됩니다."
                ),
            )
