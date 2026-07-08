"""Curator 런타임 상수."""

from __future__ import annotations

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")

VIDEO_SEARCH_LIMIT = 8
ANALYSIS_SEARCH_LIMIT = 6
# 코사인 유사도 최소 기준 — 이보다 낮으면 "가장 가까운 것"이어도 무관한 결과다.
# 임계값 없이 무조건 top-N을 반환하면, 채널명처럼 임베딩 공간에서 가까운 게 없는
# 검색어에도 억지로 결과를 만들어내 LLM이 무관한 내용을 사실인 것처럼 서술하는
# 할루시네이션이 실제로 관찰됐다.
SEARCH_SIMILARITY_THRESHOLD = 0.5
RECENT_VIDEO_LIMIT = 8
TOP_CHANNEL_LIMIT = 5
HISTORY_MESSAGE_LIMIT = 10  # DB에서 로드할 최근 메시지 수
RECENT_CONTEXT_WINDOW = (
    6  # agent 프롬프트의 <최근_대화> 참고 블록에 넣을 과거 턴 수 (HumanMessage 기준)
)

CURATOR_AGENT_TYPE = "CURATOR"
STREAM_ERROR_MESSAGE = "❌ 큐레이터 오류가 발생했습니다."
