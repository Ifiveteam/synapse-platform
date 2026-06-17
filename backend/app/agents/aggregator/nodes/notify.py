"""notify 노드 — 분석 완료 이메일·PDF 첨부."""

from __future__ import annotations

import os
from typing import Any

from app.agents.aggregator.nodes._helpers import NODE_NOTIFY
from app.agents.aggregator.report import coerce_dashboard_report
from app.agents.aggregator.state import AggregatorState
from app.agents.aggregator.trace import log_node_enter, logger
from app.services.email import EmailAttachment, send_email
from app.services.notification import build_notification, mask_email
from app.services.trend.pdf import build_trend_report_pdf, trend_report_pdf_filename

_SUBJECT = "[Synapse] B2B 트렌드 분석 완료"


def _report_url(state: AggregatorState) -> str:
    post_id = state.get("post_id", "")
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
    if post_id:
        return f"{frontend_url}/agents/aggregator/posts/{post_id}"
    return f"{frontend_url}/agents/aggregator/posts"


def _build_short_email_body(report_url: str, *, has_pdf: bool) -> str:
    if has_pdf:
        return f"""Synapse Aggregator B2B 트렌드 분석이 완료되었습니다.

첨부 PDF에서 전체 리포트를 확인하실 수 있습니다.
웹에서 보기: {report_url}
"""
    return f"""Synapse Aggregator B2B 트렌드 분석이 완료되었습니다.

PDF 첨부 생성에 실패하여 링크로 안내드립니다.
웹에서 보기: {report_url}
"""


def _build_fallback_email_body(state: AggregatorState, report_url: str) -> str:
    """PDF·메일 발송 실패 시 상세 텍스트 fallback."""
    report = coerce_dashboard_report(state["report_json"])
    integrated_data = state["integrated_data"]
    cohort_size = integrated_data["internal_user_stats"]["cognitive_bias_map"][
        "cohort_size"
    ]
    verification_score = state.get("verification_score", 0)

    return f"""Synapse Aggregator B2B 트렌드 분석이 완료되었습니다.

헤드라인
{report.headline_summary}

코호트 규모: {cohort_size:,}명
미디어 중립성: {report.neutrality_score}점 ({report.neutrality_status})
검수 점수: {verification_score}점

격차 해석 (요약)
{report.gap_analysis.filter_bubble_scenario}

리포트 보기: {report_url}
"""


async def _build_pdf_attachment(state: AggregatorState) -> EmailAttachment | None:
    raw_report = state.get("report_json")
    if not raw_report:
        return None

    post_id = state.get("post_id", "")
    pdf_bytes = await build_trend_report_pdf(raw_report)
    return EmailAttachment(
        filename=trend_report_pdf_filename(post_id=post_id),
        content=pdf_bytes,
    )


async def notify_node(state: AggregatorState) -> dict[str, Any]:
    """분석 완료 후 선택적 이메일 발송. notify_email이 없으면 스킵한다."""
    log_node_enter(NODE_NOTIFY, state=state)

    recipient = state.get("notify_email")
    if not recipient:
        logger.info("  └─ notify_email 없음 — 메일 발송 스킵")
        return {"current_step": "notify"}

    report_url = _report_url(state)
    attachments: list[EmailAttachment] | None = None
    has_pdf = False

    try:
        pdf_attachment = await _build_pdf_attachment(state)
        if pdf_attachment is not None:
            attachments = [pdf_attachment]
            has_pdf = True
            logger.info(
                "  └─ PDF 첨부 생성 완료: %s (%s bytes)",
                pdf_attachment.filename,
                len(pdf_attachment.content),
            )
    except Exception as exc:  # noqa: BLE001 — PDF 실패 시 링크 메일로 fallback
        logger.warning("  └─ PDF 첨부 생성 실패 — 링크만 발송: %s", exc)

    body = _build_short_email_body(report_url, has_pdf=has_pdf)
    mail_result = send_email(
        recipient,
        _SUBJECT,
        body,
        attachments=attachments,
    )

    if not mail_result.sent and has_pdf:
        logger.warning("  └─ PDF 첨부 메일 실패 — 텍스트 fallback 재시도")
        fallback_body = _build_fallback_email_body(state, report_url)
        mail_result = send_email(recipient, _SUBJECT, fallback_body)

    notification = build_notification(
        notification_type="analysis_complete",
        message="B2B 트렌드 분석이 완료되었습니다.",
        mail_result=mail_result,
        recipient=recipient,
    )

    if mail_result.sent:
        logger.info("  └─ 메일 발송 완료: %s", mask_email(recipient))
    elif mail_result.attempted:
        logger.warning("  └─ 메일 발송 실패: %s", mail_result.error)
    else:
        logger.info("  └─ 메일 발송 스킵: %s", mail_result.error)

    return {
        "notification": notification,
        "current_step": "notify",
    }
