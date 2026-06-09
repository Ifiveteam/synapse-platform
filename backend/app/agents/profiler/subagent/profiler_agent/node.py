from __future__ import annotations

from app.agents.profiler.state import ProfilerState
from app.agents.profiler.subagent.profiler_agent.analysis import (
    get_gemini_api_key,
    run_llm_analysis,
)


def profiler_agent_node(state: ProfilerState) -> dict:
    records = state["records"]
    layer_b = state["layer_b"]
    log = list(state.get("investigation_log", []))

    llm_used = bool(get_gemini_api_key())
    log.append(f"agent: llm_mode={'gemini_tools' if llm_used else 'fallback_rules'}")

    analysis = run_llm_analysis(state["user_id"], records, layer_b, log)

    return {
        "axes": analysis.axes,
        "top5_interests": analysis.top5_interests,
        "summary": analysis.summary,
        "axis_notes": analysis.axis_notes,
        "current_step": "profiler_agent",
        "investigation_log": log,
        "llm_used": llm_used,
    }
