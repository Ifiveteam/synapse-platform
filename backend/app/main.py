"""
Synapse Platform — FastAPI 메인 앱
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# .env 로드 (가장 먼저 실행)
load_dotenv()

from app.api.v1.navigator import router as navigator_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Synapse Platform 서버 시작")
    yield
    print("🛑 서버 종료")


app = FastAPI(
    title="Synapse Platform API",
    description="Synapse AI Agent Platform — Navigator, Profiler, Indexer ...",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS (프론트엔드 Next.js 3000 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 등록 ──────────────────────────────
app.include_router(navigator_router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "platform": "Synapse"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
