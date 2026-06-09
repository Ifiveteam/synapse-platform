from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.agents.profiler.base.axes import AxesDelta, Synapse8Axes
from app.agents.profiler.base.layer_b import LayerB, LayerBDelta
from app.agents.profiler.base.profile import ProfilerResult


class ProfilerSnapshot(BaseModel):
    version: str
    user_id: str
    computed_at: datetime
    result: ProfilerResult


class ProfileCompareDelta(BaseModel):
    user_id: str
    from_version: str
    to_version: str
    axes_delta: AxesDelta
    layer_b_delta: LayerBDelta
    top5_added: list[str] = Field(default_factory=list)
    top5_removed: list[str] = Field(default_factory=list)


class AnomalyItem(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class IdealProfile(BaseModel):
    user_id: str
    axes: Synapse8Axes
    layer_b: LayerB


class IdealGap(BaseModel):
    user_id: str
    axes_gap: AxesDelta
    layer_b_gap: LayerBDelta
    axis_achievement_pct: dict[str, float] = Field(default_factory=dict)
