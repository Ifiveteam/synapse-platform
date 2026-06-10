from __future__ import annotations

from datetime import UTC, datetime

from app.agents.profiler.base import ProfilerResult
from app.agents.profiler.state import ProfilerState
from app.agents.profiler.subagent.notify.email_template import (
    build_analysis_complete_email,
)
from app.services.email import send_email
from app.services.notification import build_notification, mask_email


def _result_from_state(state: ProfilerState) -> ProfilerResult:
    return ProfilerResult(
        user_id=state["user_id"],
        computed_at=datetime.now(UTC),
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


def notify_node(state: ProfilerState) -> dict:
    result = _result_from_state(state)
    recipient = state["notify_email"]
    subject, body = build_analysis_complete_email(result)
    mail_result = send_email(recipient, subject, body)
    notification = build_notification(
        notification_type="analysis_complete",
        message=f"{result.user_id} 프로필 분석이 완료되었습니다.",
        mail_result=mail_result,
        recipient=recipient,
    )

    log = list(state.get("investigation_log", []))
    if mail_result.sent:
        log.append(f"notify: mail sent to {mask_email(recipient)}")
    elif mail_result.attempted:
        log.append(f"notify: mail failed ({mail_result.error})")
    else:
        log.append(f"notify: mail skipped ({mail_result.error})")

    return {
        "notification": notification,
        "current_step": "notify",
        "investigation_log": log,
    }
