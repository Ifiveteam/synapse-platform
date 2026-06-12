"""Aggregator 워크플로우 실행 추적용 상세 로깅."""

from __future__ import annotations

import logging
import textwrap
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas.report import DashboardReportSchema

logger = logging.getLogger("app.agents.aggregator.workflow")

_PREVIEW_CHARS = 600
_KEYWORD_PREVIEW = 5


def _truncate(text: str | None, *, limit: int = _PREVIEW_CHARS) -> str:
    if not text:
        return "(없음)"
    normalized = text.strip().replace("\r\n", "\n")
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}… [총 {len(normalized):,}자]"


def _keyword_lines(items: list[dict[str, Any]], *, label_key: str = "keyword") -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items[:_KEYWORD_PREVIEW], start=1):
        keyword = item.get(label_key, "?")
        extra_parts: list[str] = []
        for key in ("rank", "frequency", "interest_index", "category", "source"):
            if key in item and item[key] is not None:
                extra_parts.append(f"{key}={item[key]}")
        suffix = f" ({', '.join(extra_parts)})" if extra_parts else ""
        lines.append(f"    {index}. {keyword}{suffix}")
    if len(items) > _KEYWORD_PREVIEW:
        lines.append(f"    … 외 {len(items) - _KEYWORD_PREVIEW}건")
    return lines


def _banner(title: str) -> None:
    line = "═" * 72
    logger.info("%s", line)
    logger.info("  %s", title)
    logger.info("%s", line)


def log_workflow_start() -> None:
    _banner("🚀 Aggregator 멀티 에이전트 워크플로우 시작")


def log_assemble_workflow_start() -> None:
    _banner("⚡ Aggregator 데이터 조립 전용 워크플로우 시작 (Gemini 미호출)")


def log_assemble_workflow_end(state: dict[str, Any]) -> None:
    integrated = state.get("integrated_data") or {}
    profile = integrated.get("internal_user_stats", {}).get("cognitive_bias_map", {})
    _banner(
        f"✅ 데이터 조립 완료 | 코호트={profile.get('cohort_size', '?')}명 "
        f"| 8각 축={len(profile.get('axes', []))}개"
    )


def log_workflow_end(state: dict[str, Any]) -> None:
    score = state.get("verification_score")
    review_count = state.get("review_count", 0)
    report_json = state.get("report_json") or {}
    headline = report_json.get("headline_summary", "") if isinstance(report_json, dict) else ""
    _banner(
        f"✅ 워크플로우 종료 | 검수 점수={score}점 | 검수 횟수={review_count}회 "
        f"| headline={headline[:60] or '(없음)'}"
    )


def log_node_enter(node: str, *, state: dict[str, Any] | None = None) -> None:
    logger.info("▶ [%s] 노드 진입", node)
    if not state:
        return

    if node == "generate_report":
        attempt = state.get("review_count", 0) + 1
        logger.info("  └─ 리포트 생성 시도 #%s", attempt)
        feedback = state.get("critique_feedback")
        if feedback:
            logger.info("  └─ 이전 검수 피드백 반영:")
            for line in textwrap.wrap(feedback, width=68):
                logger.info("       %s", line)

    if node == "verify_report":
        logger.info("  └─ 현재 누적 검수 횟수: %s회", state.get("review_count", 0))


def log_integrated_data_summary(integrated_data: dict[str, Any]) -> None:
    internal = integrated_data.get("internal_user_stats", {})
    external = integrated_data.get("external_market_trends", {})
    profile = internal.get("cognitive_bias_map", {})

    logger.info("  ┌─ 통합 데이터 스냅샷")
    logger.info("  │ schema_version : %s", integrated_data.get("schema_version"))
    logger.info("  │ generated_at   : %s", integrated_data.get("generated_at"))
    logger.info("  │ cohort_size    : %s명", profile.get("cohort_size"))

    logger.info("  │ [내부 TOP 키워드]")
    for line in _keyword_lines(internal.get("top_keywords", [])):
        logger.info("  │ %s", line)

    logger.info("  │ [8각 인지 성향 평균]")
    for axis in profile.get("axes", []):
        logger.info(
            "  │   - %s (%s): %.1f점",
            axis.get("label", "?"),
            axis.get("key", "?"),
            axis.get("avg_score", 0),
        )

    logger.info("  │ [외부 Google Trends TOP]")
    for line in _keyword_lines(external.get("google_trends", [])):
        logger.info("  │ %s", line)

    logger.info("  │ [외부 YouTube 급상승 TOP]")
    for line in _keyword_lines(external.get("youtube_trending", [])):
        logger.info("  │ %s", line)

    logger.info("  │ [외부 Naver 검색어 TOP]")
    for line in _keyword_lines(external.get("naver_search", [])):
        logger.info("  │ %s", line)

    news_items = external.get("naver_news", [])
    logger.info("  │ [외부 Naver 뉴스 헤드라인 TOP %s건]", min(len(news_items), _KEYWORD_PREVIEW))
    for index, item in enumerate(news_items[:_KEYWORD_PREVIEW], start=1):
        headline = item.get("headline") or item.get("title") or "?"
        section = item.get("section", "?")
        press = item.get("press")
        suffix = f" ({press})" if press and press != "미상" else ""
        logger.info("  │   %s. [%s] %s%s", index, section, headline, suffix)
    if len(news_items) > _KEYWORD_PREVIEW:
        logger.info("  │   … 외 %s건", len(news_items) - _KEYWORD_PREVIEW)

    logger.info("  │ data_collected_at: %s", external.get("data_collected_at"))
    logger.info("  └─ 통합 데이터 요약 완료")


def log_culture_input(integrated_data: dict[str, Any]) -> None:
    internal = integrated_data.get("internal_user_stats", {})
    youtube = integrated_data.get("external_market_trends", {}).get("youtube_trending", [])
    logger.info("  ┌─ culture_analysis 입력 범위")
    logger.info("  │ 내부 유저 통계 + YouTube 급상승 (%s건)", len(youtube))
    logger.info("  │ 내부 키워드 %s건, 8각 축 %s개",
                len(internal.get("top_keywords", [])),
                len(internal.get("cognitive_bias_map", {}).get("axes", [])))
    logger.info("  └─ Gemini 문화/콘텐츠 분석 호출 중…")


def log_market_input(integrated_data: dict[str, Any]) -> None:
    external = integrated_data.get("external_market_trends", {})
    logger.info("  ┌─ market_analysis 입력 범위")
    logger.info("  │ Google Trends %s건", len(external.get("google_trends", [])))
    logger.info("  │ Naver 검색어 %s건", len(external.get("naver_search", [])))
    logger.info("  │ Naver 뉴스 %s건", len(external.get("naver_news", [])))
    logger.info("  └─ Gemini 매크로 시장 분석 호출 중…")


def log_analysis_result(*, agent: str, content: str) -> None:
    logger.info("  ┌─ %s 초안 생성 완료 (%s자)", agent, len(content))
    for line in _truncate(content).splitlines():
        logger.info("  │ %s", line)
    logger.info("  └─ %s 초안 미리보기 종료", agent)


def log_report_generation(
    *,
    culture_chars: int,
    market_chars: int,
    has_critique: bool,
    critique_preview: str | None = None,
) -> None:
    logger.info("  ┌─ generate_report 입력")
    logger.info("  │ culture_analysis : %s자", culture_chars)
    logger.info("  │ market_analysis  : %s자", market_chars)
    logger.info("  │ critique 반영    : %s", "예" if has_critique else "아니오")
    if critique_preview:
        logger.info("  │ critique 미리보기:")
        for line in _truncate(critique_preview, limit=300).splitlines():
            logger.info("  │   %s", line)
    logger.info("  └─ Gemini 마스터 리포트 융합 호출 중…")


def log_report_result(report: "DashboardReportSchema") -> None:
    logger.info("  ┌─ 최종 JSON 리포트 생성 완료")
    logger.info("  │ headline       : %s", report.headline_summary)
    logger.info(
        "  │ neutrality     : %s/100 (%s)",
        report.neutrality_score,
        report.neutrality_status,
    )
    logger.info("  │ radar axes     : %s개", len(report.radar_chart_data))
    logger.info(
        "  │ macro trends   : internal=%s, external=%s",
        len(report.macro_trend_internal),
        len(report.macro_trend_external),
    )
    logger.info("  └─ 리포트 JSON 스냅샷 종료")


def log_verification_result(
    *,
    score: int,
    feedback: str,
    is_template_valid: bool,
    revision_target: str | None,
    review_count: int,
    pass_threshold: int,
    max_attempts: int,
) -> None:
    passed = score >= pass_threshold
    logger.info("  ┌─ 🔍 검수 결과 (시니어 검수자 · Structured Output)")
    logger.info("  │ 검수 점수     : %s / 100", score)
    logger.info("  │ 서식 준수     : %s", "✅" if is_template_valid else "❌")
    logger.info("  │ 재실행 대상   : %s", revision_target or "(미지정)")
    logger.info("  │ 합격 기준     : %s점 이상", pass_threshold)
    logger.info("  │ 검수 횟수     : %s / %s회", review_count, max_attempts)
    logger.info("  │ 합격 여부     : %s", "✅ 합격" if passed else "❌ 반려")
    if feedback:
        logger.info("  │ 반려 사유/피드백:")
        for line in _truncate(feedback, limit=800).splitlines():
            logger.info("  │   %s", line)
    else:
        logger.info("  │ 반려 사유/피드백: (없음 — 합격 또는 피드백 미제공)")
    logger.info("  └─ 검수 완료")


def log_route_decision(
    *,
    score: int,
    review_count: int,
    pass_threshold: int,
    max_attempts: int,
    next_node: str,
    revision_target: str | None = None,
) -> None:
    reason: str
    if score >= pass_threshold:
        reason = f"검수 점수 {score}점 ≥ 합격 기준 {pass_threshold}점"
    elif review_count >= max_attempts:
        reason = f"최대 재시도 {max_attempts}회 도달 (현재 {review_count}회)"
    else:
        reason = (
            f"검수 점수 {score}점 < {pass_threshold}점 → "
            f"revision_target={revision_target or 'generate_report'} 역주행"
        )

    logger.info("  ┌─ 🔀 조건부 분기 (verify_report 이후)")
    logger.info("  │ 검수 점수 : %s점", score)
    logger.info("  │ 검수 횟수 : %s회", review_count)
    logger.info("  │ 재실행 대상: %s", revision_target or "(없음)")
    logger.info("  │ 분기 사유 : %s", reason)
    logger.info("  │ 다음 노드 : %s", next_node)
    logger.info("  └─ 라우팅 결정 완료")
