"""노드 실행 단계 trace."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.agents.aggregator.trace._common import (
    KEYWORD_PREVIEW,
    keyword_lines,
    logger,
    truncate,
)

if TYPE_CHECKING:
    from app.schemas.report import DashboardReportSchema


def log_integrated_data_summary(integrated_data: dict[str, Any]) -> None:
    internal = integrated_data.get("internal_user_stats", {})
    external = integrated_data.get("external_market_trends", {})
    profile = internal.get("cognitive_bias_map", {})

    logger.info("  ┌─ 통합 데이터 스냅샷")
    logger.info("  │ schema_version : %s", integrated_data.get("schema_version"))
    logger.info("  │ generated_at   : %s", integrated_data.get("generated_at"))
    logger.info("  │ cohort_size    : %s명", profile.get("cohort_size"))

    logger.info("  │ [내부 TOP 키워드]")
    for line in keyword_lines(internal.get("top_keywords", [])):
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
    for line in keyword_lines(external.get("google_trends", [])):
        logger.info("  │ %s", line)

    logger.info("  │ [외부 YouTube 급상승 TOP]")
    for line in keyword_lines(external.get("youtube_trending", [])):
        logger.info("  │ %s", line)

    logger.info("  │ [외부 Naver 검색어 TOP]")
    for line in keyword_lines(external.get("naver_search", [])):
        logger.info("  │ %s", line)

    news_items = external.get("naver_news", [])
    logger.info(
        "  │ [외부 Naver 뉴스 헤드라인 TOP %s건]", min(len(news_items), KEYWORD_PREVIEW)
    )
    for index, item in enumerate(news_items[:KEYWORD_PREVIEW], start=1):
        headline = item.get("headline") or item.get("title") or "?"
        section = item.get("section", "?")
        press = item.get("press")
        suffix = f" ({press})" if press and press != "미상" else ""
        logger.info("  │   %s. [%s] %s%s", index, section, headline, suffix)
    if len(news_items) > KEYWORD_PREVIEW:
        logger.info("  │   … 외 %s건", len(news_items) - KEYWORD_PREVIEW)

    logger.info("  │ data_collected_at: %s", external.get("data_collected_at"))
    logger.info("  └─ 통합 데이터 요약 완료")


def log_culture_input(integrated_data: dict[str, Any]) -> None:
    internal = integrated_data.get("internal_user_stats", {})
    youtube = integrated_data.get("external_market_trends", {}).get(
        "youtube_trending", []
    )
    logger.info("  ┌─ culture_analysis 입력 범위")
    logger.info("  │ 내부 유저 통계 + YouTube 급상승 (%s건)", len(youtube))
    logger.info(
        "  │ 내부 키워드 %s건, 8각 축 %s개",
        len(internal.get("top_keywords", [])),
        len(internal.get("cognitive_bias_map", {}).get("axes", [])),
    )
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
    for line in truncate(content).splitlines():
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
        for line in truncate(critique_preview, limit=300).splitlines():
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
        for line in truncate(feedback, limit=800).splitlines():
            logger.info("  │   %s", line)
    else:
        logger.info("  │ 반려 사유/피드백: (없음 — 합격 또는 피드백 미제공)")
    logger.info("  └─ 검수 완료")
