"""Aggregator 에이전트 프롬프트 (하위 호환 re-export)."""

from app.agents.aggregator.prompts.culture import (
    CULTURE_ANALYSIS_SYSTEM_PROMPT,
    build_culture_analysis_user_prompt,
)
from app.agents.aggregator.prompts.market import (
    MARKET_ANALYSIS_SYSTEM_PROMPT,
    build_market_analysis_user_prompt,
)
from app.agents.aggregator.prompts.master import (
    MASTER_REPORT_SYSTEM_PROMPT,
    build_master_report_user_prompt,
)
from app.agents.aggregator.prompts.shared import COGNITIVE_PROFILE_AXIS_KEYS
from app.agents.aggregator.prompts.verify import (
    VERIFY_REPORT_SYSTEM_PROMPT,
    build_verify_report_user_prompt,
)

__all__ = [
    "COGNITIVE_PROFILE_AXIS_KEYS",
    "CULTURE_ANALYSIS_SYSTEM_PROMPT",
    "MARKET_ANALYSIS_SYSTEM_PROMPT",
    "MASTER_REPORT_SYSTEM_PROMPT",
    "VERIFY_REPORT_SYSTEM_PROMPT",
    "build_culture_analysis_user_prompt",
    "build_market_analysis_user_prompt",
    "build_master_report_user_prompt",
    "build_verify_report_user_prompt",
]
