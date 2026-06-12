from __future__ import annotations

import os

from app.agents.profiler.base import ProfilerResult, profiler_result_from_state
from app.agents.profiler.state import ProfilerState
from app.services.email import send_email
from app.services.notification import build_notification, mask_email


def _build_analysis_complete_email(result: ProfilerResult) -> tuple[str, str]:
    subject = f"[Synapse] {result.user_id} 프로필 분석 완료"

    top5_lines = "\n".join(
        f"  {item.rank}. {item.label} ({item.score:.0%})"
        for item in result.top5_interests[:5]
    )
    layer_b = result.layer_b
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
    profile_url = f"{frontend_url}/agents/profiler"

    text = f"""Synapse Profiler 분석이 완료되었습니다.

사용자: {result.user_id}
LLM 사용: {"예" if result.llm_used else "아니오 (규칙 fallback)"}

요약
{result.summary}

TOP5 관심사
{top5_lines or "  (없음)"}

Layer B
  검색 활성 비율: {layer_b.search_active_ratio:.0%}
  시청 편중도: {layer_b.viewing_concentration:.0%}
  취향 다양성: {layer_b.taste_diversity_index:.1f}
  탐색 깊이: {layer_b.exploration_depth:.0%}

해석
  소비 모드: {result.interpretation.consumption_mode}
  주요 레버: {result.interpretation.primary_lever}

프로필 보기: {profile_url}
"""
    return subject, text


def notify_node(state: ProfilerState) -> dict:
    result = profiler_result_from_state(state)
    recipient = state["notify_email"]
    subject, body = _build_analysis_complete_email(result)
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
