"""Gemini tool loop, structured profiling output, and rule-based fallback."""

from __future__ import annotations

import json
import os
from collections import Counter

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.profiler.base import (
    SYNAPSE_AXIS_KEYS,
    IndexedRecord,
    LayerB,
    ProfilerAnalysisOutput,
    Synapse8Axes,
    Top5Interest,
)
from app.agents.profiler.nodes.layer_b import complete_layer_b
from app.agents.profiler.prompt import (
    INVESTIGATION_HUMAN_TEMPLATE,
    INVESTIGATION_SYSTEM_PROMPT,
    PROFILER_AGENT_SYSTEM_PROMPT,
    PROFILER_ANALYSIS_HUMAN_TEMPLATE,
)
from app.agents.profiler.state import ProfilerState
from app.agents.profiler.tools import (
    TAG_AXIS_WEIGHTS,
    build_investigation_tools,
    filter_search_records,
    filter_watch_records,
    get_channel_breakdown,
    get_sample_records,
    get_search_queries,
    get_tag_distribution,
)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
MAX_TOOL_ITERATIONS = 1

_TOOL_TO_EVIDENCE_KEY: dict[str, str] = {
    "get_channel_breakdown": "channel_breakdown",
    "get_search_queries": "search_queries",
    "get_tag_distribution": "tag_distribution",
    "get_sample_records": "sample_records",
}

_MAX_CHANNELS = 10
_MAX_TAGS = 15
_MAX_QUERIES = 10
_MAX_SAMPLES = 6


def get_gemini_api_key() -> str | None:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _top_axes(axes: Synapse8Axes, count: int = 2) -> list[str]:
    axis_values = [getattr(axes, key) for key in SYNAPSE_AXIS_KEYS]
    ranked = sorted(
        zip(SYNAPSE_AXIS_KEYS, axis_values, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    return [key for key, _ in ranked[:count]]


def _tool_result_content(result: object) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _sample_payload(records: list[IndexedRecord]) -> list[dict[str, object]]:
    return [
        {
            "source_type": record.source_type,
            "title": record.title,
            "query": record.query,
            "channel": record.channel,
            "tags": record.tags,
            "duration_sec": record.duration_sec,
        }
        for record in records
    ]


def _build_investigation_evidence(records: list[IndexedRecord]) -> dict[str, object]:
    channels = get_channel_breakdown(records)
    tags = get_tag_distribution(records)
    return {
        "channel_breakdown": dict(list(channels.items())[:_MAX_CHANNELS]),
        "search_queries": get_search_queries(records)[:_MAX_QUERIES],
        "tag_distribution": dict(list(tags.items())[:_MAX_TAGS]),
        "sample_records": _sample_payload(get_sample_records(records, _MAX_SAMPLES)),
    }


def _cap_investigation_evidence(evidence: dict[str, object]) -> dict[str, object]:
    capped = dict(evidence)
    channels = capped.get("channel_breakdown")
    if isinstance(channels, dict):
        capped["channel_breakdown"] = dict(list(channels.items())[:_MAX_CHANNELS])

    tags = capped.get("tag_distribution")
    if isinstance(tags, dict):
        capped["tag_distribution"] = dict(list(tags.items())[:_MAX_TAGS])

    queries = capped.get("search_queries")
    if isinstance(queries, list):
        capped["search_queries"] = queries[:_MAX_QUERIES]

    samples = capped.get("sample_records")
    if isinstance(samples, list):
        capped["sample_records"] = samples[:_MAX_SAMPLES]

    return capped


def _merge_tool_results(
    base: dict[str, object],
    tool_results: dict[str, str],
) -> dict[str, object]:
    merged = dict(base)
    for tool_name, content in tool_results.items():
        key = _TOOL_TO_EVIDENCE_KEY.get(tool_name)
        if key is None:
            continue
        try:
            merged[key] = json.loads(content)
        except json.JSONDecodeError:
            continue
    return _cap_investigation_evidence(merged)


def _evidence_json_sections(evidence: dict[str, object]) -> dict[str, str]:
    return {
        key: json.dumps(evidence.get(key, {}), ensure_ascii=False, indent=2)
        for key in (
            "channel_breakdown",
            "search_queries",
            "tag_distribution",
            "sample_records",
        )
    }


def _score_from_tags(records: list[IndexedRecord]) -> dict[str, float]:
    scores = {key: 35.0 for key in SYNAPSE_AXIS_KEYS}
    for record in records:
        weight = 2.0 if record.source_type == "watch" else 1.2
        if record.is_shorts:
            weight *= 0.8
        for tag in record.tags:
            for axis, delta in TAG_AXIS_WEIGHTS.get(tag, {}).items():
                scores[axis] = scores.get(axis, 35.0) + delta * 8 * weight

    watches = filter_watch_records(records)
    if watches:
        avg_duration = sum(r.duration_sec or 0 for r in watches) / len(watches)
        if avg_duration >= 900:
            scores["depth_immersion"] += 15
        elif avg_duration >= 600:
            scores["depth_immersion"] += 8
        shorts_ratio = sum(1 for r in watches if r.is_shorts) / len(watches)
        scores["entertainment_release"] += shorts_ratio * 20
        scores["depth_immersion"] -= shorts_ratio * 12

    searches = filter_search_records(records)
    unique_queries = len(set(get_search_queries(records)))
    scores["intellectual_curiosity"] += min(unique_queries, 8) * 2
    scores["practical_orientation"] += min(len(searches), 6) * 1.5

    return {key: _clamp(scores[key]) for key in SYNAPSE_AXIS_KEYS}


def _build_top5_from_records(records: list[IndexedRecord]) -> list[Top5Interest]:
    label_scores: Counter[str] = Counter()
    evidence_map: dict[str, list[str]] = {}

    for record in records:
        if record.source_type == "watch" and record.channel:
            label = record.channel
            label_scores[label] += record.duration_sec or 60
            evidence_map.setdefault(label, [])
            if record.title and len(evidence_map[label]) < 2:
                evidence_map[label].append(record.title)
        elif record.source_type == "search" and record.query:
            label = f"검색: {record.query}"
            label_scores[label] += 30
            evidence_map.setdefault(label, [record.query])
        elif record.source_type == "scrap" and record.title:
            label = f"스크랩: {record.title}"
            label_scores[label] += 25
            evidence_map.setdefault(label, [])
            if len(evidence_map[label]) < 2:
                evidence_map[label].append(record.title)

    top_items = label_scores.most_common(5)
    max_score = top_items[0][1] if top_items else 1
    return [
        Top5Interest(
            rank=idx,
            label=label,
            score=round(score / max_score, 3),
            evidence=evidence_map.get(label, [])[:2],
        )
        for idx, (label, score) in enumerate(top_items, start=1)
    ]


def fallback_analysis(
    user_id: str,
    records: list[IndexedRecord],
    layer_b: LayerB,
    investigation_log: list[str],
) -> ProfilerAnalysisOutput:
    scores = _score_from_tags(records)
    if layer_b.viewing_concentration > 0.65:
        scores["social_awareness"] = _clamp(scores["social_awareness"] + 10)
        scores["intellectual_curiosity"] = _clamp(scores["intellectual_curiosity"] - 8)
    if layer_b.viewing_concentration > 0.55:
        scores["depth_immersion"] = _clamp(scores["depth_immersion"] + 6)

    axes = Synapse8Axes(**{key: int(round(scores[key])) for key in SYNAPSE_AXIS_KEYS})
    top5 = _build_top5_from_records(records)
    dominant = _top_axes(axes)
    summary = (
        f"{user_id} 사용자는 {', '.join(dominant)} 성향이 "
        f"두드러지는 소비 패턴을 보입니다. "
        f"채널 편중도 {layer_b.viewing_concentration:.0%}, "
        f"검색 활동 {layer_b.search_active_ratio:.0%}, "
        f"탐색 깊이 {layer_b.exploration_depth:.0%}입니다. "
        f"(규칙 기반 분석 — Gemini API 키 미설정)"
    )
    axis_notes = {
        key: f"{key} 점수 {getattr(axes, key)} — 태그·시청 패턴 기반 추정"
        for key in SYNAPSE_AXIS_KEYS
    }
    investigation_log.append("fallback: rule-based axis scoring applied")
    return ProfilerAnalysisOutput(
        axes=axes,
        top5_interests=top5,
        summary=summary,
        axis_notes=axis_notes,
    )


def run_llm_analysis(
    user_id: str,
    records: list[IndexedRecord],
    layer_b: LayerB,
    investigation_log: list[str],
) -> ProfilerAnalysisOutput:
    api_key = get_gemini_api_key()

    if not api_key:
        return fallback_analysis(user_id, records, layer_b, investigation_log)

    tools = build_investigation_tools(records)
    tool_by_name = {tool.name: tool for tool in tools}

    model = ChatGoogleGenerativeAI(
        model=get_gemini_model(),
        temperature=0.2,
        google_api_key=api_key,
    )

    llm_with_tools = model.bind_tools(tools)
    watch_count = len(filter_watch_records(records))
    search_count = len(filter_search_records(records))

    messages = [
        SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT),
        HumanMessage(
            content=INVESTIGATION_HUMAN_TEMPLATE.format(
                user_id=user_id,
                record_summary=(
                    f"total={len(records)}, watch={watch_count}, search={search_count}"
                ),
                layer_b_json=layer_b.model_dump_json(),
            )
        ),
    ]

    investigation_log.append("agent: llm_tool_loop_start")
    collected_tool_results: dict[str, str] = {}

    for _ in range(MAX_TOOL_ITERATIONS):
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        tool_calls = getattr(ai_message, "tool_calls", None) or []
        if not tool_calls:
            investigation_log.append("agent: tool_loop_no_calls")
            break

        for tool_call in tool_calls:
            name = tool_call["name"]
            tool = tool_by_name.get(name)
            if tool is None:
                content = f"unknown tool: {name}"
            else:
                content = _tool_result_content(tool.invoke(tool_call.get("args") or {}))
            collected_tool_results[name] = content
            investigation_log.append(f"tool:{name}")
            messages.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))

    investigation_log.append("agent: tool_loop_complete")

    evidence = _merge_tool_results(
        _build_investigation_evidence(records),
        collected_tool_results,
    )
    if not collected_tool_results:
        investigation_log.append("agent: evidence_backfill")

    sections = _evidence_json_sections(evidence)
    human = PROFILER_ANALYSIS_HUMAN_TEMPLATE.format(
        user_id=user_id,
        layer_b_json=layer_b.model_dump_json(indent=2),
        investigation_log="\n".join(f"- {line}" for line in investigation_log),
        record_summary=(
            f"total={len(records)}, watch={watch_count}, search={search_count}"
        ),
        channel_breakdown=sections["channel_breakdown"],
        search_queries=sections["search_queries"],
        tag_distribution=sections["tag_distribution"],
        sample_records=sections["sample_records"],
    )

    final_messages = [
        SystemMessage(content=PROFILER_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=human),
    ]

    structured = model.with_structured_output(ProfilerAnalysisOutput)
    result = structured.invoke(final_messages)

    if isinstance(result, ProfilerAnalysisOutput):
        return result

    return ProfilerAnalysisOutput.model_validate(result)


def profile_llm_node(state: ProfilerState) -> dict:
    records = state["records"]
    layer_b = state["layer_b"]
    log = list(state.get("investigation_log", []))

    llm_used = bool(get_gemini_api_key())
    log.append(f"agent: llm_mode={'gemini_tools' if llm_used else 'fallback_rules'}")

    analysis = run_llm_analysis(state["user_id"], records, layer_b, log)
    layer_b = complete_layer_b(layer_b, analysis.axes)
    log.append(f"layer_b: taste_diversity_index={layer_b.taste_diversity_index}")

    return {
        "axes": analysis.axes,
        "top5_interests": analysis.top5_interests,
        "summary": analysis.summary,
        "axis_notes": analysis.axis_notes,
        "layer_b": layer_b,
        "current_step": "profile_llm",
        "investigation_log": log,
        "llm_used": llm_used,
    }
