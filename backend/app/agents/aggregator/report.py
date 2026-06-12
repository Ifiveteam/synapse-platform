"""Aggregator B2B 리포트 생성 (Gemini Structured Output)."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from typing import TypeVar

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.agents.aggregator.base import IntegratedData
from app.agents.aggregator.prompts import (
    MASTER_REPORT_SYSTEM_PROMPT,
    build_master_report_user_prompt,
    build_report_user_prompt,
)
from app.schemas.report import DashboardReportSchema

logger = logging.getLogger(__name__)

TSchema = TypeVar("TSchema", bound=BaseModel)

PRIMARY_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODEL = "gemini-2.5-flash-lite"
SUPPORTED_GEMINI_MODELS: tuple[str, ...] = (
    PRIMARY_GEMINI_MODEL,
    FALLBACK_GEMINI_MODEL,
)
DEFAULT_GEMINI_MODEL = PRIMARY_GEMINI_MODEL
GEMINI_MODEL_ENV_VAR = "GEMINI_MODEL"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


def _resolve_gemini_api_key() -> str:
    for env_var in GEMINI_API_KEY_ENV_VARS:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key
    joined = ", ".join(GEMINI_API_KEY_ENV_VARS)
    msg = (
        "Gemini API 키가 설정되지 않았습니다. "
        f"환경 변수 중 하나를 설정하세요: {joined}"
    )
    raise ValueError(msg)


def resolve_gemini_model(model: str | None = None) -> str:
    """사용할 Gemini 모델명을 결정한다. 기본값은 gemini-2.5-flash."""
    resolved = model or os.getenv(GEMINI_MODEL_ENV_VAR) or DEFAULT_GEMINI_MODEL
    if resolved not in SUPPORTED_GEMINI_MODELS:
        supported = ", ".join(SUPPORTED_GEMINI_MODELS)
        msg = (
            f"지원하지 않는 Gemini 모델입니다: {resolved}. "
            f"사용 가능한 모델: {supported}"
        )
        raise ValueError(msg)
    return resolved


def get_gemini_model(
    *,
    model: str | None = None,
    temperature: float = 0.4,
) -> ChatGoogleGenerativeAI:
    """Gemini Chat 모델 인스턴스를 반환한다."""
    return ChatGoogleGenerativeAI(
        model=resolve_gemini_model(model),
        google_api_key=_resolve_gemini_api_key(),
        temperature=temperature,
    )


def extract_response_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "\n".join(text_parts).strip()

    return str(content).strip()


def _is_non_retryable_gemini_error(exc: Exception) -> bool:
    """모델 미존재·인증 오류 등 fallback으로 해결되지 않는 Gemini 오류."""
    if isinstance(exc, ValueError):
        return True

    visited: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        status_code = getattr(current, "status_code", None)
        if status_code in {401, 403, 404}:
            return True
        message = str(current).upper()
        if any(
            marker in message
            for marker in ("NOT_FOUND", "UNAUTHENTICATED", "PERMISSION_DENIED")
        ):
            return True
        current = current.__cause__ or current.__context__

    return False


async def _invoke_gemini_with_model(
    messages: Sequence[BaseMessage],
    *,
    model: str,
    temperature: float,
) -> str:
    llm = get_gemini_model(model=model, temperature=temperature)
    response = await llm.ainvoke(messages)
    return extract_response_text(response.content)


async def _invoke_gemini_structured_with_model(
    messages: Sequence[BaseMessage],
    schema: type[TSchema],
    *,
    model: str,
    temperature: float,
) -> TSchema:
    llm = get_gemini_model(model=model, temperature=temperature)
    structured_llm = llm.with_structured_output(
        schema,
        method="json_schema",
    )
    result = await structured_llm.ainvoke(messages)
    if isinstance(result, schema):
        return result
    return schema.model_validate(result)


async def invoke_gemini_structured(
    messages: Sequence[BaseMessage],
    schema: type[TSchema],
    *,
    model: str | None = None,
    temperature: float = 0.2,
) -> TSchema:
    """Gemini Structured Output(Pydantic)을 반환한다. 실패 시 fallback 모델로 재시도."""
    resolved_model = resolve_gemini_model(model)

    try:
        return await _invoke_gemini_structured_with_model(
            messages,
            schema,
            model=resolved_model,
            temperature=temperature,
        )
    except Exception as exc:
        if (
            resolved_model == FALLBACK_GEMINI_MODEL
            or _is_non_retryable_gemini_error(exc)
        ):
            raise
        logger.warning(
            "Gemini Structured Output 실패 (%s). fallback 모델(%s)로 재시도합니다: %s",
            resolved_model,
            FALLBACK_GEMINI_MODEL,
            exc,
            exc_info=True,
        )
        return await _invoke_gemini_structured_with_model(
            messages,
            schema,
            model=FALLBACK_GEMINI_MODEL,
            temperature=temperature,
        )


async def invoke_gemini(
    messages: Sequence[BaseMessage],
    *,
    model: str | None = None,
    temperature: float = 0.4,
) -> str:
    """Gemini를 호출하고 응답 텍스트를 반환한다. 실패 시 fallback 모델로 재시도."""
    resolved_model = resolve_gemini_model(model)

    try:
        return await _invoke_gemini_with_model(
            messages, model=resolved_model, temperature=temperature
        )
    except Exception as exc:
        if (
            resolved_model == FALLBACK_GEMINI_MODEL
            or _is_non_retryable_gemini_error(exc)
        ):
            raise
        logger.warning(
            "Gemini 호출 실패 (%s). fallback 모델(%s)로 재시도합니다: %s",
            resolved_model,
            FALLBACK_GEMINI_MODEL,
            exc,
            exc_info=True,
        )
        return await _invoke_gemini_with_model(
            messages, model=FALLBACK_GEMINI_MODEL, temperature=temperature
        )


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


async def generate_b2b_report(
    integrated_data: IntegratedData,
    *,
    model: str | None = None,
) -> DashboardReportSchema:
    """통합 데이터를 기반으로 B2B 대시보드 JSON 리포트를 생성한다."""
    messages = [
        SystemMessage(content=MASTER_REPORT_SYSTEM_PROMPT),
        HumanMessage(content=build_report_user_prompt(integrated_data)),
    ]
    return await invoke_gemini_structured(
        messages,
        DashboardReportSchema,
        model=model or PRIMARY_GEMINI_MODEL,
        temperature=0.3,
    )


async def generate_fused_b2b_report(
    integrated_data: IntegratedData,
    *,
    culture_analysis: str,
    market_analysis: str,
    critique_feedback: str | None = None,
    model: str | None = None,
) -> DashboardReportSchema:
    """서브 에이전트 초안을 융합하여 최종 B2B 대시보드 JSON 리포트를 생성한다."""
    messages = [
        SystemMessage(content=MASTER_REPORT_SYSTEM_PROMPT),
        HumanMessage(
            content=build_master_report_user_prompt(
                integrated_data,
                culture_analysis=culture_analysis,
                market_analysis=market_analysis,
                critique_feedback=critique_feedback,
            )
        ),
    ]
    return await invoke_gemini_structured(
        messages,
        DashboardReportSchema,
        model=model or PRIMARY_GEMINI_MODEL,
        temperature=0.3,
    )
