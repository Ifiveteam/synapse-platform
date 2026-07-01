"""Synapse Platform FastAPI 애플리케이션 진입점."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from app.core.env import load_backend_env

load_backend_env()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.v1 import api_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)
logging.getLogger("app.agents.aggregator.workflow").setLevel(logging.INFO)
logging.getLogger("app.agents.archiver.workflow").setLevel(logging.INFO)
logging.getLogger("app.agents.archiver.observability").setLevel(logging.INFO)
# httpx INFO 로그에 URL 쿼리(key= 등)가 그대로 노출되므로 WARNING 이상만 출력
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 수명주기 — 고아 인덱싱 소스 정리 + Takeout 자동분석 스케줄러 기동/종료."""
    from app.core.database.session import AsyncSessionLocal
    from app.repositories.analysis_source_repository import fail_orphan_sources
    from app.services.takeout_scheduler import scheduler_loop

    # 재시작으로 인메모리 큐가 비었으므로, 이전 프로세스의 진행 중(pending/running)
    # 소스는 되살릴 수 없다 → failed로 정리(화면에 '분류/분석 중' 영구표시 방지).
    async with AsyncSessionLocal() as session:
        orphaned = await fail_orphan_sources(session)
        await session.commit()
    if orphaned:
        logging.getLogger(__name__).info(
            "[startup] 고아 인덱싱 소스 %d건 failed 처리", orphaned
        )

    task = asyncio.create_task(scheduler_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Synapse Platform API",
    version="0.1.0",
    description="Multi-Agent System 백엔드 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
