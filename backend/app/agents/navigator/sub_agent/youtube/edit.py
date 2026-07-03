"""재생목록 편집 연산 — 영상 1개 새로고침(규칙) + 채팅 부분수정(LLM, SSE).

보충 우선순위: ① reservoir → ② channels re-RSS → ③ 검색(add_theme).
채널 발굴·RSS 수집 IO는 client.py.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.agents.navigator.llm import invoke_structured_safe
from app.agents.navigator.schemas import NavigatorStreamEvent, PlaylistItem
from app.agents.navigator.sub_agent.youtube.client import (
    fetch_channel_uploads,
    filter_out_shorts,
    search_channels,
)
from app.agents.navigator.sub_agent.youtube.constants import (
    CHANNELS_PER_QUERY,
    CURATED_CHANNELS,
    RESERVOIR_TARGET,
    UPLOADS_PER_CHANNEL,
)
from app.agents.navigator.sub_agent.youtube.schemas import EditSpec
from app.agents.navigator.sub_agent.youtube.store import PlaylistStore


def _to_item(v) -> PlaylistItem:
    return PlaylistItem(
        video_id=v.video_id,
        title=v.title,
        channel=v.channel,
        channel_id=v.channel_id,
        thumbnail_url=v.thumbnail_url,
    )


# ── 영상 1개 새로고침 (규칙, LLM 없음) ───────────────────────────


@dataclass(frozen=True, slots=True)
class RefreshResult:
    new_item: PlaylistItem | None  # None = 교체할 후보 없음
    items: list[PlaylistItem]
    reservoir: list[PlaylistItem]


async def refresh_item(
    *,
    store: PlaylistStore | None,
    user_id: uuid.UUID,
    items: list[PlaylistItem],
    reservoir: list[PlaylistItem],
    channel_ids: list[str],
    target_video_id: str,
) -> RefreshResult:
    """target 영상을 새 후보로 교체. ① 저수지 → ② 채널 re-RSS 순."""
    shown = {it.video_id for it in items}
    new_reservoir = list(reservoir)

    # ① 저수지에서 미표시 후보 1개
    new_item: PlaylistItem | None = None
    for idx, cand in enumerate(new_reservoir):
        if cand.video_id not in shown:
            new_item = cand
            new_reservoir.pop(idx)
            break

    # ② 저수지 비면 → 저장 채널 re-RSS (무료)
    if new_item is None and channel_ids:
        watched = await store.fetch_watched_video_ids(user_id) if store else set()
        results = await asyncio.gather(
            *(
                fetch_channel_uploads(channel_id=cid, limit=UPLOADS_PER_CHANNEL)
                for cid in channel_ids
            )
        )
        seen: set[str] = set()
        fresh: list[PlaylistItem] = []
        for vids in results:
            for v in vids:
                if v.video_id in shown or v.video_id in watched or v.video_id in seen:
                    continue
                seen.add(v.video_id)
                fresh.append(_to_item(v))
        fresh = await filter_out_shorts(fresh)  # 교체 후보도 쇼츠 제외
        if fresh:
            new_item = fresh[0]
            new_reservoir = (new_reservoir + fresh[1:])[:RESERVOIR_TARGET]

    if new_item is None:
        return RefreshResult(new_item=None, items=items, reservoir=reservoir)

    new_items = [new_item if it.video_id == target_video_id else it for it in items]
    return RefreshResult(new_item=new_item, items=new_items, reservoir=new_reservoir)


# ── 채팅 부분수정 (LLM, SSE) ─────────────────────────────────────


def _ev(event: str, content: str) -> NavigatorStreamEvent:
    return NavigatorStreamEvent(event=event, content=content)


async def _interpret(message: str, items: list[PlaylistItem]) -> EditSpec | None:
    listed = "\n".join(f"{i}. {it.title} · {it.channel}" for i, it in enumerate(items))
    prompt = f"""사용자의 재생목록 수정 요청을 해석하라.

[현재 재생목록 영상 (번호. 제목 · 채널)]
{listed}

[사용자 요청] {message}

- scope: reshuffle(재구성)/swap(특정 영상 교체)/add_theme(새 주제 추가).
- target_indices: 바꾸거나 빼야 할 영상의 **번호(0-기반 인덱스)**, 위 목록 범위 내에서만. 보통 1~2개.
- new_query: 새 주제가 필요하면(add_theme) 채널 검색어, 아니면 빈 문자열.
- note: 무엇을 어떻게 바꾸는지 한 줄 요약(한국어)."""
    return await invoke_structured_safe(
        system_instruction=prompt,
        user_content="요청을 해석하세요.",
        schema=EditSpec,
        temperature=0.2,
    )


async def edit_playlist(
    *,
    store: PlaylistStore | None,
    user_id: uuid.UUID,
    items: list[PlaylistItem],
    reservoir: list[PlaylistItem],
    channels: list[dict],
    message: str,
) -> AsyncIterator[NavigatorStreamEvent]:
    """채팅 요청으로 1~2개 부분수정. status 이벤트 + 최종 playlist 이벤트(전체 build JSON)."""
    yield _ev("status", "요청을 이해하는 중...")
    spec = await _interpret(message, items)

    shown = {it.video_id for it in items}
    watched = await store.fetch_watched_video_ids(user_id) if store else set()
    new_channels = list(channels)
    new_videos: list[PlaylistItem] = []  # add_theme 신규 (교체 시 우선 사용)

    if spec is None:
        yield _ev("status", "요청을 이해하지 못했어요. 그대로 둘게요.")
        targets: set[str] = set()
    else:
        yield _ev("status", spec.note or "재생목록을 수정하는 중...")
        targets = {
            items[i].video_id for i in spec.target_indices if 0 <= i < len(items)
        }

        if spec.scope == "add_theme" and spec.new_query.strip():
            yield _ev("status", f"'{spec.new_query}' 채널을 찾는 중...")
            found = await search_channels(
                query=spec.new_query, max_results=CHANNELS_PER_QUERY
            )
            picked = found[:CURATED_CHANNELS]
            results = await asyncio.gather(
                *(
                    fetch_channel_uploads(
                        channel_id=c.channel_id, limit=UPLOADS_PER_CHANNEL
                    )
                    for c in picked
                )
            )
            known = {c.get("channel_id") for c in new_channels}
            for c, vids in zip(picked, results, strict=True):
                if c.channel_id not in known:
                    new_channels.append({"channel_id": c.channel_id, "title": c.title})
                for v in vids:
                    if v.video_id not in shown and v.video_id not in watched:
                        new_videos.append(_to_item(v))
            new_videos = await filter_out_shorts(new_videos)  # 쇼츠 제외

        # 바꿀 대상 미지정인데 교체 의도면 끝의 1~2개를 기본 타깃으로
        if not targets and spec.scope in ("swap", "add_theme"):
            targets = {it.video_id for it in items[-2:]}

    reservoir_pool = [r for r in reservoir if r.video_id not in shown]
    # 저수지 부족 & 신규 없음 → 기존 채널 re-RSS
    if targets and not new_videos and len(reservoir_pool) < len(targets):
        cids = [c["channel_id"] for c in channels if c.get("channel_id")]
        results = await asyncio.gather(
            *(
                fetch_channel_uploads(channel_id=cid, limit=UPLOADS_PER_CHANNEL)
                for cid in cids
            )
        )
        fetched: list[PlaylistItem] = []
        for vids in results:
            for v in vids:
                if v.video_id not in shown and v.video_id not in watched:
                    fetched.append(_to_item(v))
        reservoir_pool.extend(await filter_out_shorts(fetched))  # 쇼츠 제외

    # add_theme 신규를 앞에 두어 교체가 새 주제를 우선 사용
    pool = new_videos + reservoir_pool

    # pool 중복 제거
    seen: set[str] = set()
    uniq_pool: list[PlaylistItem] = []
    for p in pool:
        if p.video_id not in seen:
            seen.add(p.video_id)
            uniq_pool.append(p)

    # 타깃을 pool 후보로 교체 (위치 유지)
    used = set(shown)
    pool_q = iter(uniq_pool)
    new_items: list[PlaylistItem] = []
    for it in items:
        if it.video_id in targets:
            repl = next((p for p in pool_q if p.video_id not in used), None)
            if repl is not None:
                used.add(repl.video_id)
                new_items.append(repl)
                continue
        new_items.append(it)

    final_ids = {i.video_id for i in new_items}
    new_reservoir = [p for p in uniq_pool if p.video_id not in final_ids][
        :RESERVOIR_TARGET
    ]

    payload = {
        "items": [i.model_dump() for i in new_items],
        "reservoir": [r.model_dump() for r in new_reservoir],
        "channels": new_channels,
    }
    yield _ev("playlist", json.dumps(payload, ensure_ascii=False))
