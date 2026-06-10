"""알림 payload 조립 (에이전트·API 공통)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.email import DEFAULT_FROM_ADDRESS, MailDeliveryResult


class InAppChannel(BaseModel):
    delivered: bool = True


class EmailChannel(BaseModel):
    attempted: bool = False
    sent: bool = False
    from_address: str = DEFAULT_FROM_ADDRESS
    recipient_masked: str = ""
    error: str | None = None


class NotificationChannels(BaseModel):
    in_app: InAppChannel = Field(default_factory=InAppChannel)
    email: EmailChannel = Field(default_factory=EmailChannel)


class NotificationPayload(BaseModel):
    type: str
    message: str = ""
    channels: NotificationChannels = Field(default_factory=NotificationChannels)


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
    *,
    notification_type: str,
    message: str,
    mail_result: MailDeliveryResult,
    recipient: str,
    in_app_delivered: bool = True,
) -> NotificationPayload:
    email_channel = EmailChannel(
        attempted=mail_result.attempted,
        sent=mail_result.sent,
        from_address=mail_result.from_address or DEFAULT_FROM_ADDRESS,
        recipient_masked=mask_email(recipient),
        error=mail_result.error,
    )
    return NotificationPayload(
        type=notification_type,
        message=message,
        channels=NotificationChannels(
            in_app=InAppChannel(delivered=in_app_delivered),
            email=email_channel,
        ),
    )
