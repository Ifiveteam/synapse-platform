"""Synapse Platform FastAPI 애플리케이션 진입점."""

from __future__ import annotations

import logging

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
# httpx INFO 로그에 URL 쿼리(key= 등)가 그대로 노출되므로 WARNING 이상만 출력
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(
    title="Synapse Platform API",
    version="0.1.0",
    description="Multi-Agent System 백엔드 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5173",
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
