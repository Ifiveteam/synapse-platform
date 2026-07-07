"""Reporter 에이전트 런타임 상수."""

from __future__ import annotations

import os

# Phase 3-1: B2B 마크다운 리포트 생성 전용 Gemini 3 Flash 계열 모델.
REPORTER_GEMINI_MODEL = os.getenv("REPORTER_GEMINI_MODEL", "gemini-3-flash-preview")

REPORTER_TEMPERATURE = float(os.getenv("REPORTER_TEMPERATURE", "0.4"))
REPORTER_MAX_OUTPUT_TOKENS = int(os.getenv("REPORTER_MAX_OUTPUT_TOKENS", "8192"))

# 급상승 키워드·도메인 등 리포트 최소 데이터 임계값
MIN_TRENDING_KEYWORDS = 1
MIN_DOMAIN_ACTIVE_USERS = 1
