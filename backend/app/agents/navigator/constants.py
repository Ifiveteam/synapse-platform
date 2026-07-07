"""Navigator 런타임 상수 SSOT — 축·모델·온도·에이전트 타입."""

from __future__ import annotations

# Synapse 행동 8축 (이상향 타깃) — 순서는 user_ideal_persona 컬럼과 동일해야 한다.
BEHAVIOR_AXES: tuple[str, ...] = (
    "exploration",
    "analytical",
    "creativity",
    "execution",
    "achievement_drive",
    "autonomy",
    "sociality",
    "sensitivity",
)

# 이상향 설계 축 — 가치관 10축 + 기질 3축 (프로파일러 점수 키와 동일 명칭).
# LLM이 이 13축으로 이상향을 설계하고, behavior_map이 여기서 8축을 파생한다.
VALUES_AXES: tuple[str, ...] = (
    "self_direction",
    "stimulation",
    "achievement",
    "power",
    "security",
    "benevolence",
    "universalism",
    "hedonism",
    "conformity",
    "tradition",
)
TEMPERAMENT_AXES: tuple[str, ...] = (
    "novelty_seeking",
    "persistence",
    "self_transcendence",
)
VALUES_TEMPERAMENT_AXES: tuple[str, ...] = VALUES_AXES + TEMPERAMENT_AXES

# 성향 disposition 6축 — profiler portrait(DispositionLLM)와 동일 키.
# 이상향 설계의 "주 신호"이자 화면 표시 축(현재→목표).
# ⚠️ exploration은 행동 8축과 이름이 같지만 정의가 다르다(콘텐츠 탐험성 vs 행동 탐색).
DISPOSITION_AXES: tuple[str, ...] = (
    "immersion",
    "exploration",
    "fandom",
    "trend",
    "info",
    "emotion",
)
DISPOSITION_LABELS_KO: dict[str, str] = {
    "immersion": "몰입도",
    "exploration": "탐험성",
    "fandom": "팬심",
    "trend": "트렌드민감",
    "info": "정보추구",
    "emotion": "감성지향",
}

# 관심 도메인 9개 — profiler portrait(_DOMAINS)와 동일. 이상향 목표 도메인 축.
INTEREST_DOMAINS: tuple[str, ...] = (
    "스포츠",
    "게임",
    "음악",
    "예능",
    "인물·일상",
    "영화·애니",
    "뉴스·시사",
    "지식·교육",
    "라이프·취미",
)

# 점수 범위 (프로파일러와 동일)
AXIS_MIN = 0.0
AXIS_MAX = 100.0

# Gemini
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")

# Step temperature
PROPOSE_TEMPERATURE = 0.4
INTERPRET_TEMPERATURE = 0.2
CHAT_TEMPERATURE = 0.7
GUIDE_TEMPERATURE = 0.5

# multi-turn 대화 (메시지 상한)
MAX_HISTORY_MESSAGES = 20

# DB ai_chat_logs.agent_type 필터
NAVIGATOR_AGENT_TYPE = "NAVIGATOR"

# user_ideal_persona.description 인코딩 (ideal_type + 근거 reasoning)
DESCRIPTION_SEP = "\n\n"

# 관심사 집계 상한
TOP_INTERESTS_LIMIT = 5

# 사용자-facing 스트림 오류 메시지 (SSE token·DB 영속 정책 SSOT)
STREAM_ERROR_PREFIX = "❌"
STREAM_ERROR_MESSAGE = (
    f"{STREAM_ERROR_PREFIX} 네비게이터 코어 엔진 오류가 발생했습니다."
)
