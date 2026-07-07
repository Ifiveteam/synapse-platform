"""YouTube 재생목록 서브에이전트 상수."""

from __future__ import annotations

# 검색 쿼리 수 = search 콜 수 (콜당 100유닛). 도메인별 다양성 위해 목표 도메인마다
# 1개씩 뽑는다(≈RAISE_DOMAINS_TOP_K). 늘리면 다양성↑·쿼터↑. 1로 낮추면 단일 주제로 수렴.
SEARCH_QUERIES_MAX = 3
CHANNELS_PER_QUERY = 25  # search?type=channel maxResults (쿼리 3개면 총 ~75 후보)
CURATED_CHANNELS = 10  # RSS로 펼칠 채널 수 (pick에서 선택)
UPLOADS_PER_CHANNEL = 10  # 채널당 RSS 수집 영상 수
MAX_ITEMS_TOTAL = 10  # 한 재생목록에 보여줄 최종 영상 수
RESERVOIR_TARGET = 30  # 여분 후보 목표 (즉시 교체용)
PRERANK_POOL = 40  # 큐레이션 전 임베딩 프리랭크 컷
MIN_VALID_CANDIDATES = 10  # 이만큼 못 채우면 자기교정(재발굴)
# discover 재발굴 상한. 후보가 MIN_VALID_CANDIDATES 미만이면 검색어를 넓혀 1회 재발굴한다
# (3년 필터·다양성 때문에 후보가 적을 때 결과가 1~2개로 붕괴하는 걸 방지). 2 = 최대 1회 재발굴.
MAX_ATTEMPTS = 2

# 쇼츠 제외 — videos.list 길이가 이 값 이하면 쇼츠로 보고 뺀다 (초)
SHORTS_MAX_SECONDS = 180

# 너무 오래된 영상 제외 — 발행일이 이보다 오래면 후보에서 뺀다 (최신 위주)
MAX_VIDEO_AGE_DAYS = 365 * 3

# discover 검색어에 넣을 '넓힐 목표 도메인' 수 (raise 상위)
RAISE_DOMAINS_TOP_K = 3

# 최종 재생목록에서 한 채널이 차지할 수 있는 최대 영상 수 (한 채널 독식 방지·다양성)
MAX_PER_CHANNEL = 3

PROPOSE_TEMPERATURE = 0.4
CURATE_TEMPERATURE = 0.5
