"""
Database connection setup for the NCERT Learning Platform API.

Provides:
- Redis (session state):  save_session / load_session helpers
- Postgres (student data): pool init, get_student, upsert_student

Both connections are initialised once during the FastAPI lifespan and exposed
as module-level globals so routes can import them without re-connecting.

Environment variables:
    REDIS_URL     — defaults to redis://localhost:6379/0
    DATABASE_URL  — defaults to postgresql://localhost/teacher_ji
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level connection handles (set during lifespan startup)
# ---------------------------------------------------------------------------

redis_client: aioredis.Redis | None = None
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

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


async def init_redis() -> None:
    """Create the Redis client and verify connectivity.

    Supports both local redis:// and remote rediss:// (TLS) URLs.
    Upstash and other managed Redis providers use rediss://.
    """
    global redis_client
    url = os.getenv("REDIS_URL", "redis://redis:6379")

    # rediss:// scheme means TLS automatically in redis.asyncio.
    # We pass ssl_cert_reqs=None to skip cert verification (standard for managed Redis).
    use_ssl = url.startswith("rediss://")
    kwargs = {"decode_responses": True}
    if use_ssl:
        kwargs["ssl_cert_reqs"] = None

    redis_client = aioredis.from_url(url, **kwargs)
    await redis_client.ping()
    logger.info("Redis connected (%s): %s", "TLS" if use_ssl else "plain", url)


async def close_redis() -> None:
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection closed.")


async def init_postgres() -> None:
    """Create the asyncpg connection pool and ensure the students table exists."""
    global pg_pool
    dsn = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/ncert_platform")
    # asyncpg doesn't parse sslmode from the DSN — strip it and pass ssl explicitly
    ssl: str | bool = False
    if "sslmode=require" in dsn:
        dsn = dsn.replace("?sslmode=require", "").replace("&sslmode=require", "")
        ssl = True
    pg_pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10, ssl=ssl)
    async with pg_pool.acquire() as conn:
        await conn.execute(_CREATE_STUDENTS_TABLE)
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


async def save_session(
    session_id: str,
    state: dict[str, Any],
    ttl: int = SESSION_TTL_SECONDS,
) -> None:
    """Persist session state as JSON with a TTL (default 4 h)."""
    if redis_client is None:
        raise RuntimeError("Redis client not initialised. Call init_redis() first.")
    await redis_client.setex(_session_key(session_id), ttl, json.dumps(state))


async def load_session(session_id: str) -> dict[str, Any]:
    """Load and deserialise session state from Redis.

    Raises HTTP 404 if the session does not exist or has expired.
    """
    if redis_client is None:
        raise RuntimeError("Redis client not initialised.")
    raw = await redis_client.get(_session_key(session_id))
    if raw is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or has expired.",
        )
    return json.loads(raw)


async def delete_session(session_id: str) -> None:
    """Remove a session from Redis (e.g. after profile update at session end)."""
    if redis_client:
        await redis_client.delete(_session_key(session_id))


# ---------------------------------------------------------------------------
# Postgres helpers
# ---------------------------------------------------------------------------


async def get_student(student_id: str) -> dict[str, Any] | None:
    """Return the student's profile dict, or None if not found."""
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    row = await pg_pool.fetchrow(
        "SELECT grade, profile FROM students WHERE student_id = $1",
        student_id,
    )
    if row is None:
        return None
    profile: dict[str, Any] = dict(row["profile"])
    profile["student_id"] = student_id
    profile["grade"] = row["grade"]
    return profile


async def upsert_student(
    student_id: str,
    grade: int,
    profile: dict[str, Any],
) -> None:
    """Insert or update a student record. Touches updated_at on every call."""
    if pg_pool is None:
        raise RuntimeError("Postgres pool not initialised.")
    # Remove redundant keys before storing in JSONB
    serialisable = {
        k: v for k, v in profile.items() if k not in ("student_id", "grade")
    }
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
