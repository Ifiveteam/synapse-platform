"""배치 스코프 스모크 테스트 (개발용, LLM 미사용).

AB·CD 시나리오의 핵심 불변식을 실제 DB에 합성 데이터로 검증한다:
  1) 소속 짝(link_source_catalog) 기록 + 겹치는 영상이 양쪽 배치에 무손실 포함
  2) fetch_catalog_rows_by_sources가 그 배치 영상만(합집합) 돌려줌
  3) sealed→profiling 원자 전환은 한 번만 성공(try_start_batch_profiling 중복 방지)

실행:
  cd backend
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/synapse \
    uv run python -m scripts.batch_smoke

테스트 유저/데이터는 끝에 삭제(cascade)하므로 DB에 잔여물을 남기지 않는다.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.core.database.session import AsyncSessionLocal
from app.models.analysis_batch import AnalysisBatch, AnalysisBatchStatus
from app.models.user import User
from app.models.user_analysis_source import (
    AnalysisSourceStage,
    AnalysisSourceStatus,
    UserAnalysisSource,
)
from app.models.user_watch_catalog import UserWatchCatalog
from app.repositories.analysis_source_repository import (
    batch_ready_to_profile,
    fetch_batch_source_ids,
    try_start_batch_profiling,
)
from app.repositories.indexer_repository import link_source_catalog
from app.repositories.profiler_repository import fetch_catalog_rows_by_sources

WINDOW = 63


def _ok(cond: bool, msg: str) -> None:
    print(("  [OK] " if cond else "  [FAIL] ") + msg)
    if not cond:
        raise AssertionError(msg)


async def _make_catalog(session, user_id, url, title) -> uuid.UUID:
    row = UserWatchCatalog(
        user_id=user_id,
        platform="youtube",
        url=url,
        title=title,
        channel="ch",
        watched_at=datetime.now(UTC),
    )
    session.add(row)
    await session.flush()
    return row.id


async def _make_source(session, user_id, batch_id, key) -> uuid.UUID:
    src = UserAnalysisSource(
        user_id=user_id,
        source_key=key,
        file_name=key,
        status=AnalysisSourceStatus.RUNNING,
        stage=AnalysisSourceStage.INDEXED,  # 인덱싱 완료 상태로 세팅
        batch_id=batch_id,
    )
    session.add(src)
    await session.flush()
    return src.id


async def main() -> None:
    async with AsyncSessionLocal() as session:
        user = User(
            email=f"smoke+{uuid.uuid4().hex}@test.local",
            google_sub_id=f"smoke-{uuid.uuid4().hex}",
            name="smoke",
        )
        session.add(user)
        await session.flush()
        uid = user.id

        try:
            # 배치 A(sealed), 배치 B(sealed) + 소스 각 1개
            batch_a = AnalysisBatch(
                id=uuid.uuid4(), user_id=uid, status=AnalysisBatchStatus.SEALED
            )
            batch_b = AnalysisBatch(
                id=uuid.uuid4(), user_id=uid, status=AnalysisBatchStatus.SEALED
            )
            session.add_all([batch_a, batch_b])
            await session.flush()
            src_a = await _make_source(session, uid, batch_a.id, "A.zip")
            src_b = await _make_source(session, uid, batch_b.id, "B.zip")

            # 영상: u1,u2 → A / u2(겹침),u3,u4 → B
            await _make_catalog(session, uid, "u1", "v1")
            await _make_catalog(session, uid, "u2", "v2")
            await _make_catalog(session, uid, "u3", "v3")
            await _make_catalog(session, uid, "u4", "v4")
            await link_source_catalog(session, uid, src_a, ["u1", "u2"])
            await link_source_catalog(session, uid, src_b, ["u2", "u3", "u4"])
            await session.flush()

            print("[1] 스코프 격리 + 겹침 무손실")
            rows_a = await fetch_catalog_rows_by_sources(
                session, uid, [str(src_a)], WINDOW
            )
            rows_b = await fetch_catalog_rows_by_sources(
                session, uid, [str(src_b)], WINDOW
            )
            urls_a = {r.url for r in rows_a}
            urls_b = {r.url for r in rows_b}
            _ok(urls_a == {"u1", "u2"}, f"배치 A = {{u1,u2}} (실제 {urls_a})")
            _ok(urls_b == {"u2", "u3", "u4"}, f"배치 B = {{u2,u3,u4}} (실제 {urls_b})")
            _ok("u2" in urls_a and "u2" in urls_b, "겹친 영상 u2가 양쪽에 무손실 포함")

            print("[2] 배치 트리거 가드")
            ready = await batch_ready_to_profile(session, batch_a.id)
            _ok(ready, "sealed + 모든 소스 인덱싱 완료 → ready=True")
            sids = await fetch_batch_source_ids(session, batch_a.id)
            _ok(sids == [src_a], f"배치 A source_ids = [src_a] (실제 {sids})")

            print("[3] sealed→profiling 원자 전환 (중복 방지)")
            first = await try_start_batch_profiling(session, batch_a.id)
            second = await try_start_batch_profiling(session, batch_a.id)
            _ok(first and not second, "첫 호출만 True, 두 번째 False")

            print("[4] 통합본 경로(빈 source_ids)")
            empty = await fetch_catalog_rows_by_sources(session, uid, [], WINDOW)
            _ok(empty == [], "source_ids 없으면 빈 목록(=통합본 분기로)")

            print("[5] cascade 삭제")
            await session.execute(delete(User).where(User.id == uid))
            await session.commit()
            async with AsyncSessionLocal() as s2:
                left = await s2.execute(
                    select(UserAnalysisSource).where(UserAnalysisSource.user_id == uid)
                )
                _ok(
                    len(list(left.scalars().all())) == 0,
                    "유저 삭제 → 소스/배치/소속 cascade 정리",
                )
            print("\n=== 모든 불변식 통과 ===")
        except Exception:
            await session.rollback()
            async with AsyncSessionLocal() as s3:
                await s3.execute(delete(User).where(User.id == uid))
                await s3.commit()
            raise


if __name__ == "__main__":
    asyncio.run(main())
