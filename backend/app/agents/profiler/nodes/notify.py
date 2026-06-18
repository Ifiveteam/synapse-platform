from __future__ import annotations

import os

from app.agents.profiler.state import ProfilerState
from app.services.email import send_email
from app.services.notification import build_notification, mask_email


def _build_email(state: ProfilerState) -> tuple[str, str]:
    insight = state.get("profile_insight")
    summary = insight.summary_text if insight else "(요약 없음)"
    persona = insight.persona_label if insight else ""
    stats = state.get("catalog_stats") or {}
    total = stats.get("total") or 0
    shorts_ratio = stats.get("shorts_ratio") or 0.0
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")

    subject = f"[Synapse] {state['user_id']} 프로필 분석 완료"
    text = f"""Synapse Profiler 분석이 완료되었습니다.

사용자: {state["user_id"]}
LLM 사용: {"예" if state.get("llm_used") else "아니오 (규칙 fallback)"}

페르소나: {persona or "(미정)"}
요약
{summary}

시청 요약
  기록: {total}건
  숏폼 비중: {shorts_ratio:.0%}

프로필 보기: {frontend_url}/agents/profiler
"""
    return subject, text


def notify_node(state: ProfilerState) -> dict:
    recipient = (state.get("notify_email") or "").strip()
    log = list(state.get("investigation_log") or [])

    if not recipient:
        log.append("notify: skipped (no email)")
        return {"current_step": "notify", "investigation_log": log}

    subject, body = _build_email(state)
    mail_result = send_email(recipient, subject, body)
    notification = build_notification(
        notification_type="analysis_complete",
        message=f"{state['user_id']} 프로필 분석이 완료되었습니다.",
        mail_result=mail_result,
        recipient=recipient,
    )

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
