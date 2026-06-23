"""interpret 노드 — 유저 메시지를 해석해 조율 중인 이상향(working_ideal)을 갱신한다."""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.config import get_stream_writer

from app.agents.navigator.behavior_map import derive_8_from_13
from app.agents.navigator.constants import INTERPRET_TEMPERATURE
from app.agents.navigator.gemini import invoke_structured_safe
from app.agents.navigator.ideal import clamp_values_13
from app.agents.navigator.nodes._common import latest_user_message
from app.agents.navigator.prompts.chat import build_interpret_prompt
from app.agents.navigator.schemas import IdealAdjustment
from app.agents.navigator.state import NavigatorState

logger = logging.getLogger(__name__)


async def interpret(state: NavigatorState) -> dict[str, Any]:
    """유저 의도를 Structured Output으로 추출해 working_ideal을 조정한다."""
    writer = get_stream_writer()
    writer({"event": "status", "content": "🧭 [Navigator] 이상향을 조율합니다...\n\n"})

    user_message = latest_user_message(state)
    adjustment = await invoke_structured_safe(
        system_instruction=build_interpret_prompt(state),
        user_content=user_message or "현재 이상향을 설명해줘.",
        schema=IdealAdjustment,
        temperature=INTERPRET_TEMPERATURE,
    )

    updates: dict[str, Any] = {"current_step": "interpret"}

    if adjustment is not None and adjustment.changed:
        working_values = clamp_values_13(adjustment.updated_design.values())
        working_ideal = derive_8_from_13(working_values)
        updates["working_values"] = working_values
        updates["working_ideal"] = working_ideal
        updates["ideal_reasoning"] = adjustment.updated_design.reasoning
    else:
        working_values = state.get("working_values")
        working_ideal = state.get("working_ideal")

    # 레이더(8축)·바(13축) 동기화용 ideal 이벤트 (토큰 아님 → DB 미저장)
    if working_ideal or working_values:
        writer(
            {
                "event": "ideal",
                "content": json.dumps(
                    {
                        "behavior": working_ideal or {},
                        "values_temperament": working_values or {},
                    },
                    ensure_ascii=False,
                ),
            }
        )

    return updates
