"""Archiver Gemini client 및 Structured Output 호출."""

from __future__ import annotations

import logging
import os
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.agents.archiver.constants import GEMINI_API_KEY_ENV_VARS, GEMINI_MODEL

logger = logging.getLogger(__name__)

TSchema = TypeVar("TSchema", bound=BaseModel)

_client: genai.Client | None = None


def _resolve_api_key() -> str:
    for env_var in GEMINI_API_KEY_ENV_VARS:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key
    joined = ", ".join(GEMINI_API_KEY_ENV_VARS)
    msg = f"Gemini API 키가 설정되지 않았습니다. 환경 변수를 확인하세요: {joined}"
    raise ValueError(msg)


def get_client() -> genai.Client:
    """Gemini 클라이언트 싱글톤을 반환한다."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=_resolve_api_key())
    return _client


async def invoke_structured(
    *,
    system_instruction: str,
    user_content: str,
    schema: type[TSchema],
    temperature: float = 0.0,
) -> TSchema:
    """Gemini 2.5 Flash Structured Output(Pydantic)을 반환한다."""
    client = get_client()
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    raw = (response.text or "").strip()
    if not raw:
        msg = "Gemini Structured Output 응답 본문이 비어 있습니다."
        raise ValueError(msg)
    return schema.model_validate_json(raw)


async def invoke_structured_safe(
    *,
    system_instruction: str,
    user_content: str,
    schema: type[TSchema],
    temperature: float = 0.0,
) -> TSchema | None:
    """Structured Output 호출. 실패 시 None."""
    try:
        return await invoke_structured(
            system_instruction=system_instruction,
            user_content=user_content,
            schema=schema,
            temperature=temperature,
        )
    except Exception:
        logger.exception("Archiver Gemini Structured Output failed")
        return None
