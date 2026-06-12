"""문화/콘텐츠 트렌드 서브 에이전트."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.aggregator.base import IntegratedData
from app.agents.aggregator.prompts import (
    CULTURE_ANALYSIS_SYSTEM_PROMPT,
    build_culture_analysis_user_prompt,
)
from app.agents.aggregator.report import invoke_gemini


async def run_culture_analysis(
    integrated_data: IntegratedData,
    *,
    critique_feedback: str | None = None,
    model: str | None = None,
) -> str:
    """8각 성향·YouTube 급상승 기반 문화/콘텐츠 격차 분석 초안을 생성한다."""
    messages = [
        SystemMessage(content=CULTURE_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(
            content=build_culture_analysis_user_prompt(
                integrated_data,
                critique_feedback=critique_feedback,
            )
        ),
    ]
    return await invoke_gemini(messages, model=model)
