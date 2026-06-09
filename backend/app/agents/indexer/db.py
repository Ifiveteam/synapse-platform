import os

import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/synapse"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """pgvector 확장 + 테이블 생성"""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS video_vectors (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                channel TEXT,
                channel_url TEXT,
                url TEXT,
                watched_at TIMESTAMP,
                category TEXT,
                keywords TEXT[],
                duration INTEGER,
                is_shorts BOOLEAN,
                embedding vector(1024)
            )
        """)
        )
        conn.commit()
        print("DB 초기화 완료!")


def save_vectors(items: list[dict]):
    """벡터화된 데이터 pgvector에 저장"""
    with engine.connect() as conn:
        for item in items:
            conn.execute(
                text("""
                INSERT INTO video_vectors
                (title, channel, channel_url, url, watched_at, category, keywords, duration, is_shorts, embedding)
                VALUES (
                    :title, :channel, :channel_url, :url,
                    :watched_at, :category, :keywords, :duration, :is_shorts, :embedding
                )
            """),
                {
                    "title": item.get("title", ""),
                    "channel": item.get("channel", ""),
                    "channel_url": item.get("channel_url", ""),
                    "url": item.get("url", ""),
                    "watched_at": item.get("watched_at"),
                    "category": item.get("category", ""),
                    "keywords": item.get("keywords", []),
                    "duration": item.get("duration", 0),
                    "is_shorts": item.get("is_shorts", False),
                    "embedding": str(item.get("embedding", [])),
                },
            )
        conn.commit()
        print(f"{len(items)}개 저장 완료!")


def create_user_vector() -> list[float]:
    """저장된 모든 영상 벡터를 평균내서 유저 성향 벡터 생성"""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT embedding FROM video_vectors
            WHERE embedding IS NOT NULL
        """)
        )
        rows = result.fetchall()

    if not rows:
        print("저장된 벡터 없음!")
        return []

    embeddings = []
    for row in rows:
        vec_str = row[0]
        vec = [float(x) for x in vec_str.strip("[]").split(",")]
        embeddings.append(vec)

    user_vector = np.mean(embeddings, axis=0).tolist()
    print(
        f"유저 성향 벡터 생성 완료! (개수: {len(embeddings)}, 차원: {len(user_vector)})"
    )
    return user_vector