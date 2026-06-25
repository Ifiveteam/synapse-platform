"""YouTube 재생목록 서브에이전트 상수."""

from __future__ import annotations

SEARCH_QUERIES_MAX = 2  # 검색 쿼리 수 = search 콜 수 (콜당 100유닛)
CHANNELS_PER_QUERY = 25  # search?type=channel maxResults
CURATED_CHANNELS = 10  # RSS로 펼칠 채널 수 (pick에서 선택)
UPLOADS_PER_CHANNEL = 10  # 채널당 RSS 수집 영상 수
MAX_ITEMS_TOTAL = 10  # 한 재생목록에 보여줄 최종 영상 수
RESERVOIR_TARGET = 30  # 여분 후보 목표 (즉시 교체용)
PRERANK_POOL = 40  # 큐레이션 전 임베딩 프리랭크 컷
MIN_VALID_CANDIDATES = 10  # 이만큼 못 채우면 자기교정(재발굴)
MAX_ATTEMPTS = 2  # discover 재발굴 상한 (검색 콜 폭주 방지)

PROPOSE_TEMPERATURE = 0.4
CURATE_TEMPERATURE = 0.5
