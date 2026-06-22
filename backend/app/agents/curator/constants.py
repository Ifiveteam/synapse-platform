"""Curator 런타임 상수."""

from __future__ import annotations

import os

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")

VIDEO_SEARCH_LIMIT = 6
ANALYSIS_SEARCH_LIMIT = 4

CURATOR_AGENT_TYPE = "CURATOR"
STREAM_ERROR_MESSAGE = "❌ 오케스트레이터 오류가 발생했습니다."
