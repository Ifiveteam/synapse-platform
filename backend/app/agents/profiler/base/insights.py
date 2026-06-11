from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.agents.profiler.base.axes import AxesDelta
from app.agents.profiler.base.layer_b import LayerBDelta
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
