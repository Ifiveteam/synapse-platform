"""가이드 서브에이전트 상수 — 루프 한도 · RAG 검색용 성향/도메인 쿼리."""

from __future__ import annotations

MAX_RETRIEVE_ATTEMPTS = 2
MAX_GEN_ATTEMPTS = 2
CATALOG_SEARCH_LIMIT = 5

# 심화(성향)·확장(도메인) 각각 몇 개를 겨냥할지
DEEPEN_TOP_K = 2
EXPAND_TOP_K = 2

# 확장 다리 검색 — 이 유사도 이상만 '진입로'로 채택 (억지 연결 방지)
BRIDGE_SIM_THRESHOLD = 0.25

# 성향 6축 RAG 검색 문장 (키만으론 임베딩 검색이 약해서 문장으로)
DISPOSITION_QUERY_TEXT: dict[str, str] = {
    "immersion": "한 주제나 인물을 깊이 파고드는 몰입형·긴 호흡의 심층 콘텐츠",
    "exploration": "여러 분야를 넓게 넘나들며 낯선 주제를 시도하는 탐험형 콘텐츠",
    "fandom": "특정 인물·팀·그룹에 열광하는 팬덤 콘텐츠",
    "trend": "최신 유행·숏폼·화제성 즉시 소비 콘텐츠",
    "info": "학습·전문 지식·해설·분석 등 정보 지향 콘텐츠",
    "emotion": "정서·위로·공감 등 감성 지향 콘텐츠",
}

# 관심 도메인 9개 다리 검색 문장 (새 도메인에 가장 가까운 기존 시청 찾기)
DOMAIN_QUERY_TEXT: dict[str, str] = {
    "스포츠": "스포츠 경기·하이라이트·선수 관련 콘텐츠",
    "게임": "게임 플레이·공략·e스포츠 콘텐츠",
    "음악": "음악·뮤직비디오·공연·플레이리스트 콘텐츠",
    "예능": "예능·코미디·오락 콘텐츠",
    "인물·일상": "인물·브이로그·일상 기록 콘텐츠",
    "영화·애니": "영화·드라마·애니메이션 리뷰와 콘텐츠",
    "뉴스·시사": "뉴스·시사·정치·사회 이슈 콘텐츠",
    "지식·교육": "지식·교육·강의·다큐멘터리 등 배우는 콘텐츠",
    "라이프·취미": "라이프스타일·취미·요리·여행 콘텐츠",
}


def disposition_query(axis: str, relax_level: int = 0) -> str:
    """성향 축 검색 문장. 완화 레벨이 오르면 더 넓게(재검색용)."""
    base = DISPOSITION_QUERY_TEXT.get(axis, axis)
    if relax_level <= 0:
        return base
    return f"{base}. 이 성향과 조금이라도 관련된 다양한 영상"


def domain_query(domain: str) -> str:
    """도메인 다리 검색 문장."""
    return DOMAIN_QUERY_TEXT.get(domain, domain)
