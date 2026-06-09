from __future__ import annotations

from typing import NotRequired, TypedDict

from app.agents.profiler.base import (
    BehaviorPatterns,
    IndexedRecord,
    LayerB,
    NotificationPayload,
    ProfileInterpretation,
    Synapse8Axes,
    Top5Interest,
)


class ProfilerState(TypedDict):
    user_id: str
    notify_email: str
    current_step: str
    records: list[IndexedRecord]
    layer_b: NotRequired[LayerB]
    behavior_patterns: NotRequired[BehaviorPatterns]
    axes: NotRequired[Synapse8Axes]
    top5_interests: NotRequired[list[Top5Interest]]
    summary: NotRequired[str]
    interpretation: NotRequired[ProfileInterpretation]
    axis_notes: NotRequired[dict[str, str]]
    investigation_log: NotRequired[list[str]]
    llm_used: NotRequired[bool]
    notification: NotRequired[NotificationPayload]
    error: NotRequired[str]
