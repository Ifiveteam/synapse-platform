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
    # 배치 스코프: 이 분석이 대상으로 삼는 소스 id들 (없으면 통합본=최근 2달 전체)
    analysis_source_ids: NotRequired[list[str] | None]
    # 이 분석을 유발한 배치 id (스냅샷에 박제 → 네비게이터가 근거 스코프에 활용)
    batch_id: NotRequired[str | None]

    video_summary_saved_count: NotRequired[int | None]
    video_summary_skipped_count: NotRequired[int | None]
    video_summary_error: NotRequired[str | None]

    catalog_stats: NotRequired[dict[str, Any]]
    analysis_samples: NotRequired[list[AnalysisSample]]

    profile_scores: NotRequired[ProfileScoresOutput]
    profile_insight: NotRequired[ProfileInsightOutput]
    supporting_evidence: NotRequired[dict[str, Any]]
    # 초상(portrait): 결과 페이지·완료 이메일과 동일한 페르소나/키워드/요약
    portrait: NotRequired[dict[str, Any] | None]

    snapshot_id: NotRequired[str | None]
    llm_used: NotRequired[bool]

    investigation_log: NotRequired[list[str]]
    error: NotRequired[str | None]
    notification: NotRequired[NotificationPayload]
