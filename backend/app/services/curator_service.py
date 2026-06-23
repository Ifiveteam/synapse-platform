"""Curator 서비스 — API → Engine 연결 + 대화 히스토리 관리."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curator.constants import CURATOR_AGENT_TYPE, HISTORY_MESSAGE_LIMIT
from app.agents.curator.engine import CuratorEngine, get_curator_engine
from app.agents.curator.streaming import format_stream_event
from app.core.database.session import get_db
from app.models.chat import AIChatLog

logger = logging.getLogger(__name__)


class CuratorService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        engine: CuratorEngine = Depends(get_curator_engine),
    ) -> None:
        self.db = db
        self.engine = engine

    async def _load_history(self, session_id: str, user_id: uuid.UUID) -> list[BaseMessage]:
        """session_id 기준으로 최근 대화 히스토리를 로드한다."""
        rows = (await self.db.execute(
            select(AIChatLog.role, AIChatLog.content)
            .where(
                AIChatLog.session_id == session_id,
                AIChatLog.user_id == user_id,
                AIChatLog.agent_type == CURATOR_AGENT_TYPE,
            )
            .order_by(AIChatLog.created_at.desc())
            .limit(HISTORY_MESSAGE_LIMIT)
        )).fetchall()

        messages: list[BaseMessage] = []
        for row in reversed(rows):
            if row.role == "user":
                messages.append(HumanMessage(content=row.content))
            else:
                messages.append(AIMessage(content=row.content))
        return messages

    async def list_sessions(self, user_id: uuid.UUID) -> list[dict]:
        """유저의 큐레이터 채팅 세션 목록을 최신순으로 반환한다."""
        from sqlalchemy import text

        rows = (await self.db.execute(
            text("""
                WITH session_first AS (
                    SELECT DISTINCT ON (session_id)
                        session_id,
                        content AS title
                    FROM ai_chat_logs
                    WHERE user_id = :uid
                      AND agent_type = :agent_type
                      AND role = 'user'
                    ORDER BY session_id, created_at ASC
                ),
                session_last AS (
                    SELECT session_id, MAX(created_at) AS updated_at
                    FROM ai_chat_logs
                    WHERE user_id = :uid AND agent_type = :agent_type
                    GROUP BY session_id
                )
                SELECT sf.session_id, sf.title, sl.updated_at
                FROM session_first sf
                JOIN session_last sl ON sf.session_id = sl.session_id
                ORDER BY sl.updated_at DESC
                LIMIT 30
            """),
            {"uid": str(user_id), "agent_type": CURATOR_AGENT_TYPE},
        )).fetchall()

        return [
            {"session_id": r.session_id, "title": r.title, "updated_at": r.updated_at}
            for r in rows
        ]

    async def get_session_messages(self, session_id: str, user_id: uuid.UUID) -> list[dict]:
        """세션의 메시지 목록을 시간순으로 반환한다."""
        rows = (await self.db.execute(
            select(AIChatLog.role, AIChatLog.content)
            .where(
                AIChatLog.session_id == session_id,
                AIChatLog.user_id == user_id,
                AIChatLog.agent_type == CURATOR_AGENT_TYPE,
            )
            .order_by(AIChatLog.created_at.asc())
        )).fetchall()
        return [{"role": r.role, "content": r.content} for r in rows]

    async def delete_session(self, session_id: str, user_id: uuid.UUID) -> None:
        """세션의 모든 메시지를 삭제한다."""
        from sqlalchemy import delete as sql_delete

        await self.db.execute(
            sql_delete(AIChatLog).where(
                AIChatLog.session_id == session_id,
                AIChatLog.user_id == user_id,
                AIChatLog.agent_type == CURATOR_AGENT_TYPE,
            )
        )
        await self.db.commit()

    async def _save_turn(
        self,
        session_id: str,
        user_id: uuid.UUID,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """유저·어시스턴트 한 턴을 DB에 저장한다."""
        self.db.add(AIChatLog(
            session_id=session_id,
            user_id=user_id,
            agent_type=CURATOR_AGENT_TYPE,
            role="user",
            content=user_message,
        ))
        self.db.add(AIChatLog(
            session_id=session_id,
            user_id=user_id,
            agent_type=CURATOR_AGENT_TYPE,
            role="assistant",
            content=assistant_message,
        ))
        await self.db.commit()

    async def generate_stream(
        self,
        *,
        message: str,
        user_id: uuid.UUID,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        history = await self._load_history(session_id, user_id)

        initial_state = CuratorEngine.build_initial_state(
            messages=history + [HumanMessage(content=message)],
            user_id=user_id,
            session_id=session_id,
        )

        response_tokens: list[str] = []
        try:
            async for event in self.engine.stream(initial_state=initial_state, db=self.db):
                yield format_stream_event(event)
                if event.event == "token":
                    response_tokens.append(event.content)
        except Exception:
            logger.exception("Curator stream error")
            yield 'event: token\ndata: {"content": "❌ 오류가 발생했습니다."}\n\n'
            return

        assistant_response = "".join(response_tokens)
        if assistant_response:
            try:
                await self._save_turn(session_id, user_id, message, assistant_response)
            except Exception:
                logger.error("Failed to save chat history — history will not accumulate for session %s", session_id, exc_info=True)
