from __future__ import annotations

from app.agents.profiler.base import (
    DEFAULT_FROM_ADDRESS,
    EmailChannel,
    InAppChannel,
    NotificationChannels,
    NotificationPayload,
    ProfilerResult,
)
from app.agents.profiler.subagent.notify.mail import MailDeliveryResult


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    if len(local) == 1:
        return f"{local}***@{domain}"
    return f"{local[0]}***@{domain}"


def build_notification(
    result: ProfilerResult,
    mail_result: MailDeliveryResult,
    recipient: str,
) -> NotificationPayload:
    email_channel = EmailChannel(
        attempted=mail_result.attempted,
        sent=mail_result.sent,
        from_address=mail_result.from_address or DEFAULT_FROM_ADDRESS,
        recipient_masked=mask_email(recipient),
        error=mail_result.error,
    )
    return NotificationPayload(
        type="analysis_complete",
        message=f"{result.user_id} 프로필 분석이 완료되었습니다.",
        channels=NotificationChannels(
            in_app=InAppChannel(delivered=True),
            email=email_channel,
        ),
    )
