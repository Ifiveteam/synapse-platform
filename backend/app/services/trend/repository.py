"""트렌드 분석 게시판 인메모리 저장소."""

from __future__ import annotations

from app.services.trend.types import TrendPostRecord

_posts: dict[str, TrendPostRecord] = {}


def save_post(post: TrendPostRecord) -> None:
    _posts[post["post_id"]] = post


def get_post(post_id: str) -> TrendPostRecord | None:
    return _posts.get(post_id)


def list_posts() -> list[TrendPostRecord]:
    return list(_posts.values())
