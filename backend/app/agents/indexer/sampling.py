"""카테고리 × 영상 타입별 대표 샘플 선정."""

from collections import defaultdict

from app.agents.indexer.prompt import DEFAULT_CATEGORY


def select_samples(items: list[dict], per_group: int = 5) -> list[dict]:
    """카테고리·숏츠/롱폼 그룹별 최신 watched_at 상위 N개."""
    groups: dict[tuple[str, bool], list[dict]] = defaultdict(list)
    for item in items:
        category = item.get("category") or DEFAULT_CATEGORY
        is_shorts = bool(item.get("is_shorts"))
        groups[(category, is_shorts)].append(item)

    selected: list[dict] = []
    for group_items in groups.values():
        ordered = sorted(
            group_items,
            key=lambda row: row.get("watched_at", ""),
            reverse=True,
        )
        selected.extend(ordered[:per_group])
    return selected
