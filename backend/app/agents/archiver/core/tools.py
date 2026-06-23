"""Archiver Gemini Tool 정의 SSOT."""

from __future__ import annotations

from google.genai import types

GOOGLE_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())
