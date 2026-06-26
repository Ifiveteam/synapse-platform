#!/usr/bin/env python
"""데이터베이스 리셋 스크립트"""

import sys
from pathlib import Path

# 백엔드 경로 추가 (scripts/ 한 단계 위가 backend 루트)
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio

from sqlalchemy import text

from app.core.env import load_backend_env

load_backend_env()

import app.models  # noqa: E402,F401 - 모든 모델 등록
from app.core.database.base import Base  # noqa: E402
from app.core.database.session import engine  # noqa: E402


async def reset_db():
    print("🗑️  데이터베이스 리셋 중...")
    try:
        async with engine.begin() as conn:
            # CASCADE로 모든 테이블 삭제
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            print("✓ 기존 테이블 삭제 완료")

        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.run_sync(Base.metadata.create_all)
            print("✓ 새 테이블 생성 완료")

        print("✅ 데이터베이스 리셋 완료!")
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(reset_db())
