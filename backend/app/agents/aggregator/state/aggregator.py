"""Aggregator LangGraph 워크플로우 상태."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from app.agents.aggregator.base import IntegratedData
from app.schemas.report import DashboardReportSchema
from app.services.notification import NotificationPayload

RevisionTarget = Literal[
    "generate_report",
    "culture_analysis",
    "market_analysis",
    "both_analyses",
]

MAX_REVIEW_ATTEMPTS = 3
REVIEW_PASS_THRESHOLD = 80


class AggregatorState(TypedDict):
    """LangGraph 실행 상태."""

    integrated_data: NotRequired[IntegratedData]
    culture_analysis: NotRequired[str]
    market_analysis: NotRequired[str]
    report_json: NotRequired[DashboardReportSchema]
    verification_score: NotRequired[int]
    is_template_valid: NotRequired[bool]
    critique_feedback: NotRequired[str]
    revision_target: NotRequired[RevisionTarget]
    review_count: NotRequired[int]
    error: NotRequired[str]
    notify_email: NotRequired[str]
    post_id: NotRequired[str]
    notification: NotRequired[NotificationPayload]
    current_step: NotRequired[str]
