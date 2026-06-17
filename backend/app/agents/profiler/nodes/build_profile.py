"""L2 프로필: catalog 조회 → 21축 점수 → insight → DB 저장 (단일 노드)."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from typing import Any

from app.agents.profiler.prompt import (
    BEHAVIOR_SPIDER_HUMAN,
    BEHAVIOR_SPIDER_SYSTEM,
    PROFILE_INSIGHT_HUMAN,
    PROFILE_INSIGHT_SYSTEM,
    VALUES_TEMPERAMENT_HUMAN,
    VALUES_TEMPERAMENT_SYSTEM,
)
from app.agents.profiler.state import ProfilerState
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


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


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


def _habits_from_stats(stats: dict[str, Any]) -> tuple[float, float, float]:
    """편중도, 탐색깊이, 다양성(0~1) — catalog_stats에서 직접 산출."""
    total = stats.get("total") or 0
    if total == 0:
        return 0.5, 0.0, 0.0
    top5 = stats.get("channel_top5") or []
    top_count = top5[0]["count"] if top5 else 0
    concentration = min(1.0, top_count / total)
    unique_channels = stats.get("unique_channels") or 1
    exploration_depth = min(1.0, unique_channels / max(total, 1) * 3)
    n_categories = len(stats.get("category_stats") or {})
    diversity = min(100.0, 20.0 + n_categories * 6.0) / 100.0
    return concentration, exploration_depth, diversity


def _category_weight(stats: dict[str, Any], keys: set[str]) -> float:
    cat_stats = stats.get("category_stats") or {}
    total = sum(cat_stats.values()) or 1
    matched = sum(count for cat, count in cat_stats.items() if cat in keys)
    return matched / total


def rule_based_values_temperament(stats: dict[str, Any]) -> ValuesTemperamentOutput:
    """1단계 폴백: catalog 통계 → 가치관·기질."""
    concentration, exploration_depth, diversity = _habits_from_stats(stats)
    shorts_ratio = float(stats.get("shorts_ratio") or 0.0)
    long_ratio = float(stats.get("long_ratio") or (1.0 - shorts_ratio))
    edu_w = _category_weight(stats, _EDU_CATEGORIES)
    news_w = _category_weight(stats, _NEWS_CATEGORIES)
    entertain_w = _category_weight(stats, _ENTERTAINMENT_CATEGORIES)

    self_direction = _clamp(38 + diversity * 38 + (1 - concentration) * 22)
    stimulation = _clamp(32 + shorts_ratio * 48 + entertain_w * 28)
    achievement = _clamp(38 + edu_w * 42 + long_ratio * 18)
    power = _clamp(42 + concentration * 32)
    security = _clamp(48 + concentration * 28 - diversity * 18)
    benevolence = _clamp(38 + news_w * 32 + entertain_w * 12)
    universalism = _clamp(34 + news_w * 28 + edu_w * 22 + diversity * 16)
    hedonism = _clamp(28 + shorts_ratio * 52 + entertain_w * 32)
    conformity = _clamp(44 + concentration * 38 - self_direction * 0.12)
    tradition = _clamp(50 - diversity * 22 - stimulation * 0.08)

    novelty_seeking = _clamp(
        34 + diversity * 38 + shorts_ratio * 18 + exploration_depth * 22
    )
    persistence = _clamp(36 + edu_w * 38 + long_ratio * 28 + achievement * 0.12)
    self_transcendence = _clamp(
        32 + universalism * 0.28 + benevolence * 0.28 + news_w * 22
    )

    return ValuesTemperamentOutput(
        self_direction=round(self_direction, 1),
        stimulation=round(stimulation, 1),
        achievement=round(achievement, 1),
        power=round(power, 1),
        security=round(security, 1),
        benevolence=round(benevolence, 1),
        universalism=round(universalism, 1),
        hedonism=round(hedonism, 1),
        conformity=round(conformity, 1),
        tradition=round(tradition, 1),
        novelty_seeking=round(novelty_seeking, 1),
        persistence=round(persistence, 1),
        self_transcendence=round(self_transcendence, 1),
    )


def rule_based_behavior_spider(vt: ValuesTemperamentOutput) -> BehaviorSpiderOutput:
    """2단계 폴백: 가치관·기질 점수 → 행동 스파이더 8."""
    exploration = _clamp(
        vt.novelty_seeking * 0.55 + vt.self_direction * 0.28 + vt.stimulation * 0.17
    )
    analytical = _clamp(
        vt.achievement * 0.32 + vt.universalism * 0.33 + vt.persistence * 0.25
    )
    creativity = _clamp(
        vt.self_direction * 0.38 + vt.stimulation * 0.34 + vt.hedonism * 0.18
    )
    execution = _clamp(vt.persistence * 0.52 + vt.achievement * 0.38)
    achievement_drive = _clamp(
        vt.achievement * 0.52 + vt.persistence * 0.33 + vt.power * 0.15
    )
    autonomy = _clamp(
        vt.self_direction * 0.52 + vt.novelty_seeking * 0.28 - vt.conformity * 0.18
    )
    sociality = _clamp(
        vt.benevolence * 0.42 + vt.universalism * 0.28 + vt.hedonism * 0.18
    )
    sensitivity = _clamp(
        vt.self_transcendence * 0.38 + vt.hedonism * 0.28 + vt.stimulation * 0.22
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
    persona = "탐색형 큐레이터" if top[0][0] == "exploration" else "집중형 소비자"
    if shorts_ratio > 0.5:
        persona = "숏폼 중심 소비자"

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


async def _load_context(
    user_id: uuid.UUID,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from app.core.database.session import AsyncSessionLocal
    from app.repositories.profiler_repository import (
        fetch_analysis_for_catalog_ids,
        fetch_catalog_rows,
    )

    async with AsyncSessionLocal() as session:
        rows = await fetch_catalog_rows(session, user_id)
        stats = _build_catalog_stats(rows)
        analyses = await fetch_analysis_for_catalog_ids(
            session, [row.id for row in rows[:50]]
        )

    by_catalog = {a.catalog_id: a for a in analyses}
    samples = []
    for row in rows[:30]:
        analysis = by_catalog.get(row.id)
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
        samples.append(sample)
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
    vt = await _llm_values_temperament(user_id, stats, analysis_samples)
    stage1_llm = vt is not None
    if vt is None:
        vt = rule_based_values_temperament(stats)

    behavior = await _llm_behavior_spider(user_id, vt, stats)
    stage2_llm = behavior is not None
    if behavior is None:
        behavior = rule_based_behavior_spider(vt)

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
        log.append(
            f"build_profile: catalog={stats['total']} "
            f"samples={len(samples)} shorts_ratio={stats.get('shorts_ratio', 0)}"
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
