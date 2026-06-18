"""비교 분석 HTTP 응답."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.profiler.llm.compare import CompareNarrativeOutput


class HabitMetrics(BaseModel):
    channel_concentration: float
    category_concentration: float
    category_diversity: float
    exploration_depth: float


class CompareSnapshotSummary(BaseModel):
    snapshot_id: str
    snapshot_date: datetime
    persona_label: str | None = None
    summary_text: str = ""
    scores: dict[str, float]
    habits: HabitMetrics
    shorts_ratio: float = 0.0
    total_videos: int = 0


class AnalysisCompareResponse(BaseModel):
    from_snapshot: CompareSnapshotSummary
    to_snapshot: CompareSnapshotSummary
    scores_delta: dict[str, float]
    habits_from: HabitMetrics
    habits_to: HabitMetrics
    habits_delta: HabitMetrics
    shorts_ratio_delta: float = 0.0
    traits_added: list[str] = []
    traits_removed: list[str] = []
    channels_added: list[str] = []
    channels_removed: list[str] = []
    narrative: CompareNarrativeOutput | None = None
    narrative_error: str | None = None
