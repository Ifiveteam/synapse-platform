"""Archiver 런타임 상수 SSOT — 루프 한도·모델·온도·스크래핑 한도."""

from __future__ import annotations

# LangGraph evaluator 루프 한도
MAX_SEARCH_ATTEMPTS = 2
MAX_RETRIEVAL_ATTEMPTS = 2

# RAG 수집
RAG_SEARCH_LIMIT = 3

# Gemini
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")

# Step temperature
CLASSIFY_TEMPERATURE = 0.0
EVALUATE_TEMPERATURE = 0.0
SEARCH_TEMPERATURE = 0.2

# respond route별 생성 온도 (ArchiverRoute.value 키)
RESPOND_TEMPERATURES: dict[str, float] = {
    "BASIC": 0.2,
    "RAG": 0.3,
    "SEARCH": 0.5,
    "GENERAL": 0.7,
}
RESPOND_DEFAULT_TEMPERATURE = 0.4

# Trace 미리보기
TRACE_PREVIEW_CHARS = 400

# 활성 탭 본문 스크래핑
MAX_CONTEXT_BODY_CHARS = 5_000

# LangGraph RunnableConfig store 키
ARCHIVER_STORE_KEY = "archiver_store"

# DB ai_chat_logs.agent_type 필터
ARCHIVER_AGENT_TYPE = "ARCHIVER"

# 사용자-facing 스트림 오류 메시지
STREAM_ERROR_MESSAGE = "❌ 아카이버 코어 엔진 오류가 발생했습니다."
