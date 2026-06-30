"""Archiver 런타임 상수 SSOT — 루프 한도·모델·온도·스크래핑 한도."""

from __future__ import annotations

# ┌───────────────────────────────────────────────────────────────── [SSOT_SYNC] ─┐
# │ 이 파일의 아래 상수는 익스텐션과 수동 동기화가 필요합니다.                      │
# │ ↔ extension/src/features/archiver/utils/limits.ts                            │
# │                                                                              │
# │ 전체 검색: [SSOT_SYNC]                                                       │
# │                                                                              │
# │ 매핑 (값·단위 반드시 일치):                                                   │
# │   MAX_BODY_LENGTH              ↔ MAX_BODY_LENGTH / MAX_TAB_CONTEXT_BODY_CHARS │
# │   QUALITY_THRESHOLD (0–100)    ↔ QUALITY_THRESHOLD (0–100)                   │
# │   MIN_CONTEXT_BODY_QUALITY     ↔ MIN_CONTEXT_BODY_QUALITY (0.0–1.0)          │
# │   DOM_STABILITY_TIMEOUT_MS     ↔ DOM_STABILITY_TIMEOUT_MS (ms)               │
# └──────────────────────────────────────────────────────────────────────────────┘

# ── [SSOT_SYNC] 익스텐션 동기화 상수 ────────────────────────────────────────────
MAX_BODY_LENGTH = 5_000
MAX_CONTEXT_BODY_CHARS = MAX_BODY_LENGTH

QUALITY_THRESHOLD = 35  # 0–100 척도; 본문 품질 채점 커트라인
MIN_CONTEXT_BODY_QUALITY = QUALITY_THRESHOLD / 100

DOM_STABILITY_TIMEOUT_MS = 500  # DOM mutation 안정화 quiet 대기 (ms)

# LangGraph evaluator 루프 한도
MAX_SEARCH_ATTEMPTS = 2
MAX_RETRIEVAL_ATTEMPTS = 2

# RAG 수집
RAG_SEARCH_LIMIT = 3

# multi-turn 대화 (user+assistant 메시지 쌍 상한)
MAX_HISTORY_MESSAGES = 20

# Router(classify) — Structured Output JSON 잘림 방지 (↔ scrap classifier 2048)
CLASSIFY_MODEL = "gemini-2.5-flash"
CLASSIFY_TEMPERATURE = 0.0
CLASSIFY_MAX_OUTPUT_TOKENS = 2048

# Step temperature
EVALUATE_TEMPERATURE = 0.0
SEARCH_TEMPERATURE = 0.2

# respond 생성 온도 — chitchat(is_general) vs factual(근거 기반)
RESPOND_CHITCHAT_TEMPERATURE = 0.8
RESPOND_FACTUAL_TEMPERATURE = 0.4

# Trace 미리보기
TRACE_PREVIEW_CHARS = 400

# 활성 탭 본문 스크래핑 ([SSOT_SYNC] MAX_BODY_LENGTH·QUALITY_THRESHOLD 참조)
MIN_CLIENT_CONTEXT_BODY_CHARS = 80
THIN_CONTEXT_BODY_CHARS = 500

# LangGraph RunnableConfig store 키
ARCHIVER_STORE_KEY = "archiver_store"

# DB ai_chat_logs.agent_type 필터
ARCHIVER_AGENT_TYPE = "ARCHIVER"

# 사용자-facing 스트림 오류 메시지 (SSE token·DB 영속 정책 SSOT)
STREAM_ERROR_PREFIX = "❌"
STREAM_ERROR_MESSAGE = f"{STREAM_ERROR_PREFIX} 아카이버 코어 엔진 오류가 발생했습니다."
