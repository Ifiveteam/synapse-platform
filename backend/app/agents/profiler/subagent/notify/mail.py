from __future__ import annotations

import os
from dataclasses import dataclass

from app.agents.profiler.base import DEFAULT_FROM_ADDRESS, ProfilerResult


@dataclass
class MailDeliveryResult:
    attempted: bool
    sent: bool
    from_address: str
    error: str | None = None


def _get_from_email() -> str:
    return os.getenv("RESEND_FROM_EMAIL", f"Synapse <{DEFAULT_FROM_ADDRESS}>")


def _build_subject(result: ProfilerResult) -> str:
    return f"[Synapse] {result.user_id} 프로필 분석 완료"


def _build_body_text(result: ProfilerResult) -> str:
    top5_lines = "\n".join(
        f"  {item.rank}. {item.label} ({item.score:.0%})"
        for item in result.top5_interests[:5]
    )
    layer_b = result.layer_b
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
    profile_url = f"{frontend_url}/agents/profiler"

    return f"""Synapse Profiler 분석이 완료되었습니다.

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


def send_analysis_complete_email(
    to: str,
    result: ProfilerResult,
) -> MailDeliveryResult:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_email = _get_from_email()

    if not api_key:
        return MailDeliveryResult(
            attempted=False,
            sent=False,
            from_address=DEFAULT_FROM_ADDRESS,
            error="mail_not_configured",
        )

    try:
        import resend

        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": from_email,
                "to": [to],
                "subject": _build_subject(result),
                "text": _build_body_text(result),
            }
        )
        return MailDeliveryResult(
            attempted=True,
            sent=True,
            from_address=DEFAULT_FROM_ADDRESS,
        )
    except Exception as exc:  # noqa: BLE001 — mail must not fail the pipeline
        return MailDeliveryResult(
            attempted=True,
            sent=False,
            from_address=DEFAULT_FROM_ADDRESS,
            error=str(exc),
        )
