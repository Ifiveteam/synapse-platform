"""재생목록 서브에이전트 Store Port — 시청기록 근거를 repository에 위임.

가이드 sub_agent의 store.py 패턴 미러. 노드가 DB를 직접 모르고 service가 주입한다.
(채널 검색·RSS는 DB가 아니므로 client를 노드가 직접 호출)
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from langchain_core.runnables import RunnableConfig

from app.agents.navigator.sub_agent._shared import (
    build_run_config as _build_run_config,
)
from app.agents.navigator.sub_agent._shared import (
    get_store as _get_store,
)
from app.agents.navigator.sub_agent.youtube.schemas import WatchGrounding


@runtime_checkable
class PlaylistStore(Protocol):
    """시청기록 조회 Port (repository가 구현, service가 주입)."""

    async def fetch_watch_grounding(self, user_id: uuid.UUID) -> WatchGrounding: ...

    async def fetch_watched_video_ids(self, user_id: uuid.UUID) -> set[str]: ...


_PLAYLIST_STORE_KEY = "playlist_store"


def build_run_config(store: PlaylistStore | None) -> RunnableConfig:
    return _build_run_config(_PLAYLIST_STORE_KEY, store)


def get_store(config: RunnableConfig | None) -> PlaylistStore | None:
    return _get_store(_PLAYLIST_STORE_KEY, config)
