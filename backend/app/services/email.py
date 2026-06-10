"""Resend 기반 이메일 발송 (에이전트·API 공통)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_FROM_ADDRESS = "synapse@ifive.site"


@dataclass
class MailDeliveryResult:
    attempted: bool
    sent: bool
    from_address: str
    error: str | None = None


def _get_from_email() -> str:
    return os.getenv("RESEND_FROM_EMAIL", f"Synapse <{DEFAULT_FROM_ADDRESS}>")


def send_email(
    to: str,
    subject: str,
    text: str,
    *,
    from_email: str | None = None,
) -> MailDeliveryResult:
    """텍스트 메일 발송. 실패해도 예외를 던지지 않고 MailDeliveryResult로 반환."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    sender = from_email or _get_from_email()

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
                "from": sender,
                "to": [to],
                "subject": subject,
                "text": text,
            }
        )
        return MailDeliveryResult(
            attempted=True,
            sent=True,
            from_address=DEFAULT_FROM_ADDRESS,
        )
    except Exception as exc:  # noqa: BLE001 — mail must not fail the caller pipeline
        return MailDeliveryResult(
            attempted=True,
            sent=False,
            from_address=DEFAULT_FROM_ADDRESS,
            error=str(exc),
        )
