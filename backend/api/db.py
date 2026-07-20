from __future__ import annotations

import json
import logging
import os
from typing import Any

import asyncpg
from upstash_redis.asyncio import Redis as UpstashRedis
from dotenv import load_dotenv, find_dotenv
from fastapi import HTTPException

load_dotenv(find_dotenv(usecwd=True), override=True)

logger = logging.getLogger(__name__)

redis_client: UpstashRedis | None = None
pg_pool: asyncpg.Pool | None = None

SESSION_TTL_SECONDS = 60 * 60 * 4  # 4 hours

_CREATE_STUDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS students (
    student_id  TEXT PRIMARY KEY,
    grade       INT  NOT NULL,
    profile     JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

_CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    document_id  TEXT PRIMARY KEY,
    student_id   TEXT NOT NULL,
    title        TEXT NOT NULL,
    filename     TEXT NOT NULL,
    topics       JSONB NOT NULL DEFAULT '[]',
    chunk_count  INT NOT NULL DEFAULT 0,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


async def init_redis() -> None:
    global redis_client
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        raise RuntimeError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set")
    redis_client = UpstashRedis(url=url, token=token)
    await redis_client.ping()
    logger.info("Upstash Redis connected: %s", url)


async def close_redis() -> None:
    pass  # Upstash REST client is stateless


async def init_postgres() -> None:
    global pg_pool
    dsn = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/ncert_platform")
    ssl: str | bool = False
    if "sslmode=require" in dsn:
        dsn = dsn.replace("?sslmode=require&", "?").replace("?sslmode=require", "").replace("&sslmode=require", "")
        ssl = True
    pg_pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10, ssl=ssl)
    async with pg_pool.acquire() as conn:
        await conn.execute(_CREATE_STUDENTS_TABLE)
        await conn.execute(_CREATE_DOCUMENTS_TABLE)
    logger.info("Postgres connected and schema ready.")


async def close_postgres() -> None:
    if pg_pool:
        await pg_pool.close()
        logger.info("Postgres pool closed.")


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def save_session(session_id: str, state: dict[str, Any], ttl: int = SESSION_TTL_SECONDS) -> None:
    if redis_client is None:
        raise RuntimeError("Redis client not initialised.")
    await redis_client.setex(_session_key(session_id), ttl, json.dumps(state))


async def load_session(session_id: str) -> dict[str, Any]:
    if redis_client is None:
        raise RuntimeError("Redis client not initialised.")
    raw = await redis_client.get(_session_key(session_id))
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or has expired.")
    return json.loads(raw)


async def delete_session(session_id: str) -> None:
    if redis_client:
        await redis_client.delete(_session_key(session_id))


# ---------------------------------------------------------------------------
# Postgres helpers
# ---------------------------------------------------------------------------


async def get_student(student_id: str) -> dict[str, Any] | None:
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    row = await pg_pool.fetchrow(
        "SELECT grade, profile FROM students WHERE student_id = $1",
        student_id,
    )
    if row is None:
        return None
    raw = row["profile"]
    profile: dict[str, Any] = raw if isinstance(raw, dict) else json.loads(raw)
    profile["student_id"] = student_id
    profile["grade"] = row["grade"]
    return profile


async def upsert_student(student_id: str, grade: int, profile: dict[str, Any]) -> None:
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    serialisable = {k: v for k, v in profile.items() if k not in ("student_id", "grade")}
    await pg_pool.execute(
        """
        INSERT INTO students (student_id, grade, profile, created_at, updated_at)
        VALUES ($1, $2, $3::jsonb, NOW(), NOW())
        ON CONFLICT (student_id) DO UPDATE
            SET grade = EXCLUDED.grade,
                profile = EXCLUDED.profile,
                updated_at = NOW()
        """,
        student_id,
        grade,
        json.dumps(serialisable),
    )


# ---------------------------------------------------------------------------
# Documents (student-uploaded study material)
# ---------------------------------------------------------------------------


def _document_row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    raw_topics = data.get("topics")
    data["topics"] = raw_topics if isinstance(raw_topics, list) else json.loads(raw_topics or "[]")
    created_at = data.get("created_at")
    data["created_at"] = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    return data


async def insert_document(
    document_id: str,
    student_id: str,
    title: str,
    filename: str,
    topics: list[str],
    chunk_count: int,
) -> None:
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    await pg_pool.execute(
        """
        INSERT INTO documents (document_id, student_id, title, filename, topics, chunk_count, created_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, NOW())
        """,
        document_id,
        student_id,
        title,
        filename,
        json.dumps(topics),
        chunk_count,
    )


async def list_documents(student_id: str) -> list[dict[str, Any]]:
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    rows = await pg_pool.fetch(
        """
        SELECT document_id, title, filename, topics, chunk_count, created_at
        FROM documents
        WHERE student_id = $1
        ORDER BY created_at DESC
        """,
        student_id,
    )
    return [_document_row_to_dict(row) for row in rows]


async def get_document(document_id: str) -> dict[str, Any] | None:
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    row = await pg_pool.fetchrow(
        """
        SELECT document_id, student_id, title, filename, topics, chunk_count, created_at
        FROM documents
        WHERE document_id = $1
        """,
        document_id,
    )
    return _document_row_to_dict(row) if row else None


async def delete_document(document_id: str) -> None:
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    await pg_pool.execute("DELETE FROM documents WHERE document_id = $1", document_id)
