from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from app.schemas.profiler import ProfileInsightOutput, ProfileScoresOutput
from app.services.notification import NotificationPayload


class AnalysisSample(TypedDict, total=False):
    catalog_id: str
    title: str | None
    channel: str
    summary_kr: str | None
    youtube_category_id: str | None
    is_shorts: bool | None


class ProfilerState(TypedDict):
    user_id: str
    notify_email: str
    current_step: str
    analysis_limit: NotRequired[int | None]

    video_summary_saved_count: NotRequired[int | None]
    video_summary_skipped_count: NotRequired[int | None]
    video_summary_error: NotRequired[str | None]

    catalog_stats: NotRequired[dict[str, Any]]
    analysis_samples: NotRequired[list[AnalysisSample]]

    profile_scores: NotRequired[ProfileScoresOutput]
    profile_insight: NotRequired[ProfileInsightOutput]
    supporting_evidence: NotRequired[dict[str, Any]]

    snapshot_id: NotRequired[str | None]
    llm_used: NotRequired[bool]

    investigation_log: NotRequired[list[str]]
    error: NotRequired[str | None]
    notification: NotRequired[NotificationPayload]
