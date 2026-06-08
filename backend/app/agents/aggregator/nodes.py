"""Aggregator LangGraph 노드 및 Gemini 리포트 생성 로직."""

from __future__ import annotations

import os
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .mock_data import MockIntegratedData, generate_mock_integrated_data
from .prompts import AGGREGATOR_SYSTEM_PROMPT, build_report_user_prompt

PRIMARY_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODEL = "gemini-1.5-flash"
SUPPORTED_GEMINI_MODELS: tuple[str, ...] = (
    PRIMARY_GEMINI_MODEL,
    FALLBACK_GEMINI_MODEL,
)
DEFAULT_GEMINI_MODEL = PRIMARY_GEMINI_MODEL
GEMINI_MODEL_ENV_VAR = "GEMINI_MODEL"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


class AggregatorNodeState(TypedDict, total=False):
    """LangGraph 상태 스키마 (graph.py 연동용 베이스라인)."""

    integrated_data: MockIntegratedData
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


def _invoke_b2b_report(
    data: MockIntegratedData,
    *,
    model: str,
) -> str:
    llm = get_gemini_model(model=model)
    messages = [
        SystemMessage(content=AGGREGATOR_SYSTEM_PROMPT),
        HumanMessage(content=build_report_user_prompt(data)),
    ]
    response = llm.invoke(messages)
    return _extract_response_text(response.content)


def generate_b2b_report(
    integrated_data: MockIntegratedData | None = None,
    *,
    model: str | None = None,
) -> str:
    """가상 통합 데이터를 기반으로 B2B 시장 분석 리포트(Markdown)를 생성한다."""
    data = integrated_data or generate_mock_integrated_data()
    resolved_model = resolve_gemini_model(model)

    try:
        return _invoke_b2b_report(data, model=resolved_model)
    except Exception:
        if resolved_model == FALLBACK_GEMINI_MODEL:
            raise
        return _invoke_b2b_report(data, model=FALLBACK_GEMINI_MODEL)


def generate_report_node(state: AggregatorNodeState) -> dict[str, Any]:
    """LangGraph 노드: 통합 데이터를 입력받아 Markdown 리포트를 상태에 기록한다."""
    integrated_data = state.get("integrated_data") or generate_mock_integrated_data()
    report_markdown = generate_b2b_report(integrated_data)

    return {
        "integrated_data": integrated_data,
        "report_markdown": report_markdown,
    }
