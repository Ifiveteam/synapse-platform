from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.agents.profiler.base.axes import Synapse8Axes
from app.agents.profiler.base.layer_b import LayerB


class Top5Interest(BaseModel):
    rank: int = Field(ge=1, le=5)
    label: str
    score: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class ProfilerAnalysisOutput(BaseModel):
    axes: Synapse8Axes
    top5_interests: list[Top5Interest]
    summary: str
    axis_notes: dict[str, str] = Field(default_factory=dict)


class ProfileInterpretation(BaseModel):
    consumption_mode: str
    primary_lever: str
    sovereignty_verdict: str
    radar_gap_insight: str


class BehaviorPatterns(BaseModel):
    hour_distribution: dict[str, float] = Field(default_factory=dict)
    weekend_ratio: float = Field(ge=0, le=1, default=0.0)
    top_repeated_channels: list[dict[str, str | int | float]] = Field(
        default_factory=list
    )
    top_repeated_tags: list[dict[str, str | int | float]] = Field(default_factory=list)


class ProfilerResult(BaseModel):
    user_id: str
    computed_at: datetime
    axes: Synapse8Axes
    layer_b: LayerB
    top5_interests: list[Top5Interest]
    summary: str
    interpretation: ProfileInterpretation
    axis_notes: dict[str, str] = Field(default_factory=dict)
    investigation_log: list[str] = Field(default_factory=list)
    llm_used: bool = False
    behavior_patterns: BehaviorPatterns | None = None


def profiler_result_from_state(state: dict) -> ProfilerResult:
    return ProfilerResult(
        user_id=state["user_id"],
        computed_at=datetime.now(tz=UTC),
        axes=state["axes"],
        layer_b=state["layer_b"],
        top5_interests=state["top5_interests"],
        summary=state["summary"],
        interpretation=state["interpretation"],
        axis_notes=state.get("axis_notes", {}),
        investigation_log=state.get("investigation_log", []),
        llm_used=state.get("llm_used", False),
        behavior_patterns=state.get("behavior_patterns"),
    )
