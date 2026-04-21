"""
FastAPI application entry point for the NCERT Learning Platform.

Start the server:
    uvicorn api.main:app --reload --port 8000

All routes are registered through APIRouter instances to keep main.py
focused on wiring, not business logic.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import (
    close_postgres,
    close_redis,
    init_postgres,
    init_redis,
    pg_pool,
    redis_client,
)
from api.models import HealthResponse
from api.routes import quiz, session, student

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: startup + shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise connections on startup; cleanly close them on shutdown."""
    logger.info("Starting up NCERT Learning Platform API …")
    await init_redis()
    await init_postgres()
    logger.info("All connections ready.")
    yield
    logger.info("Shutting down …")
    await close_redis()
    await close_postgres()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = FastAPI(
    title="NCERT Learning Platform API",
    description=(
        "REST API wrapping the LangGraph multi-agent teaching system. "
        "Provides session management, teaching delivery, quiz generation, "
        "per-answer feedback, and persistent student profiles."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Create React App
        "http://localhost:5173",   # Vite
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# session.py handles both session management AND subject-agent invocation.
# quiz.py is purely /quiz/* — no overlap with session routes.
# student.py is purely /student/* — no overlap with either.

app.include_router(session.router)
app.include_router(quiz.router)
app.include_router(student.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """
    Verify both Redis and Postgres connections are alive.

    Returns:
        status='ok'       — both connections healthy
        status='degraded' — one or more connections failed
    """
    redis_status = "ok"
    postgres_status = "ok"

    # Redis ping
    try:
        from api.db import redis_client as _rc
        if _rc is None:
            redis_status = "not initialised"
        else:
            await _rc.ping()
    except Exception as exc:
        redis_status = f"error: {exc}"

    # Postgres ping
    try:
        from api.db import pg_pool as _pp
        if _pp is None:
            postgres_status = "not initialised"
        else:
            async with _pp.acquire() as conn:
                await conn.fetchval("SELECT 1")
    except Exception as exc:
        postgres_status = f"error: {exc}"

    overall = (
        "ok"
        if redis_status == "ok" and postgres_status == "ok"
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        redis=redis_status,
        postgres=postgres_status,
    )
