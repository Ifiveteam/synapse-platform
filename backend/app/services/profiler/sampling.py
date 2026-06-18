"""영상 분석 샘플 선정 (catalog 행 기반, DB 무관)."""

from __future__ import annotations

import uuid

from app.models.user_watch_catalog import UserWatchCatalog


def _pick_representative(
    rows: list[UserWatchCatalog],
    seen: set[uuid.UUID],
) -> UserWatchCatalog | None:
    for row in rows:
        if row.id not in seen:
            seen.add(row.id)
            return row
    return None


def select_analysis_sample(
    rows: list[UserWatchCatalog],
    *,
    top_channels: int = 5,
) -> list[UserWatchCatalog]:
    """롱/숏 각 top N 채널당 1편 + 카테고리별 top N 채널당 1편 (dedupe)."""
    if not rows:
        return []

    seen: set[uuid.UUID] = set()
    picked: list[UserWatchCatalog] = []

    def add_group(group_rows: list[UserWatchCatalog]) -> None:
        by_channel: dict[str, list[UserWatchCatalog]] = {}
        for row in group_rows:
            by_channel.setdefault(row.channel, []).append(row)
        top = sorted(by_channel.items(), key=lambda x: len(x[1]), reverse=True)[
            :top_channels
        ]
        for _, channel_rows in top:
            rep = _pick_representative(channel_rows, seen)
            if rep:
                picked.append(rep)

    long_rows = [r for r in rows if not r.is_shorts]
    short_rows = [r for r in rows if r.is_shorts]
    add_group(long_rows)
    add_group(short_rows)

    by_category: dict[str, list[UserWatchCatalog]] = {}
    for row in rows:
        key = row.youtube_category_id or "unknown"
        by_category.setdefault(key, []).append(row)

    for cat_rows in by_category.values():
        by_channel: dict[str, list[UserWatchCatalog]] = {}
        for row in cat_rows:
            by_channel.setdefault(row.channel, []).append(row)
        top = sorted(by_channel.items(), key=lambda x: len(x[1]), reverse=True)[
            :top_channels
        ]
        for _, channel_rows in top:
            rep = _pick_representative(channel_rows, seen)
            if rep:
                picked.append(rep)

    return picked
