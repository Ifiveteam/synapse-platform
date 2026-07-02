"""Curator 런타임 상수."""

from __future__ import annotations

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")

VIDEO_SEARCH_LIMIT = 8
ANALYSIS_SEARCH_LIMIT = 6
RECENT_VIDEO_LIMIT = 8
TOP_CHANNEL_LIMIT = 5
HISTORY_MESSAGE_LIMIT = 10   # DB에서 로드할 최근 메시지 수
RECENT_CONTEXT_WINDOW = 6   # agent 프롬프트의 <최근_대화> 참고 블록에 넣을 과거 턴 수 (HumanMessage 기준)

CURATOR_AGENT_TYPE = "CURATOR"
STREAM_ERROR_MESSAGE = "❌ 큐레이터 오류가 발생했습니다."
