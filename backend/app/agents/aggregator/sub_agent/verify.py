"""시니어 검수자 서브 에이전트."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.aggregator.base import IntegratedData
from app.agents.aggregator.prompts import (
    VERIFY_REPORT_SYSTEM_PROMPT,
    build_verify_report_user_prompt,
)
from app.agents.aggregator.report import (
    coerce_dashboard_report,
    invoke_gemini_structured,
)
from app.agents.aggregator.sub_agent.schemas import VerificationResult
from app.schemas.report import DashboardReportSchema


async def run_report_verification(
    report_json: DashboardReportSchema | dict[str, object],
    integrated_data: IntegratedData,
    *,
    model: str | None = None,
) -> VerificationResult:
    """최종 JSON 리포트를 Pydantic Structured Output으로 검수한다."""
    report = coerce_dashboard_report(report_json)
    messages = [
        SystemMessage(content=VERIFY_REPORT_SYSTEM_PROMPT),
        HumanMessage(
            content=build_verify_report_user_prompt(
                report.model_dump(),
                integrated_data,
            )
        ),
    ]
    return await invoke_gemini_structured(
        messages,
        VerificationResult,
        model=model,
        temperature=0.2,
    )
