"""Aggregator LangGraph 노드."""

from __future__ import annotations

from typing import Any

from app.agents.aggregator.pipeline import assemble_integrated_data
from app.agents.aggregator.report import coerce_dashboard_report, generate_fused_b2b_report
from app.agents.aggregator.routing import (
    build_verification_state_patch,
    critique_for_culture,
    critique_for_market,
    critique_for_master_report,
)
from app.agents.aggregator.state import (
    MAX_REVIEW_ATTEMPTS,
    REVIEW_PASS_THRESHOLD,
    AggregatorState,
)
from app.agents.aggregator.sub_agent import (
    run_culture_analysis,
    run_market_analysis,
    run_report_verification,
)
from app.agents.aggregator.trace import (
    log_analysis_result,
    log_culture_input,
    log_integrated_data_summary,
    log_market_input,
    log_node_enter,
    log_report_generation,
    log_report_result,
    log_verification_result,
    logger,
)

_NODE_ASSEMBLE = "assemble_data"
_NODE_CULTURE = "culture_analysis"
_NODE_MARKET = "market_analysis"
_NODE_GENERATE = "generate_report"
_NODE_VERIFY = "verify_report"


def _require_integrated_data(state: AggregatorState) -> dict[str, Any]:
    integrated_data = state.get("integrated_data")
    if integrated_data is None:
        msg = (
            "integrated_data가 상태에 없습니다. "
            "assemble_data 노드 이후에 실행하세요."
        )
        raise ValueError(msg)
    return integrated_data


async def assemble_data_node(_state: AggregatorState) -> dict[str, Any]:
    """내부·외부 데이터를 조립해 integrated_data를 상태에 기록한다."""
    log_node_enter(_NODE_ASSEMBLE)
    integrated_data = await assemble_integrated_data()
    log_integrated_data_summary(integrated_data)
    return {
        "integrated_data": integrated_data,
        "review_count": 0,
        "revision_target": "generate_report",
        "error": None,
    }


async def culture_analysis_node(state: AggregatorState) -> dict[str, Any]:
    """서브 에이전트 1: 문화/콘텐츠 관점 트렌드 격차 분석 초안."""
    log_node_enter(_NODE_CULTURE, state=state)
    integrated_data = _require_integrated_data(state)
    critique_feedback = critique_for_culture(state)
    log_culture_input(integrated_data)
    if critique_feedback:
        logger.info("  └─ 검수 피드백 반영 culture 재분석 (revision_target=%s)",
                    state.get("revision_target"))
    culture_analysis = await run_culture_analysis(
        integrated_data,
        critique_feedback=critique_feedback,
    )
    log_analysis_result(agent="culture_analysis", content=culture_analysis)
    return {"culture_analysis": culture_analysis}


async def market_analysis_node(state: AggregatorState) -> dict[str, Any]:
    """서브 에이전트 2: 매크로 시장·언론 경제 이슈 분석 초안."""
    log_node_enter(_NODE_MARKET, state=state)
    integrated_data = _require_integrated_data(state)
    critique_feedback = critique_for_market(state)
    log_market_input(integrated_data)
    if critique_feedback:
        logger.info("  └─ 검수 피드백 반영 market 재분석 (revision_target=%s)",
                    state.get("revision_target"))
    market_analysis = await run_market_analysis(
        integrated_data,
        critique_feedback=critique_feedback,
    )
    log_analysis_result(agent="market_analysis", content=market_analysis)
    return {"market_analysis": market_analysis}


async def generate_report_node(state: AggregatorState) -> dict[str, Any]:
    """마스터 에이전트: 서브 에이전트 초안을 융합해 최종 JSON 리포트를 생성한다."""
    log_node_enter(_NODE_GENERATE, state=state)
    integrated_data = _require_integrated_data(state)

    culture_analysis = state.get("culture_analysis")
    market_analysis = state.get("market_analysis")
    if not culture_analysis or not market_analysis:
        msg = (
            "culture_analysis·market_analysis가 모두 필요합니다. "
            "병렬 분석 노드 완료 후 실행하세요."
        )
        raise ValueError(msg)

    critique_feedback = critique_for_master_report(state)
    log_report_generation(
        culture_chars=len(culture_analysis),
        market_chars=len(market_analysis),
        has_critique=bool(critique_feedback),
        critique_preview=critique_feedback,
    )

    report_json = await generate_fused_b2b_report(
        integrated_data,
        culture_analysis=culture_analysis,
        market_analysis=market_analysis,
        critique_feedback=critique_feedback,
    )
    log_report_result(report_json)

    return {
        "report_json": report_json.model_dump(),
        "error": None,
    }


async def verify_report_node(state: AggregatorState) -> dict[str, Any]:
    """시니어 검수자: Structured Output으로 채점 후 상태를 결정론적으로 갱신한다."""
    log_node_enter(_NODE_VERIFY, state=state)
    integrated_data = _require_integrated_data(state)

    raw_report = state.get("report_json")
    if not raw_report:
        msg = "report_json이 상태에 없습니다. generate_report 노드 이후에 실행하세요."
        raise ValueError(msg)

    report = coerce_dashboard_report(raw_report)
    logger.info("  ┌─ 검수 대상 리포트: headline=%s", report.headline_summary[:80])
    logger.info("  └─ Gemini 시니어 검수자(Structured Output) 호출 중…")

    result = await run_report_verification(report, integrated_data)
    review_count = state.get("review_count", 0) + 1
    state_patch = build_verification_state_patch(result, review_count=review_count)

    log_verification_result(
        score=state_patch["verification_score"],
        feedback=state_patch["critique_feedback"],
        is_template_valid=state_patch["is_template_valid"],
        revision_target=state_patch["revision_target"],
        review_count=state_patch["review_count"],
        pass_threshold=REVIEW_PASS_THRESHOLD,
        max_attempts=MAX_REVIEW_ATTEMPTS,
    )

    return {**state_patch, "error": None}
