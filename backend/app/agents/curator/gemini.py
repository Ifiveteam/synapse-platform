"""Curator Gemini 클라이언트 — Archiver gemini.py 패턴 동일."""

from __future__ import annotations

import logging
import os
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.agents.curator.constants import GEMINI_API_KEY_ENV_VARS, GEMINI_MODEL

logger = logging.getLogger(__name__)
TSchema = TypeVar("TSchema", bound=BaseModel)

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        for env_var in GEMINI_API_KEY_ENV_VARS:
            api_key = os.getenv(env_var)
            if api_key:
                _client = genai.Client(api_key=api_key)
                return _client
        raise ValueError("Gemini API 키가 없습니다.")
    return _client


async def invoke_structured_safe(
    *,
    system_instruction: str,
    user_content: str,
    schema: type[TSchema],
    temperature: float = 0.0,
) -> TSchema | None:
    try:
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
            return None
        return schema.model_validate_json(raw)
    except Exception:
        logger.exception("Curator Gemini structured call failed")
        return None
