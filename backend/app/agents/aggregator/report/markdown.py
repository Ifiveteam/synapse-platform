"""구조화 리포트 복원·PDF용 Markdown 변환."""

from __future__ import annotations

from app.schemas.report import DashboardReportSchema


def coerce_dashboard_report(
    report: DashboardReportSchema | dict[str, object],
) -> DashboardReportSchema:
    """상태·API 경계에서 DashboardReportSchema를 안전하게 복원한다."""
    if isinstance(report, DashboardReportSchema):
        return report
    return DashboardReportSchema.model_validate(report)


def dashboard_report_to_markdown(report: DashboardReportSchema) -> str:
    """PDF 다운로드 호환용으로 구조화 리포트를 Markdown으로 변환한다."""
    lines: list[str] = [
        "# 요약",
        "",
        f"> {report.headline_summary}",
        "",
        f"- **미디어 중립성**: {report.neutrality_score}/100 ({report.neutrality_status})",
        f"- {report.neutrality_reason}",
        "",
        "---",
        "",
        "## 매크로 트렌드 TOP 5",
        "",
        "### 내부 유저 상위 키워드 TOP 5",
        "",
        "| 순위 | 키워드 | 지표 | 변화 |",
        "|------|--------|------|------|",
    ]
    for item in report.macro_trend_internal:
        lines.append(
            f"| {item.rank} | {item.keyword} | {item.metrics} | {item.change} |"
        )

    lines.extend(
        [
            "",
            "### 외부 시장 급상승 TOP 5",
            "",
            "| 순위 | 키워드 | 지표 | 변화 |",
            "|------|--------|------|------|",
        ]
    )
    for item in report.macro_trend_external:
        lines.append(
            f"| {item.rank} | {item.keyword} | {item.metrics} | {item.change} |"
        )

    gap = report.gap_analysis
    lines.extend(
        [
            "",
            "### 격차 하이라이트",
            "",
            f"- **교집합**: {', '.join(gap.intersection_keywords)} — {gap.intersection_interpretation}",
            f"- **내부 우세**: {', '.join(gap.internal_only_keywords)} — {gap.internal_only_interpretation}",
            f"- **외부 우세**: {', '.join(gap.external_only_keywords)} — {gap.external_only_interpretation}",
            f"- **필터 버블 시나리오**: {gap.filter_bubble_scenario}",
            "",
            "---",
            "",
            "## 미디어 중립성 및 성향 분포 평가",
            "",
            "### 8각 인지 성향 분포",
            "",
            "| Key | 라벨 | 점수 | 해석 |",
            "|-----|------|------|------|",
        ]
    )
    for axis in report.radar_chart_data:
        lines.append(
            f"| {axis.key} | {axis.subject} | {axis.score:.1f} | {axis.interpretation} |"
        )

    lines.extend(
        [
            "",
            f"- **우세 성향 축**: {', '.join(report.dominant_axes)}",
            f"- **저조 성향 축**: {', '.join(report.deficient_axes)}",
            "",
            "### B2B 권고",
            "",
            "**콘텐츠 기획**",
        ]
    )
    lines.extend(f"- {item}" for item in report.recommendations.content_strategy)
    lines.append("")
    lines.append("**마케팅**")
    lines.extend(f"- {item}" for item in report.recommendations.marketing)
    lines.append("")
    lines.append("**플랫폼 정책**")
    lines.extend(f"- {item}" for item in report.recommendations.platform_policy)

    return "\n".join(lines)
