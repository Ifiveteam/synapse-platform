"""Aggregator Gemini 호출·Structured Output·fallback."""

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
