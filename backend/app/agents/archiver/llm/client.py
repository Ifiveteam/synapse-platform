"""Archiver Gemini client — module-level singleton connection pool."""

from __future__ import annotations

import os

from google import genai

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


def _resolve_api_key() -> str:
    for env_var in GEMINI_API_KEY_ENV_VARS:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key
    joined = ", ".join(GEMINI_API_KEY_ENV_VARS)
    msg = f"Gemini API 키가 설정되지 않았습니다. 환경 변수를 확인하세요: {joined}"
    raise ValueError(msg)


# 모듈 로드 시점에 최초 1회만 클라이언트 커넥션 풀 생성 (성능 최적화)
gemini_client = genai.Client(api_key=_resolve_api_key())
