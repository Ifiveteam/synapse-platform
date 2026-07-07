"""비동기 메일 발송 추상화 — ``app.services.email`` Resend 어댑터 래퍼."""

from __future__ import annotations

import asyncio

from app.services.email import (
    EmailAttachment,
    MailDeliveryResult,
)
from app.services.email import (
    send_email as _send_email_sync,
)


async def send_email(
    to: str,
    subject: str,
    text: str,
    *,
    html: str | None = None,
    from_email: str | None = None,
    attachments: list[EmailAttachment] | None = None,
) -> MailDeliveryResult:
    """동기 Resend 클라이언트를 스레드 풀에서 실행하는 비동기 메일 발송."""
    return await asyncio.to_thread(
        _send_email_sync,
        to,
        subject,
        text,
        html=html,
        from_email=from_email,
        attachments=attachments,
    )
