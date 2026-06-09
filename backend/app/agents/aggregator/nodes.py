"""Aggregator LangGraph 노드 및 Gemini 리포트 생성 로직."""

from __future__ import annotations

import logging
import os
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .prompts import AGGREGATOR_SYSTEM_PROMPT, build_report_user_prompt
from .types import IntegratedData

logger = logging.getLogger(__name__)

PRIMARY_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODEL = "gemini-2.5-flash-lite"
SUPPORTED_GEMINI_MODELS: tuple[str, ...] = (
    PRIMARY_GEMINI_MODEL,
    FALLBACK_GEMINI_MODEL,
)
DEFAULT_GEMINI_MODEL = PRIMARY_GEMINI_MODEL
GEMINI_MODEL_ENV_VAR = "GEMINI_MODEL"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


class AggregatorNodeState(TypedDict, total=False):
    """LangGraph 상태 스키마 (graph.py 연동용 베이스라인)."""

    integrated_data: IntegratedData
    report_markdown: str


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


def get_gemini_model(*, model: str | None = None) -> ChatGoogleGenerativeAI:
    """Gemini Chat 모델 인스턴스를 반환한다."""
    return ChatGoogleGenerativeAI(
        model=resolve_gemini_model(model),
        google_api_key=_resolve_gemini_api_key(),
        temperature=0.4,
    )


def _extract_response_text(content: object) -> str:
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


async def _invoke_b2b_report(
    data: IntegratedData,
    *,
    model: str,
) -> str:
    llm = get_gemini_model(model=model)
    messages = [
        SystemMessage(content=AGGREGATOR_SYSTEM_PROMPT),
        HumanMessage(content=build_report_user_prompt(data)),
    ]
    response = await llm.ainvoke(messages)
    return _extract_response_text(response.content)


async def generate_b2b_report(
    integrated_data: IntegratedData,
    *,
    model: str | None = None,
) -> str:
    """통합 데이터를 기반으로 B2B 시장 분석 리포트(Markdown)를 생성한다."""
    resolved_model = resolve_gemini_model(model)

    try:
        return await _invoke_b2b_report(integrated_data, model=resolved_model)
    except Exception as exc:
        if (
            resolved_model == FALLBACK_GEMINI_MODEL
            or _is_non_retryable_gemini_error(exc)
        ):
            raise
        logger.warning(
            "Gemini B2B 리포트 생성 실패 (%s). fallback 모델(%s)로 재시도합니다: %s",
            resolved_model,
            FALLBACK_GEMINI_MODEL,
            exc,
            exc_info=True,
        )
        return await _invoke_b2b_report(integrated_data, model=FALLBACK_GEMINI_MODEL)


async def generate_report_node(state: AggregatorNodeState) -> dict[str, Any]:
    """LangGraph 노드: 통합 데이터를 입력받아 Markdown 리포트를 상태에 기록한다."""
    integrated_data = state.get("integrated_data")
    if integrated_data is None:
        msg = (
            "integrated_data가 상태에 없습니다. "
            "라우터에서 조립된 데이터를 전달하세요."
        )
        raise ValueError(msg)

    report_markdown = await generate_b2b_report(integrated_data)

    return {
        "integrated_data": integrated_data,
        "report_markdown": report_markdown,
    }
