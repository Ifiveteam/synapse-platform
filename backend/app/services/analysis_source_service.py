"""업로드 소스 키 생성 및 분석 이력 갱신."""

from __future__ import annotations

import hashlib
import uuid

from app.core.database.session import AsyncSessionLocal
from app.repositories.analysis_source_repository import (
    complete_indexed_siblings,
    mark_source_completed,
    mark_source_failed,
    mark_source_running,
    mark_source_stage,
)


def drive_source_key(file_id: str) -> str:
    return f"drive:{file_id}"


def upload_source_key(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"upload:{digest}"


async def complete_source_async(
    source_id: uuid.UUID | str | None,
    profile_history_id: uuid.UUID | str | None,
) -> None:
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    pid = uuid.UUID(str(profile_history_id)) if profile_history_id else None
    async with AsyncSessionLocal() as session:
        await mark_source_completed(session, sid, pid)
        await session.commit()


async def fail_source_async(source_id: uuid.UUID | str | None) -> None:
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    async with AsyncSessionLocal() as session:
        await mark_source_failed(session, sid)
        await session.commit()


async def complete_analysis_batch_async(
    user_id: uuid.UUID | str,
    source_id: uuid.UUID | str | None,
    profile_history_id: uuid.UUID | str | None,
) -> None:
    """배치 분석 성공 완료 — 트리거 소스 completed(+프로필) + 형제 indexed 전부 completed."""
    if source_id is None:
        return
    uid = uuid.UUID(str(user_id))
    sid = uuid.UUID(str(source_id))
    pid = uuid.UUID(str(profile_history_id)) if profile_history_id else None
    async with AsyncSessionLocal() as session:
        await mark_source_completed(session, sid, pid)
        await complete_indexed_siblings(session, uid)
        await session.commit()


async def resolve_indexed_siblings_async(user_id: uuid.UUID | str) -> None:
    """배치 분석 실패 시 — 분류만 성공한(indexed) 형제들은 completed로 마무리."""
    uid = uuid.UUID(str(user_id))
    async with AsyncSessionLocal() as session:
        await complete_indexed_siblings(session, uid)
        await session.commit()


async def mark_source_running_async(source_id: uuid.UUID | str | None) -> None:
    """pending → running/indexing (디스패처가 실제 실행 시작 시)."""
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    async with AsyncSessionLocal() as session:
        await mark_source_running(session, sid)
        await session.commit()


async def set_source_stage_async(source_id: uuid.UUID | str | None, stage: str) -> None:
    """진행 단계(indexing→profiling) 갱신. 표시용."""
    if source_id is None:
        return
    sid = uuid.UUID(str(source_id))
    async with AsyncSessionLocal() as session:
        await mark_source_stage(session, sid, stage)
        await session.commit()
