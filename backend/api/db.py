from __future__ import annotations

import json
import logging
import os
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from upstash_redis.asyncio import Redis as UpstashRedis
from dotenv import load_dotenv, find_dotenv
from fastapi import HTTPException

load_dotenv(find_dotenv(usecwd=True), override=True)

logger = logging.getLogger(__name__)

redis_client: Any = None
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
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        # Some render redis instances require tls, ssl_cert_reqs="none" bypasses strictly checking certs.
        # But 'ssl_cert_reqs' has been renamed in redis 4.x/5.x to be handled slightly differently or uses "none" string instead of None type in aioredis.
        # Actually in recent redis-py 'ssl_cert_reqs' might be fine as a string "none" or it could use `ssl_cert_reqs="none"`.
        # Just use standard `from_url` without the kwarg for standard local/render standard setups,
        # or we check if "rediss" is in url to add ssl args.
        kwargs: dict[str, Any] = {"decode_responses": True}
        if redis_url.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = "none"

        redis_client = aioredis.from_url(redis_url, **kwargs)
        await redis_client.ping()
        logger.info("Standard Redis connected: %s", redis_url)
        return

    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        raise RuntimeError("Either REDIS_URL or (UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN) must be set")
    redis_client = UpstashRedis(url=url, token=token)
    await redis_client.ping()
    logger.info("Upstash Redis connected: %s", url)


async def close_redis() -> None:
    global redis_client
    if isinstance(redis_client, aioredis.Redis):
        await redis_client.aclose()
        logger.info("Standard Redis connection closed.")
    # Upstash REST client is stateless, no close method


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


# ---------------------------------------------------------------------------
# Memory model (Phase 1B) — structured, per-concept learner profile.
#
# Shape (see archie.md "Student Knowledge Model"):
#   {
#     "learning_style": "visual",
#     "mastery": {"division": 0.42, "fractions": 0.81},
#     "confidence": {"division": 0.39, "fractions": 0.84},
#     "weak_topics": ["division"],
#     "revision_due": ["fractions"],
#     "quiz_history": [...],
#     "total_sessions": 0,
#   }
#
# mastery/confidence are per-concept rolling scores in [0, 1], updated after
# every feedback_agent call (quiz correctness) and every re-explanation
# request — never only at session end.
# ---------------------------------------------------------------------------

DEFAULT_MEMORY: dict[str, Any] = {
    "learning_style": "text",
    "mastery": {},
    "confidence": {},
    "weak_topics": [],
    "revision_due": [],
    "quiz_history": [],
    "total_sessions": 0,
}

_MASTERY_ALPHA = 0.3  # EMA weight given to the newest signal
_WEAK_TOPIC_THRESHOLD = 0.5
_MASTERED_THRESHOLD = 0.75
_REVISION_DUE_THRESHOLD = 0.8

_CONCEPT_STRENGTH_SCORE = {
    "mastered": 1.0,
    "developing": 0.6,
    "needs_revision": 0.2,
}


def _normalize_concept(concept: str) -> str:
    return concept.strip().lower()


_MEMORY_FIELD_TYPES: dict[str, type] = {
    "learning_style": str,
    "mastery": dict,
    "confidence": dict,
    "weak_topics": list,
    "revision_due": list,
    "quiz_history": list,
    "total_sessions": int,
}


async def get_student_memory(student_id: str) -> dict[str, Any]:
    """Load the student's persistent Memory model, filled in with defaults for
    any field never written (new student, or a profile predating Phase 1B —
    where e.g. weak_topics was a subject-keyed dict rather than a flat list)."""
    existing = await get_student(student_id) or {}
    memory = dict(DEFAULT_MEMORY)
    for key, expected_type in _MEMORY_FIELD_TYPES.items():
        value = existing.get(key)
        if isinstance(value, expected_type):
            memory[key] = value
    return memory


def _recompute_topic_lists(memory: dict[str, Any]) -> None:
    """Derive weak_topics / revision_due from the current mastery map so they
    never drift out of sync with the scores that drove them."""
    mastery: dict[str, float] = memory["mastery"]
    weak_topics = [t for t in memory.get("weak_topics", []) if mastery.get(t, 0.0) < _MASTERED_THRESHOLD]
    for concept, score in mastery.items():
        if score < _WEAK_TOPIC_THRESHOLD and concept not in weak_topics:
            weak_topics.append(concept)
    memory["weak_topics"] = weak_topics

    revision_due = [t for t in memory.get("revision_due", []) if mastery.get(t, 0.0) < _REVISION_DUE_THRESHOLD]
    memory["revision_due"] = revision_due


async def update_mastery_from_feedback(
    student_id: str,
    grade: int,
    concept: str,
    is_correct: bool,
    concept_strength: str,
) -> dict[str, Any]:
    """Roll a quiz answer's outcome into the student's persistent mastery/confidence
    for `concept`, using an exponential moving average so recent performance
    dominates without discarding history. Called after every feedback_agent turn."""
    concept = _normalize_concept(concept)
    if not concept:
        return await get_student_memory(student_id)

    memory = await get_student_memory(student_id)
    mastery: dict[str, float] = dict(memory["mastery"])
    confidence: dict[str, float] = dict(memory["confidence"])

    correctness_signal = 1.0 if is_correct else 0.0
    prior_mastery = float(mastery.get(concept, 0.5))
    mastery[concept] = round(prior_mastery * (1 - _MASTERY_ALPHA) + correctness_signal * _MASTERY_ALPHA, 4)

    strength_signal = _CONCEPT_STRENGTH_SCORE.get(concept_strength, 0.5)
    prior_confidence = float(confidence.get(concept, 0.5))
    confidence[concept] = round(prior_confidence * (1 - _MASTERY_ALPHA) + strength_signal * _MASTERY_ALPHA, 4)

    memory["mastery"] = mastery
    memory["confidence"] = confidence
    if concept_strength == "needs_revision" and concept not in memory["revision_due"]:
        memory["revision_due"].append(concept)
    _recompute_topic_lists(memory)

    await upsert_student(student_id, grade, memory)
    return memory


async def apply_reexplanation_signal(student_id: str, grade: int, topic: str) -> dict[str, Any]:
    """A student asking for the same topic to be re-explained is itself a weak-
    understanding signal, independent of any quiz answer — nudge mastery/confidence
    down and flag the topic for revision."""
    concept = _normalize_concept(topic)
    if not concept:
        return await get_student_memory(student_id)

    memory = await get_student_memory(student_id)
    mastery: dict[str, float] = dict(memory["mastery"])
    confidence: dict[str, float] = dict(memory["confidence"])

    prior_mastery = float(mastery.get(concept, 0.5))
    mastery[concept] = round(prior_mastery * (1 - _MASTERY_ALPHA) + 0.3 * _MASTERY_ALPHA, 4)
    prior_confidence = float(confidence.get(concept, 0.5))
    confidence[concept] = round(prior_confidence * (1 - _MASTERY_ALPHA) + 0.3 * _MASTERY_ALPHA, 4)

    memory["mastery"] = mastery
    memory["confidence"] = confidence
    if concept not in memory["revision_due"]:
        memory["revision_due"].append(concept)
    _recompute_topic_lists(memory)

    await upsert_student(student_id, grade, memory)
    return memory


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
