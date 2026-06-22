"""Curator 서비스 — API → Engine 연결."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curator.engine import CuratorEngine, get_curator_engine
from app.agents.curator.streaming import format_stream_event
from app.core.database.session import get_db

logger = logging.getLogger(__name__)


class CuratorService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        engine: CuratorEngine = Depends(get_curator_engine),
    ) -> None:
        self.db = db
        self.engine = engine

    async def generate_stream(
        self,
        *,
        message: str,
        user_id: uuid.UUID,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        initial_state = CuratorEngine.build_initial_state(
            messages=[HumanMessage(content=message)],
            user_id=user_id,
            session_id=session_id,
        )

        try:
            async for event in self.engine.stream(initial_state=initial_state, db=self.db):
                yield format_stream_event(event)
        except Exception:
            logger.exception("Curator stream error")
            yield 'event: token\ndata: {"content": "❌ 오류가 발생했습니다."}\n\n'
