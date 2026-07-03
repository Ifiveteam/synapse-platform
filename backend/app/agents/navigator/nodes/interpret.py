"""assess 노드 — 유저 발화를 취향으로 해석해 이상향(성향·도메인)을 갱신하고
종료 여부(sufficient·user_wants_finalize·턴)를 판정한다."""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.config import get_stream_writer

from app.agents.navigator.axes import (
    clamp_disposition,
    clamp_values_13,
    coerce_interest_targets,
    interest_from_portrait,
)
from app.agents.navigator.behavior_map import derive_8_from_13
from app.agents.navigator.constants import INTERPRET_TEMPERATURE
from app.agents.navigator.llm import invoke_structured_safe
from app.agents.navigator.nodes._common import (
    conversation_transcript,
    latest_user_message,
)
from app.agents.navigator.prompts.chat import build_assess_prompt
from app.agents.navigator.schemas import InterviewTurn
from app.agents.navigator.state import NavigatorState

logger = logging.getLogger(__name__)


def _should_finalize(*, force: bool, user_wants: bool) -> bool:
    """다음 단계(마무리)는 오직 사용자 의지 — 확정 버튼(force) 또는 종료 발화만.

    AI가 sufficient라고 판단해도 자동으로 넘어가지 않는다(사용자가 더 대화할 수 있게).
    sufficient는 ask 노드가 '이제 마무리해도 좋다'는 안내 멘트를 낼지에만 쓴다.
    """
    return force or user_wants


async def assess(state: NavigatorState) -> dict[str, Any]:
    """취향 인터뷰 한 턴 — 이상향 갱신 + 종료 판정."""
    writer = get_stream_writer()
    writer({"event": "status", "content": "🧭 [Navigator] 취향을 파악합니다...\n\n"})

    transcript = conversation_transcript(state) or latest_user_message(state)
    result = await invoke_structured_safe(
        system_instruction=build_assess_prompt(state),
        user_content=f"[대화]\n{transcript}\n\n위 대화를 반영해 갱신하세요."
        if transcript
        else "제 취향을 편하게 물어봐 주세요.",
        schema=InterviewTurn,
        temperature=INTERPRET_TEMPERATURE,
    )

    updates: dict[str, Any] = {"current_step": "assess"}
    cur_interest = interest_from_portrait(state.get("portrait"))
    sufficient = False
    user_wants = False

    if result is not None:
        design = result.design
        working_values = clamp_values_13(design.values())
        working_ideal = derive_8_from_13(working_values)
        working_disp = clamp_disposition(design.target_disposition.as_dict())
        working_int = coerce_interest_targets(design.target_interest, cur_interest)
        updates.update(
            {
                "working_values": working_values,
                "working_ideal": working_ideal,
                "working_disposition": working_disp,
                "working_interest": working_int,
                "ideal_reasoning": design.reasoning,
                "persona_label": design.persona_label,
                "taste_notes": result.taste_notes or state.get("taste_notes", ""),
                "missing": result.missing,
            }
        )
        sufficient = result.sufficient
        user_wants = result.user_wants_finalize
    else:
        working_disp = state.get("working_disposition")
        working_int = state.get("working_interest")
        working_ideal = state.get("working_ideal")
        working_values = state.get("working_values")

    # 성향·도메인(+폴드용 8/13) 실시간 이벤트
    writer(
        {
            "event": "ideal",
            "content": json.dumps(
                {
                    "disposition": working_disp or {},
                    "interest": working_int or {},
                    "behavior": working_ideal or {},
                    "values_temperament": working_values or {},
                },
                ensure_ascii=False,
            ),
        }
    )

    updates["sufficient"] = sufficient
    finalize = _should_finalize(
        force=bool(state.get("force_finalize", False)),
        user_wants=user_wants,
    )
    updates["decision"] = "finalize" if finalize else "ask"
    return updates
