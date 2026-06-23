"""L2 프로필: catalog 조회 → 21축 점수 → insight → DB 저장 (단일 노드)."""

from __future__ import annotations

import json
import math
import uuid
from collections import Counter
from typing import Any

from app.agents.profiler.habit_metrics import habit_metrics_from_catalog_stats
from app.agents.profiler.prompt import (
    BEHAVIOR_SPIDER_HUMAN,
    BEHAVIOR_SPIDER_SYSTEM,
    PROFILE_INSIGHT_HUMAN,
    PROFILE_INSIGHT_SYSTEM,
    VALUES_TEMPERAMENT_HUMAN,
    VALUES_TEMPERAMENT_SYSTEM,
)
from app.agents.profiler.state import ProfilerState
from app.agents.shared.analysis_window import WATCH_CATALOG_WINDOW_DAYS
from app.schemas.profiler import (
    BehaviorSpiderOutput,
    ProfileInsightOutput,
    ProfileScoresOutput,
    ValuesTemperamentOutput,
)

_EDU_CATEGORIES = {"27", "28"}
_ENTERTAINMENT_CATEGORIES = {"1", "17", "23", "24"}
_NEWS_CATEGORIES = {"25"}

_BEHAVIOR_KEYS = (
    "exploration",
    "analytical",
    "creativity",
    "execution",
    "achievement_drive",
    "autonomy",
    "sociality",
    "sensitivity",
)

_LABELS_KO = {
    "exploration": "탐색",
    "analytical": "분석",
    "creativity": "창의",
    "execution": "실행",
    "achievement_drive": "성취",
    "autonomy": "자율",
    "sociality": "사회성",
    "sensitivity": "감수성",
}


_SAMPLE_LIMIT = 30
_EVIDENCE_SATURATION_K = 2.8
_LLM_VT_BLEND = 0.8
_LLM_BEHAVIOR_BLEND = 0.8
_RULE_SCORE_MARGIN_LOW = 5.0
_RULE_SCORE_MARGIN_HIGH = 28.0
_BEHAVIOR_RULE_MARGIN_LOW = 8.0
_BEHAVIOR_RULE_MARGIN_HIGH = 28.0

_VALUES_TEMPERAMENT_KEYS = (
    "self_direction",
    "stimulation",
    "achievement",
    "power",
    "security",
    "benevolence",
    "universalism",
    "hedonism",
    "conformity",
    "tradition",
    "novelty_seeking",
    "persistence",
    "self_transcendence",
)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _weighted_blend(*weighted: tuple[float, float]) -> float:
    """가중 평균 (0=무관심, 100=강한 추구 스케일)."""
    total_weight = sum(weight for _, weight in weighted)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in weighted) / total_weight


def _evidence_to_score(strength: float) -> float:
    """증거 강도(0~1) → 0~100 포화 곡선 (약한 근거도 12~15+, 상단 완만)."""
    if strength <= 0.0:
        return 0.0
    return _clamp(100.0 * (1.0 - math.exp(-_EVIDENCE_SATURATION_K * strength)))


def _rule_scores_from_stats(stats: dict[str, Any]) -> dict[str, float]:
    evidence = _axis_evidence_strength(stats)
    return {
        key: round(_evidence_to_score(evidence[key]), 1)
        for key in _VALUES_TEMPERAMENT_KEYS
    }


def _build_catalog_stats(rows) -> dict[str, Any]:
    category = Counter()
    channel = Counter()
    shorts = 0
    for row in rows:
        if row.is_shorts:
            shorts += 1
        category[row.youtube_category_id or "unknown"] += 1
        channel[row.channel] += 1
    total = len(rows) or 1
    category_stats = dict(category.most_common(20))
    return {
        "total": len(rows),
        "shorts_count": shorts,
        "long_count": len(rows) - shorts,
        "shorts_ratio": round(shorts / total, 3),
        "long_ratio": round((len(rows) - shorts) / total, 3),
        "unique_channels": len(channel),
        "category_stats": category_stats,
        "category_ratios": {
            cat: round(count / total, 3) for cat, count in category_stats.items()
        },
        "channel_top5": [
            {"channel": name, "count": count} for name, count in channel.most_common(5)
        ],
    }


def _category_weight(stats: dict[str, Any], keys: set[str]) -> float:
    cat_stats = stats.get("category_stats") or {}
    total = sum(cat_stats.values()) or 1
    matched = sum(count for cat, count in cat_stats.items() if cat in keys)
    return matched / total


def _axis_evidence_strength(stats: dict[str, Any]) -> dict[str, float]:
    """축별 양성 증거 강도 (0~1, 높을수록 해당 축 근거 있음)."""
    habits = habit_metrics_from_catalog_stats(stats)
    concentration = habits["channel_concentration"]
    diversity = habits["category_diversity"]
    shorts_ratio = float(stats.get("shorts_ratio") or 0.0)
    long_ratio = float(stats.get("long_ratio") or (1.0 - shorts_ratio))
    edu_w = _category_weight(stats, _EDU_CATEGORIES)
    news_w = _category_weight(stats, _NEWS_CATEGORIES)
    entertain_w = _category_weight(stats, _ENTERTAINMENT_CATEGORIES)
    spread = 1.0 - concentration

    return {
        "self_direction": min(1.0, diversity * 0.55 + spread * 0.45),
        "stimulation": min(1.0, shorts_ratio * 0.55 + entertain_w * 0.45),
        "achievement": min(1.0, edu_w * 0.6 + long_ratio * 0.25),
        "power": min(1.0, concentration * 0.65),
        "security": min(1.0, concentration * 0.5),
        "benevolence": min(1.0, news_w * 0.55 + entertain_w * 0.2),
        "universalism": min(1.0, news_w * 0.6 + edu_w * 0.25),
        "hedonism": min(1.0, shorts_ratio * 0.45 + entertain_w * 0.5),
        "conformity": min(1.0, concentration * 0.55),
        "tradition": min(1.0, (1.0 - diversity) * 0.45 + news_w * 0.35),
        "novelty_seeking": min(
            1.0, diversity * 0.45 + shorts_ratio * 0.25 + spread * 0.2
        ),
        "persistence": min(1.0, edu_w * 0.55 + long_ratio * 0.35),
        "self_transcendence": min(1.0, news_w * 0.5 + entertain_w * 0.15),
    }


def rule_based_values_temperament(stats: dict[str, Any]) -> ValuesTemperamentOutput:
    """1단계 폴백: catalog 증거 → 포화 곡선 0~100."""
    return ValuesTemperamentOutput(**_rule_scores_from_stats(stats))


_BEHAVIOR_SOURCE_KEYS: dict[str, tuple[str, ...]] = {
    "exploration": ("novelty_seeking", "self_direction", "stimulation"),
    "analytical": ("achievement", "universalism", "persistence"),
    "creativity": ("self_direction", "stimulation", "hedonism"),
    "execution": ("persistence", "achievement"),
    "achievement_drive": ("achievement", "persistence", "power"),
    "autonomy": ("self_direction", "novelty_seeking", "conformity"),
    "sociality": ("benevolence", "universalism", "hedonism"),
    "sensitivity": ("self_transcendence", "hedonism", "stimulation"),
}


def _blend_values_temperament(
    llm: ValuesTemperamentOutput,
    rule: ValuesTemperamentOutput,
    *,
    llm_weight: float = _LLM_VT_BLEND,
) -> ValuesTemperamentOutput:
    rule_weight = 1.0 - llm_weight
    blended = {
        key: _clamp(
            llm_weight * float(llm.model_dump()[key])
            + rule_weight * float(rule.model_dump()[key])
        )
        for key in _VALUES_TEMPERAMENT_KEYS
    }
    return ValuesTemperamentOutput(
        **{key: round(blended[key], 1) for key in _VALUES_TEMPERAMENT_KEYS}
    )


def _blend_behavior_spider(
    llm: BehaviorSpiderOutput,
    rule: BehaviorSpiderOutput,
    *,
    llm_weight: float = _LLM_BEHAVIOR_BLEND,
) -> BehaviorSpiderOutput:
    rule_weight = 1.0 - llm_weight
    blended = {
        key: _clamp(
            llm_weight * float(llm.model_dump()[key])
            + rule_weight * float(rule.model_dump()[key])
        )
        for key in _BEHAVIOR_KEYS
    }
    return BehaviorSpiderOutput(
        **{key: round(blended[key], 1) for key in _BEHAVIOR_KEYS}
    )


def _ensure_values_spread(
    data: dict[str, float], rule_scores: dict[str, float]
) -> dict[str, float]:
    """LLM 몰림 방지 — rule 대비 과대 축만 rule+margin 안으로."""
    if max(data.values()) - min(data.values()) >= 24.0:
        return data
    ranked = sorted(_VALUES_TEMPERAMENT_KEYS, key=lambda k: data[k], reverse=True)
    for key in ranked[3:]:
        ceiling = rule_scores[key] + _RULE_SCORE_MARGIN_HIGH + 4.0
        if data[key] > ceiling:
            data[key] = ceiling
    return data


def calibrate_values_temperament(
    vt: ValuesTemperamentOutput, stats: dict[str, Any]
) -> ValuesTemperamentOutput:
    """rule(포화 곡선) ± margin 안으로 clamp — 하드 cap 제거."""
    rule_scores = _rule_scores_from_stats(stats)
    data = {key: float(vt.model_dump()[key]) for key in _VALUES_TEMPERAMENT_KEYS}

    for key in _VALUES_TEMPERAMENT_KEYS:
        rule = rule_scores[key]
        lo = max(0.0, rule - _RULE_SCORE_MARGIN_LOW)
        hi = min(100.0, rule + _RULE_SCORE_MARGIN_HIGH)
        data[key] = _clamp(data[key], lo, hi)

    data = _ensure_values_spread(data, rule_scores)
    return ValuesTemperamentOutput(
        **{key: round(_clamp(data[key]), 1) for key in _VALUES_TEMPERAMENT_KEYS}
    )


def calibrate_behavior_spider(
    behavior: BehaviorSpiderOutput,
    vt: ValuesTemperamentOutput,
    rule_behavior: BehaviorSpiderOutput | None = None,
) -> BehaviorSpiderOutput:
    """rule behavior ± margin — 1단계와 불일치하는 LLM 행동 점수 완화."""
    anchor = rule_behavior or rule_based_behavior_spider(vt)
    anchor_map = anchor.model_dump()
    data = behavior.model_dump()
    for key in _BEHAVIOR_KEYS:
        rule = float(anchor_map[key])
        lo = max(0.0, rule - _BEHAVIOR_RULE_MARGIN_LOW)
        hi = min(100.0, rule + _BEHAVIOR_RULE_MARGIN_HIGH)
        data[key] = _clamp(float(data[key]), lo, hi)
    return BehaviorSpiderOutput(
        **{key: round(float(data[key]), 1) for key in _BEHAVIOR_KEYS}
    )


def rule_based_behavior_spider(vt: ValuesTemperamentOutput) -> BehaviorSpiderOutput:
    """2단계 폴백: 1단계 추구 강도 가중합."""
    exploration = _clamp(
        _weighted_blend(
            (vt.novelty_seeking, 0.55),
            (vt.self_direction, 0.28),
            (vt.stimulation, 0.17),
        )
    )
    analytical = _clamp(
        _weighted_blend(
            (vt.achievement, 0.32),
            (vt.universalism, 0.33),
            (vt.persistence, 0.25),
        )
    )
    creativity = _clamp(
        _weighted_blend(
            (vt.self_direction, 0.38),
            (vt.stimulation, 0.34),
            (vt.hedonism, 0.18),
        )
    )
    execution = _clamp(_weighted_blend((vt.persistence, 0.52), (vt.achievement, 0.38)))
    achievement_drive = _clamp(
        _weighted_blend(
            (vt.achievement, 0.52),
            (vt.persistence, 0.33),
            (vt.power, 0.15),
        )
    )
    autonomy = _clamp(
        vt.self_direction * 0.45
        + vt.novelty_seeking * 0.35
        + (100.0 - vt.conformity) * 0.2
    )
    sociality = _clamp(
        _weighted_blend(
            (vt.benevolence, 0.42),
            (vt.universalism, 0.28),
            (vt.hedonism, 0.18),
        )
    )
    sensitivity = _clamp(
        _weighted_blend(
            (vt.self_transcendence, 0.38),
            (vt.hedonism, 0.28),
            (vt.stimulation, 0.22),
        )
    )

    return BehaviorSpiderOutput(
        exploration=round(exploration, 1),
        analytical=round(analytical, 1),
        creativity=round(creativity, 1),
        execution=round(execution, 1),
        achievement_drive=round(achievement_drive, 1),
        autonomy=round(autonomy, 1),
        sociality=round(sociality, 1),
        sensitivity=round(sensitivity, 1),
    )


def merge_profile_scores(
    vt: ValuesTemperamentOutput, behavior: BehaviorSpiderOutput
) -> ProfileScoresOutput:
    return ProfileScoresOutput(**vt.model_dump(), **behavior.model_dump())


def rule_based_scores(stats: dict[str, Any]) -> ProfileScoresOutput:
    vt = rule_based_values_temperament(stats)
    behavior = rule_based_behavior_spider(vt)
    return merge_profile_scores(vt, behavior)


_PERSONA_ADJ: dict[str, str] = {
    "exploration": "호기심 많은",
    "analytical": "분석적인",
    "creativity": "창의적인",
    "execution": "실행적인",
    "achievement_drive": "성취 지향",
    "autonomy": "자기주도적인",
    "sociality": "사교적인",
    "sensitivity": "감수성 높은",
}

_PERSONA_NOUN: dict[str, str] = {
    "exploration": "탐색가",
    "analytical": "분석가",
    "creativity": "창작 소비자",
    "execution": "실천가",
    "achievement_drive": "성장 추구자",
    "autonomy": "큐레이터",
    "sociality": "관람자",
    "sensitivity": "감성 소비자",
}


def _template_persona_label(top_behavior_key: str) -> str:
    adj = _PERSONA_ADJ.get(top_behavior_key, "균형적인")
    noun = _PERSONA_NOUN.get(top_behavior_key, "소비자")
    return f"{adj} {noun}"


def _template_insight(
    scores: ProfileScoresOutput, stats: dict[str, Any]
) -> ProfileInsightOutput:
    ranked = sorted(
        ((key, getattr(scores, key)) for key in _BEHAVIOR_KEYS),
        key=lambda item: item[1],
        reverse=True,
    )
    top = ranked[:3]
    traits = [_LABELS_KO[key] for key, _ in top]
    total = stats.get("total") or 0
    shorts_ratio = stats.get("shorts_ratio") or 0.0
    persona = _template_persona_label(top[0][0])
    if shorts_ratio > 0.5 and top[0][0] != "exploration":
        persona = "숏폼 중심 큐레이터"

    summary = (
        f"최근 {total}건의 시청 기록을 바탕으로, "
        f"{'·'.join(traits)} 성향이 두드러집니다. "
        f"숏폼 비중은 {shorts_ratio:.0%}입니다."
    )
    reasoning = (
        f"상위 행동 축은 {', '.join(f'{_LABELS_KO[k]}({v:.0f})' for k, v in top)} 입니다. "
        "카테고리·채널 분포와 영상 요약 샘플을 근거로 산출했습니다."
    )
    return ProfileInsightOutput(
        summary_text=summary,
        persona_label=persona,
        behavior_reasoning=reasoning,
        dominant_traits=traits,
        tone_of_user="호기심과 실용성을 오가는 디지털 소비 패턴",
    )


def _catalog_sample_dict(row, analysis) -> dict[str, Any]:
    sample: dict[str, Any] = {
        "catalog_id": str(row.id),
        "title": row.title,
        "channel": row.channel,
        "youtube_category_id": row.youtube_category_id,
        "is_shorts": row.is_shorts,
    }
    if analysis:
        sample.update(
            {
                "summary_kr": analysis.summary_kr,
                "tones": analysis.tones,
                "intents": analysis.intents,
                "value_signals": analysis.value_signals,
            }
        )
    return sample


def _select_analysis_samples(
    rows: list,
    analyses: list,
    *,
    limit: int = _SAMPLE_LIMIT,
) -> list[dict[str, Any]]:
    """video_analysis 있는 catalog 우선, 부족 시 최근 catalog로 채움."""
    rows_by_id = {row.id: row for row in rows}
    by_catalog = {a.catalog_id: a for a in analyses}
    picked: list = []
    seen: set[uuid.UUID] = set()

    for analysis in analyses:
        if len(picked) >= limit:
            break
        row = rows_by_id.get(analysis.catalog_id)
        if row is None or row.id in seen:
            continue
        seen.add(row.id)
        picked.append(row)

    for row in rows:
        if len(picked) >= limit:
            break
        if row.id in seen:
            continue
        seen.add(row.id)
        picked.append(row)

    return [_catalog_sample_dict(row, by_catalog.get(row.id)) for row in picked]


async def _load_context(
    user_id: uuid.UUID,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from app.core.database.session import AsyncSessionLocal
    from app.repositories.profiler_repository import (
        fetch_recent_catalog_rows,
        fetch_video_analyses_for_user,
    )

    async with AsyncSessionLocal() as session:
        # 누적 catalog 전체가 아니라 최근 윈도우(인덱서와 공유 상수)만 채점에 사용.
        rows = await fetch_recent_catalog_rows(
            session, user_id, WATCH_CATALOG_WINDOW_DAYS
        )
        stats = _build_catalog_stats(rows)
        analyses = await fetch_video_analyses_for_user(session, user_id, limit=50)

    samples = _select_analysis_samples(rows, analyses)
    return stats, samples


async def _llm_values_temperament(
    user_id: str,
    stats: dict[str, Any],
    analysis_samples: list[dict[str, Any]],
) -> ValuesTemperamentOutput | None:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.agents.aggregator.llm.gemini import invoke_gemini_structured

        human = VALUES_TEMPERAMENT_HUMAN.format(
            user_id=user_id,
            catalog_stats=json.dumps(stats, ensure_ascii=False),
            analysis_samples=json.dumps(analysis_samples, ensure_ascii=False),
        )
        return await invoke_gemini_structured(
            [
                SystemMessage(content=VALUES_TEMPERAMENT_SYSTEM),
                HumanMessage(content=human),
            ],
            ValuesTemperamentOutput,
        )
    except Exception:
        return None


async def _llm_behavior_spider(
    user_id: str,
    vt: ValuesTemperamentOutput,
    stats: dict[str, Any],
) -> BehaviorSpiderOutput | None:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.agents.aggregator.llm.gemini import invoke_gemini_structured

        human = BEHAVIOR_SPIDER_HUMAN.format(
            user_id=user_id,
            values_temperament=vt.model_dump_json(),
            catalog_stats=json.dumps(stats, ensure_ascii=False),
        )
        return await invoke_gemini_structured(
            [
                SystemMessage(content=BEHAVIOR_SPIDER_SYSTEM),
                HumanMessage(content=human),
            ],
            BehaviorSpiderOutput,
        )
    except Exception:
        return None


async def _llm_profile_scores(
    user_id: str,
    stats: dict[str, Any],
    analysis_samples: list[dict[str, Any]],
) -> tuple[ProfileScoresOutput | None, bool, bool]:
    """2단계 LLM 점수 산출. (scores, stage1_llm, stage2_llm)."""
    rule_vt = rule_based_values_temperament(stats)
    vt_llm = await _llm_values_temperament(user_id, stats, analysis_samples)
    stage1_llm = vt_llm is not None
    if vt_llm is None:
        vt = rule_vt
    else:
        vt = _blend_values_temperament(vt_llm, rule_vt)
    if stats.get("total", 0) > 0:
        vt = calibrate_values_temperament(vt, stats)

    rule_behavior = rule_based_behavior_spider(vt)
    behavior_llm = await _llm_behavior_spider(user_id, vt, stats)
    stage2_llm = behavior_llm is not None
    if behavior_llm is None:
        behavior = rule_behavior
    else:
        behavior = _blend_behavior_spider(behavior_llm, rule_behavior)
    if stats.get("total", 0) > 0:
        behavior = calibrate_behavior_spider(behavior, vt, rule_behavior)

    if not stage1_llm and not stage2_llm:
        return None, False, False
    return merge_profile_scores(vt, behavior), stage1_llm, stage2_llm


async def _llm_insight(
    user_id: str,
    scores: ProfileScoresOutput,
    stats: dict[str, Any],
) -> ProfileInsightOutput | None:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.agents.aggregator.llm.gemini import invoke_gemini_structured

        human = PROFILE_INSIGHT_HUMAN.format(
            user_id=user_id,
            scores=scores.model_dump_json(),
            catalog_stats=json.dumps(stats, ensure_ascii=False),
        )
        return await invoke_gemini_structured(
            [
                SystemMessage(content=PROFILE_INSIGHT_SYSTEM),
                HumanMessage(content=human),
            ],
            ProfileInsightOutput,
        )
    except Exception:
        return None


async def build_profile_node(state: ProfilerState) -> dict[str, Any]:
    user_id = uuid.UUID(str(state["user_id"]))
    log = list(state.get("investigation_log") or [])

    try:
        stats, samples = await _load_context(user_id)
        analyzed_in_samples = sum(1 for s in samples if s.get("summary_kr"))
        log.append(
            f"build_profile: catalog={stats['total']} "
            f"samples={len(samples)} analyzed_in_samples={analyzed_in_samples} "
            f"shorts_ratio={stats.get('shorts_ratio', 0)}"
        )
    except Exception as exc:
        log.append(f"build_profile load error: {exc}")
        return {
            "catalog_stats": {"total": 0},
            "analysis_samples": [],
            "error": str(exc),
            "current_step": "build_profile",
            "investigation_log": log,
        }

    if stats.get("total", 0) == 0:
        scores = rule_based_scores(stats)
        insight = _template_insight(scores, stats)
        llm_used = False
        log.append("build_profile: empty catalog, rule fallback only")
    else:
        scores, stage1_llm, stage2_llm = await _llm_profile_scores(
            state["user_id"], stats, samples
        )
        llm_used = stage1_llm or stage2_llm
        if scores is None:
            scores = rule_based_scores(stats)
            log.append("build_profile: scores rule fallback (both stages)")
        else:
            parts = []
            if stage1_llm:
                parts.append("values/temperament gemini")
            else:
                parts.append("values/temperament rule")
            if stage2_llm:
                parts.append("behavior gemini")
            else:
                parts.append("behavior rule")
            log.append(f"build_profile: {' + '.join(parts)}")

        insight = None
        if llm_used:
            insight = await _llm_insight(state["user_id"], scores, stats)
        if insight is None:
            insight = _template_insight(scores, stats)
            log.append("build_profile: insight template")
        else:
            log.append("build_profile: insight gemini")

    supporting = {
        "catalog_stats": stats,
        "analysis_samples": samples[:10],
        "llm_used": llm_used,
    }

    try:
        from app.core.database.session import AsyncSessionLocal
        from app.repositories.profiler_repository import insert_profile_snapshot

        async with AsyncSessionLocal() as session:
            snapshot_id = await insert_profile_snapshot(
                session, user_id, scores, insight, supporting
            )
            await session.commit()
        log.append(f"build_profile: stored snapshot={snapshot_id}")
        return {
            "catalog_stats": stats,
            "analysis_samples": samples,
            "profile_scores": scores,
            "profile_insight": insight,
            "supporting_evidence": supporting,
            "snapshot_id": str(snapshot_id),
            "llm_used": llm_used,
            "current_step": "build_profile",
            "investigation_log": log,
        }
    except Exception as exc:
        log.append(f"build_profile store error: {exc}")
        return {
            "catalog_stats": stats,
            "analysis_samples": samples,
            "profile_scores": scores,
            "profile_insight": insight,
            "supporting_evidence": supporting,
            "llm_used": llm_used,
            "error": str(exc),
            "current_step": "build_profile",
            "investigation_log": log,
        }
