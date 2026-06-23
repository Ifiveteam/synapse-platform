"""매크로 시장·언론 경제 서브 에이전트."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.aggregator.base import IntegratedData
from app.agents.aggregator.prompts import (
    MARKET_ANALYSIS_SYSTEM_PROMPT,
    build_market_analysis_user_prompt,
)
from app.agents.aggregator.report import invoke_gemini


async def run_market_analysis(
    integrated_data: IntegratedData,
    *,
    critique_feedback: str | None = None,
    model: str | None = None,
) -> str:
    """Google RSS·네이버 뉴스 RSS 기반 매크로 시장 분석 초안을 생성한다."""
    messages = [
        SystemMessage(content=MARKET_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(
            content=build_market_analysis_user_prompt(
                integrated_data,
                critique_feedback=critique_feedback,
            )
        ),
    ]
    return await invoke_gemini(messages, model=model)
