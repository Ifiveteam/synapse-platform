"""Aggregator B2B 리포트 생성·변환 (하위 호환 re-export)."""

from app.agents.aggregator.llm.gemini import invoke_gemini, invoke_gemini_structured
from app.agents.aggregator.report.generator import generate_fused_b2b_report
from app.agents.aggregator.report.markdown import (
    coerce_dashboard_report,
    dashboard_report_to_markdown,
)

__all__ = [
    "coerce_dashboard_report",
    "dashboard_report_to_markdown",
    "generate_fused_b2b_report",
    "invoke_gemini",
    "invoke_gemini_structured",
]
