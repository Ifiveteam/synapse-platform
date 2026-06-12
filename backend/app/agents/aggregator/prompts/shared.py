"""Aggregator 프롬프트 공유 상수·유틸."""

from __future__ import annotations

import json
from typing import Any

COGNITIVE_PROFILE_AXIS_KEYS: tuple[str, ...] = (
    "intellectual_curiosity",
    "self_improvement",
    "social_awareness",
    "depth_immersion",
    "practical_orientation",
    "emotional_comfort",
    "creative_expression",
    "entertainment_release",
)

SUB_AGENT_REVISION_TEMPLATE = """\
## 검수 반려 피드백 (초안 재작성)
아래 피드백을 반영하여 분석 초안을 **처음부터 다시** 작성하세요.

{critique_feedback}
"""


def json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_sub_agent_revision_section(critique_feedback: str | None) -> str:
    if critique_feedback and critique_feedback.strip():
        return SUB_AGENT_REVISION_TEMPLATE.format(
            critique_feedback=critique_feedback.strip()
        )
    return ""
