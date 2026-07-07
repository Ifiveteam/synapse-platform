"""B2B 트렌드 뉴스레터 — 마크다운 리포트 HTML 변환·비동기 발송."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from html import escape

import markdown

from app.utils.mailer import send_email
from app.utils.report_filer import ReportFiler

logger = logging.getLogger(__name__)

B2B_NEWSLETTER_SUBSCRIBERS_ENV = "B2B_NEWSLETTER_SUBSCRIBERS"
DEFAULT_B2B_SUBSCRIBERS: tuple[str, ...] = (
    "insights@ifive.site",
    "trend-digest@synapse.local",
)


@dataclass(frozen=True, slots=True)
class NewsletterDispatchResult:
    """뉴스레터 발송 집계 결과."""

    attempted: bool
    sent_count: int
    failed_count: int
    subscriber_count: int = 0
    skipped_reason: str | None = None


class TrendNewsletterDispatcher:
    """일별 리포트 마크다운 → HTML 뉴스레터 변환 및 B2B 구독자 발송."""

    def __init__(self, report_filer: ReportFiler | None = None) -> None:
        self._report_filer = report_filer or ReportFiler()

    @staticmethod
    def resolve_subscribers() -> list[str]:
        """환경 변수 또는 기본 가상 구독자 목록을 반환한다."""
        raw = os.getenv(B2B_NEWSLETTER_SUBSCRIBERS_ENV, "").strip()
        if raw:
            return [email.strip() for email in raw.split(",") if email.strip()]
        return list(DEFAULT_B2B_SUBSCRIBERS)

    async def dispatch_daily_newsletter(
        self,
        target_date: date,
    ) -> NewsletterDispatchResult:
        """대상 일자 리포트를 읽어 B2B 구독자에게 HTML 뉴스레터를 발송한다."""
        subscribers = self.resolve_subscribers()
        if not subscribers:
            logger.warning(
                "[newsletter] 구독자 없음 — 발송 skip date=%s",
                target_date.isoformat(),
            )
            return NewsletterDispatchResult(
                attempted=False,
                sent_count=0,
                failed_count=0,
                subscriber_count=0,
                skipped_reason="no_subscribers",
            )

        try:
            markdown_text = await self._report_filer.read_report(target_date)
        except OSError:
            logger.exception(
                "[newsletter] 리포트 파일 읽기 실패 date=%s",
                target_date.isoformat(),
            )
            return NewsletterDispatchResult(
                attempted=False,
                sent_count=0,
                failed_count=0,
                subscriber_count=len(subscribers),
                skipped_reason="file_read_error",
            )

        if not markdown_text or not markdown_text.strip():
            logger.warning(
                "[newsletter] 리포트 본문 없음 — 발송 skip date=%s",
                target_date.isoformat(),
            )
            return NewsletterDispatchResult(
                attempted=False,
                sent_count=0,
                failed_count=0,
                subscriber_count=len(subscribers),
                skipped_reason="empty_report",
            )

        subject = f"[Synapse B2B] 트렌드 인텔리전스 리포트 — {target_date.isoformat()}"
        plain_text = self._build_plain_text(markdown_text, target_date)
        html_body = self._render_newsletter_html(markdown_text, target_date)

        sent_count = 0
        failed_count = 0
        for recipient in subscribers:
            try:
                result = await send_email(
                    recipient,
                    subject,
                    plain_text,
                    html=html_body,
                )
            except OSError:
                logger.exception(
                    "[newsletter] 메일 전송 I/O 오류 recipient=%s date=%s",
                    recipient,
                    target_date.isoformat(),
                )
                failed_count += 1
                continue
            except Exception:
                logger.exception(
                    "[newsletter] 메일 전송 예외 recipient=%s date=%s",
                    recipient,
                    target_date.isoformat(),
                )
                failed_count += 1
                continue

            if result.sent:
                sent_count += 1
                logger.info(
                    "[newsletter] 발송 성공 recipient=%s date=%s",
                    recipient,
                    target_date.isoformat(),
                )
            else:
                failed_count += 1
                logger.error(
                    "[newsletter] 발송 실패 recipient=%s date=%s error=%s",
                    recipient,
                    target_date.isoformat(),
                    result.error,
                )

        return NewsletterDispatchResult(
            attempted=True,
            sent_count=sent_count,
            failed_count=failed_count,
            subscriber_count=len(subscribers),
        )

    @staticmethod
    def _build_plain_text(markdown_text: str, target_date: date) -> str:
        return (
            f"Synapse B2B 트렌드 인텔리전스 리포트 ({target_date.isoformat()})\n\n"
            f"{markdown_text.strip()}\n\n"
            "— Synapse Intelligence Team"
        )

    def _render_newsletter_html(self, markdown_text: str, target_date: date) -> str:
        article_html = markdown.markdown(
            markdown_text,
            extensions=["extra", "sane_lists", "tables", "nl2br"],
        )
        article_html = self._postprocess_article_html(article_html)
        title = f"Synapse Trend Intelligence — {target_date.isoformat()}"
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f4f6fb;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:680px;background-color:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0;">
          <tr>
            <td style="padding:28px 32px;background:linear-gradient(135deg,#312e81 0%,#4338ca 55%,#6366f1 100%);color:#ffffff;">
              <p style="margin:0 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.85;">Synapse Intelligence</p>
              <h1 style="margin:0;font-size:24px;line-height:1.3;font-weight:700;">B2B 트렌드 인텔리전스 리포트</h1>
              <p style="margin:10px 0 0;font-size:14px;opacity:0.92;">분석 기준일: {escape(target_date.isoformat())}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <div style="font-size:15px;line-height:1.75;color:#1e293b;">
                {article_html}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px 28px;border-top:1px solid #e2e8f0;background-color:#f8fafc;">
              <p style="margin:0;font-size:12px;line-height:1.6;color:#64748b;">
                본 메일은 Synapse 일별 배치 파이프라인에서 자동 발송되었습니다.<br />
                문의: Synapse Intelligence Team
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    @staticmethod
    def _postprocess_article_html(html: str) -> str:
        """인라인 스타일을 주입해 메일 클라이언트 가독성을 높인다."""
        html = re.sub(
            r"<h1>",
            '<h1 style="margin:0 0 16px;font-size:24px;line-height:1.3;color:#0f172a;">',
            html,
        )
        html = re.sub(
            r"<h2>",
            '<h2 style="margin:28px 0 12px;font-size:20px;line-height:1.35;color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:8px;">',
            html,
        )
        html = re.sub(
            r"<h3>",
            '<h3 style="margin:20px 0 8px;font-size:17px;line-height:1.4;color:#1e293b;">',
            html,
        )
        html = re.sub(
            r"<p>",
            '<p style="margin:0 0 14px;">',
            html,
        )
        html = re.sub(
            r"<ul>",
            '<ul style="margin:0 0 14px 20px;padding:0;">',
            html,
        )
        html = re.sub(
            r"<ol>",
            '<ol style="margin:0 0 14px 20px;padding:0;">',
            html,
        )
        html = re.sub(
            r"<li>",
            '<li style="margin:0 0 6px;">',
            html,
        )
        html = re.sub(
            r"<blockquote>",
            '<blockquote style="margin:0 0 14px;padding:12px 16px;border-left:4px solid #818cf8;background:#f8fafc;color:#334155;">',
            html,
        )
        html = re.sub(
            r"<code>",
            '<code style="padding:2px 6px;border-radius:4px;background:#f1f5f9;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;">',
            html,
        )
        html = re.sub(
            r"<table>",
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 16px;border-collapse:collapse;">',
            html,
        )
        html = re.sub(
            r"<th>",
            '<th style="padding:10px 12px;border:1px solid #e2e8f0;background:#f8fafc;text-align:left;font-size:13px;">',
            html,
        )
        html = re.sub(
            r"<td>",
            '<td style="padding:10px 12px;border:1px solid #e2e8f0;font-size:13px;">',
            html,
        )
        html = re.sub(
            r"<a ",
            '<a style="color:#4f46e5;text-decoration:underline;" ',
            html,
        )
        return html
