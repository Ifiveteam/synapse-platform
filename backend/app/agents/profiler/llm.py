"""Profiler Gemini Structured Output — primary→fallback 모델 재시도.

각 에이전트가 자기 LLM 진입을 소유하는 컨벤션(navigator llm.py 등)에 따라
profiler 전용으로 둔다. (이전엔 aggregator.llm.gemini에 의존)
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

TSchema = TypeVar("TSchema", bound=BaseModel)

PRIMARY_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODEL = "gemini-2.5-flash-lite"
SUPPORTED_GEMINI_MODELS: tuple[str, ...] = (PRIMARY_GEMINI_MODEL, FALLBACK_GEMINI_MODEL)
DEFAULT_GEMINI_MODEL = PRIMARY_GEMINI_MODEL
GEMINI_MODEL_ENV_VAR = "GEMINI_MODEL"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


def _resolve_gemini_api_key() -> str:
    for env_var in GEMINI_API_KEY_ENV_VARS:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key
    joined = ", ".join(GEMINI_API_KEY_ENV_VARS)
    raise ValueError(
        f"Gemini API 키가 설정되지 않았습니다. 환경 변수 중 하나를 설정하세요: {joined}"
    )


def resolve_gemini_model(model: str | None = None) -> str:
    """사용할 Gemini 모델명을 결정한다. 기본값은 gemini-2.5-flash."""
    resolved = model or os.getenv(GEMINI_MODEL_ENV_VAR) or DEFAULT_GEMINI_MODEL
    if resolved not in SUPPORTED_GEMINI_MODELS:
        supported = ", ".join(SUPPORTED_GEMINI_MODELS)
        raise ValueError(
            f"지원하지 않는 Gemini 모델입니다: {resolved}. 사용 가능한 모델: {supported}"
        )
    return resolved


def get_gemini_model(
    *, model: str | None = None, temperature: float = 0.4
) -> ChatGoogleGenerativeAI:
    """Gemini Chat 모델 인스턴스를 반환한다."""
    return ChatGoogleGenerativeAI(
        model=resolve_gemini_model(model),
        google_api_key=_resolve_gemini_api_key(),
        temperature=temperature,
    )


def _is_non_retryable_gemini_error(exc: Exception) -> bool:
    """모델 미존재·인증 오류 등 fallback으로 해결되지 않는 오류."""
    if isinstance(exc, ValueError):
        return True
    visited: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if getattr(current, "status_code", None) in {401, 403, 404}:
            return True
        message = str(current).upper()
        if any(
            marker in message
            for marker in ("NOT_FOUND", "UNAUTHENTICATED", "PERMISSION_DENIED")
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


async def _invoke_structured_with_model(
    messages: Sequence[BaseMessage],
    schema: type[TSchema],
    *,
    model: str,
    temperature: float,
) -> TSchema:
    llm = get_gemini_model(model=model, temperature=temperature)
    structured = llm.with_structured_output(schema, method="json_schema")
    result = await structured.ainvoke(messages)
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
    """Gemini Structured Output(Pydantic). 실패 시 fallback 모델로 1회 재시도."""
    resolved_model = resolve_gemini_model(model)
    try:
        return await _invoke_structured_with_model(
            messages, schema, model=resolved_model, temperature=temperature
        )
    except Exception as exc:
        if resolved_model == FALLBACK_GEMINI_MODEL or _is_non_retryable_gemini_error(
            exc
        ):
            raise
        logger.warning(
            "Gemini Structured 실패 (%s) → fallback(%s) 재시도: %s",
            resolved_model,
            FALLBACK_GEMINI_MODEL,
            exc,
            exc_info=True,
        )
        return await _invoke_structured_with_model(
            messages, schema, model=FALLBACK_GEMINI_MODEL, temperature=temperature
        )
