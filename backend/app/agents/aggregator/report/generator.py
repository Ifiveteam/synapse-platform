"""마스터 에이전트 B2B 대시보드 리포트 생성."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.aggregator.base import IntegratedData
from app.agents.aggregator.llm.gemini import (
    PRIMARY_GEMINI_MODEL,
    invoke_gemini_structured,
)
from app.agents.aggregator.prompts import (
    MASTER_REPORT_SYSTEM_PROMPT,
    build_master_report_user_prompt,
)
from app.schemas.report import DashboardReportSchema


async def generate_fused_b2b_report(
    integrated_data: IntegratedData,
    *,
    culture_analysis: str,
    market_analysis: str,
    critique_feedback: str | None = None,
    model: str | None = None,
) -> DashboardReportSchema:
    """서브 에이전트 초안을 융합하여 최종 B2B 대시보드 JSON 리포트를 생성한다."""
    messages = [
        SystemMessage(content=MASTER_REPORT_SYSTEM_PROMPT),
        HumanMessage(
            content=build_master_report_user_prompt(
                integrated_data,
                culture_analysis=culture_analysis,
                market_analysis=market_analysis,
                critique_feedback=critique_feedback,
            )
        ),
    ]
    return await invoke_gemini_structured(
        messages,
        DashboardReportSchema,
        model=model or PRIMARY_GEMINI_MODEL,
        temperature=0.3,
    )
