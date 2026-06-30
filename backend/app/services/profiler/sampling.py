"""영상 분석 샘플 선정 (catalog 행 기반, DB 무관).

선별 = 카테고리 × 포맷(롱/숏) 2갈래. 각 (카테고리, 포맷)에서 시청 많은 상위 채널
대표 1편씩. 대표성을 위해 글로벌 top이 아니라 카테고리별로 고르게 뽑는다.

- 롱폼 대표: 최근 시청순 (watched_at desc). 자막→Gemini로 깊게 분석됨.
- 숏폼 대표: 설명/태그 있는 것 중 최근순. 숏폼은 자막을 안 뽑으므로 제목·설명·태그가
  유일한 의미 신호 → 둘 다 빈 영상밖에 없는 채널은 스킵(깊은 분석 제외, 통계엔 잔존).
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from app.models.user_watch_catalog import UserWatchCatalog

TOP_CHANNELS_PER_GROUP = 5
MAX_TOTAL_SAMPLES = 150  # 카테고리수 × 2포맷 × 5 상한 (안전장치)


def _has_meta(row: UserWatchCatalog) -> bool:
    """숏폼 의미 신호 = 설명 또는 태그 존재."""
    desc = (row.description or "").strip()
    tags = row.tags if isinstance(row.tags, list) else None
    return bool(desc) or bool(tags)


def _pick_representative(
    rows: list[UserWatchCatalog],
    seen: set[uuid.UUID],
    *,
    is_shorts: bool,
) -> UserWatchCatalog | None:
    """채널 대표 1편 — 최근 시청순. 숏폼은 설명/태그 있는 것만 후보."""
    candidates = [r for r in rows if r.id not in seen]
    if is_shorts:
        candidates = [r for r in candidates if _has_meta(r)]
    if not candidates:
        return None
    rep = max(candidates, key=lambda r: r.watched_at)
    seen.add(rep.id)
    return rep


def _top_channels(rows: list[UserWatchCatalog]) -> list[list[UserWatchCatalog]]:
    """채널별로 묶어 시청량(영상 수) 상위 N채널의 행 묶음 반환."""
    by_channel: dict[str, list[UserWatchCatalog]] = defaultdict(list)
    for row in rows:
        by_channel[row.channel].append(row)
    ranked = sorted(by_channel.values(), key=len, reverse=True)
    return ranked[:TOP_CHANNELS_PER_GROUP]


def select_analysis_sample(
    rows: list[UserWatchCatalog],
    *,
    max_total: int = MAX_TOTAL_SAMPLES,
) -> list[UserWatchCatalog]:
    """카테고리 × 포맷 2갈래 선별. 각 그룹 상위 채널당 대표 1편."""
    if not rows:
        return []

    by_category: dict[str, list[UserWatchCatalog]] = defaultdict(list)
    for row in rows:
        by_category[row.youtube_category_id or "unknown"].append(row)

    seen: set[uuid.UUID] = set()
    picked: list[UserWatchCatalog] = []

    for cat_rows in by_category.values():
        long_rows = [r for r in cat_rows if not r.is_shorts]
        short_rows = [r for r in cat_rows if r.is_shorts]
        for group_rows, is_shorts in ((long_rows, False), (short_rows, True)):
            for channel_rows in _top_channels(group_rows):
                if len(picked) >= max_total:
                    return picked
                rep = _pick_representative(channel_rows, seen, is_shorts=is_shorts)
                if rep is not None:
                    picked.append(rep)

    return picked
