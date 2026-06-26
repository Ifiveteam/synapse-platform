"""트렌드 리포트 PDF 생성."""

from __future__ import annotations

from datetime import UTC, datetime

from app.agents.aggregator.report import (
    coerce_dashboard_report,
    dashboard_report_to_markdown,
)
from app.schemas.report import DashboardReportSchema
from app.services.pdf import convert_markdown_to_pdf_async


def trend_report_pdf_filename(*, post_id: str = "") -> str:
    suffix = post_id[:8] if post_id else "report"
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"B2B_Trend_Report_{suffix}_{date_part}.pdf"


async def build_trend_report_pdf(
    report: DashboardReportSchema | dict[str, object],
) -> bytes:
    """구조화 리포트를 Markdown으로 변환한 뒤 PDF 바이트를 반환한다."""
    normalized = coerce_dashboard_report(report)
    markdown = dashboard_report_to_markdown(normalized)
    return await convert_markdown_to_pdf_async(markdown)
