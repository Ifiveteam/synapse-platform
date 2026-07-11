"""LLM 비교 요약."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.agents.profiler.axis_labels import HABIT_LABELS_KO, SCORE_LABELS_KO
from app.agents.profiler.sub_agent.compare.prompts import COMPARE_HUMAN, COMPARE_SYSTEM
from app.agents.profiler.sub_agent.compare.state import CompareState
from app.schemas.profiler.llm.compare import CompareNarrativeOutput


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"not serializable: {type(value)}")


def _axis_change_list(
    from_map: dict[str, Any],
    to_map: dict[str, Any],
    delta_map: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    """{axis: value} 3종을 변화 큰 순으로 [{axis, from, to, delta}]로."""
    rows = [
        {
            "axis": key,
            "from": from_map.get(key),
            "to": to_map.get(key),
            "delta": value,
        }
        for key, value in delta_map.items()
    ]
    rows.sort(key=lambda r: abs(float(r["delta"] or 0.0)), reverse=True)
    return rows[:limit]


def _compact_diff_for_llm(diff: dict[str, Any]) -> dict[str, Any]:
    scores_delta = diff.get("scores_delta") or {}
    top_scores = sorted(
        scores_delta.items(),
        key=lambda item: abs(float(item[1])),
        reverse=True,
    )[:6]
    habits_delta = diff.get("habits_delta") or {}

    return {
        # ── 1순위: 화면에서 보여주는 축 (성향 6축·관심 도메인·상위 채널) ──
        "disposition_delta": _axis_change_list(
            diff.get("disposition_from") or {},
            diff.get("disposition_to") or {},
            diff.get("disposition_delta") or {},
            limit=6,
        ),
        "interest_delta": _axis_change_list(
            diff.get("interest_from") or {},
            diff.get("interest_to") or {},
            diff.get("interest_delta") or {},
            limit=6,
        ),
        "from_top_channels": diff.get("from_top_channels") or [],
        "to_top_channels": diff.get("to_top_channels") or [],
        "shorts_ratio_delta": diff.get("shorts_ratio_delta"),
        # ── 2순위(보조): 세부 점수·습관·태그 ──
        "top_score_changes": [
            {
                "axis": key,
                "label_ko": SCORE_LABELS_KO.get(key, key),
                "delta": value,
            }
            for key, value in top_scores
        ],
        "habits_delta": {
            key: {
                "label_ko": HABIT_LABELS_KO.get(key, key),
                "delta": value,
            }
            for key, value in habits_delta.items()
        },
        "traits_added": diff.get("traits_added") or [],
        "traits_removed": diff.get("traits_removed") or [],
        "channels_added": diff.get("channels_added") or [],
        "channels_removed": diff.get("channels_removed") or [],
        "from_persona": (diff.get("from_snapshot") or {}).get("persona_label"),
        "to_persona": (diff.get("to_snapshot") or {}).get("persona_label"),
    }


async def _llm_compare_narrative(
    user_id: str,
    diff: dict[str, Any],
) -> CompareNarrativeOutput | None:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.agents.profiler.llm import invoke_gemini_structured

        from_snap = diff.get("from_snapshot") or {}
        to_snap = diff.get("to_snapshot") or {}
        compact = _compact_diff_for_llm(diff)

        human = COMPARE_HUMAN.format(
            user_id=user_id,
            from_date=from_snap.get("snapshot_date", ""),
            from_persona=from_snap.get("persona_label") or "—",
            to_date=to_snap.get("snapshot_date", ""),
            to_persona=to_snap.get("persona_label") or "—",
            from_summary=from_snap.get("summary_text") or "—",
            to_summary=to_snap.get("summary_text") or "—",
            compare_diff=json.dumps(compact, ensure_ascii=False, default=_json_default),
        )
        return await invoke_gemini_structured(
            [
                SystemMessage(content=COMPARE_SYSTEM),
                HumanMessage(content=human),
            ],
            CompareNarrativeOutput,
            temperature=0.35,
        )
    except Exception:
        return None


async def node_summarize(state: CompareState) -> dict:
    log = list(state.get("run_log") or [])

    if state.get("error"):
        return {}

    diff = state.get("diff")
    if not diff:
        return {
            "narrative": None,
            "narrative_error": "diff_missing",
            "run_log": log + ["summarize: skipped (no diff)"],
        }

    narrative = await _llm_compare_narrative(str(state["user_id"]), diff)
    if narrative is None:
        log.append("summarize: LLM failed")
        return {
            "narrative": None,
            "narrative_error": "llm_failed",
            "run_log": log,
        }

    log.append("summarize: LLM narrative ok")
    return {
        "narrative": narrative.model_dump(),
        "narrative_error": None,
        "run_log": log,
    }
