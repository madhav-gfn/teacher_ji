"""
Session routes — teaching phase of the learning loop.

Endpoints:
    POST /session/start        → starts a new learning session, runs first topic
    POST /session/next-topic   → advances to the next topic or signals quiz-ready

Teaching logic lives here alongside session management to avoid a nearly-empty
teaching.py module. There is no route conflict: all paths are /session/*.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from agents.state import LearningState
from agents.subject_agents import math_agent, science_agent, sst_agent
from api.curriculum import get_chapter_topics
from api.db import load_session, save_session
from api.models import (
    ChapterCompleteResponse,
    ExplainDifferentlyRequest,
    NextTopicRequest,
    SessionQuestionRequest,
    StartSessionRequest,
    TeachingResponse,
)

router = APIRouter(prefix="/session", tags=["session"])
logger = logging.getLogger(__name__)

# Map subject string → agent callable
_SUBJECT_AGENTS = {
    "math": math_agent,
    "science": science_agent,
    "sst": sst_agent,
}

_JSON_RETRY_MESSAGE = (
    "Your previous response was not valid JSON. "
    "Return ONLY the JSON object, nothing else."
)


# ---------------------------------------------------------------------------
# Agent invocation helpers
# ---------------------------------------------------------------------------


def _append_retry_message(state: LearningState) -> LearningState:
    """Return a copy of state with the JSON-retry nudge appended to messages."""
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": _JSON_RETRY_MESSAGE})
    return {**state, "messages": messages}


async def _invoke_teaching_agent(
    agent_fn,
    state: LearningState,
) -> dict[str, Any]:
    """
    Run a synchronous subject agent in a thread pool.

    Retries once if the agent raises a JSON-related error.
    Raises HTTP 500 after two failures.
    """
    try:
        return await asyncio.to_thread(agent_fn, state)
    except (json.JSONDecodeError, KeyError, ValueError) as first_err:
        logger.warning("Agent %s first attempt failed: %s", agent_fn.__name__, first_err)
        retry_state = _append_retry_message(state)
        try:
            return await asyncio.to_thread(agent_fn, retry_state)
        except Exception as second_err:
            logger.error(
                "Agent %s failed after retry: %s", agent_fn.__name__, second_err
            )
            raise HTTPException(
                status_code=500,
                detail="Agent failed to generate valid response. Please try again.",
            )
    except Exception as err:
        logger.error("Agent %s unexpected error: %s", agent_fn.__name__, err)
        raise HTTPException(
            status_code=500,
            detail="Agent failed to generate valid response. Please try again.",
        )


def _topic_order_from_state(state: dict[str, Any]) -> list[str]:
    stored_topics = state.get("all_chapter_topics", [])
    if isinstance(stored_topics, list) and stored_topics:
        return [str(topic) for topic in stored_topics if str(topic).strip()]

    return get_chapter_topics(state["subject"], state["grade"], state["chapter"])


def _remaining_topics_from_state(
    state: dict[str, Any],
    completed_topics: list[str],
) -> list[str]:
    all_topics = _topic_order_from_state(state)
    done = {topic.strip().lower() for topic in completed_topics}
    return [topic for topic in all_topics if topic.strip().lower() not in done]


def _append_user_message(state: dict[str, Any], content: str) -> dict[str, Any]:
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": content})
    return {**state, "messages": messages}


async def _reteach_current_topic(
    session_id: str,
    state: dict[str, Any],
    *,
    user_message: str,
) -> TeachingResponse:
    subject = state["subject"]
    agent_fn = _SUBJECT_AGENTS.get(subject)
    if agent_fn is None:
        raise HTTPException(status_code=400, detail=f"Unsupported subject: {subject}")

    reteach_state = _append_user_message(state, user_message)
    reteach_state["mode"] = "teaching"
    reteach_state["teaching_output"] = {}

    updates = await _invoke_teaching_agent(agent_fn, reteach_state)
    reteach_state = {**reteach_state, **updates}

    await save_session(session_id, reteach_state)

    return TeachingResponse(
        session_id=session_id,
        subject=subject,
        chapter=reteach_state["chapter"],
        topic=reteach_state["topic"],
        teaching_output=reteach_state.get("teaching_output", {}),
        retrieved_chunks=reteach_state.get("retrieved_context", []),
        next_topics=_remaining_topics_from_state(
            reteach_state,
            list(reteach_state.get("topics_covered", [])) + [reteach_state["topic"]],
        ),
    )


# ---------------------------------------------------------------------------
# POST /session/start
# ---------------------------------------------------------------------------


@router.post("/start", response_model=TeachingResponse)
async def start_session(body: StartSessionRequest) -> TeachingResponse:
    """
    Create a new learning session.

    1. Generates a UUID session_id.
    2. Looks up the chapter's topic list from NCERT_CURRICULUM.
    3. Builds the initial LearningState and runs the subject agent for topic #1.
    4. Stores state in Redis (TTL 4 h).
    5. Returns TeachingResponse with the agent output and remaining topics.
    """
    session_id = str(uuid.uuid4())

    agent_fn = _SUBJECT_AGENTS.get(body.subject)
    if agent_fn is None:
        raise HTTPException(status_code=400, detail=f"Unsupported subject: {body.subject}")

    all_topics = list(body.custom_topics) or get_chapter_topics(body.subject, body.grade, body.chapter)
    if not all_topics:
        logger.warning(
            "Chapter '%s' not found in curriculum for %s class%d. Proceeding without topic list.",
            body.chapter,
            body.subject,
            body.grade,
        )

    # Use provided topic if it's valid, otherwise default to first curriculum topic
    topic = body.topic if body.topic else (all_topics[0] if all_topics else "Introduction")
    if topic not in all_topics:
        all_topics = [topic, *all_topics]

    initial_state: LearningState = {
        "student_id": body.student_id,
        "grade": body.grade,
        "subject": body.subject,
        "chapter": body.chapter,
        "topic": topic,
        "mode": "teaching",
        "retrieved_context": [],
        "teaching_output": {},
        "quiz_questions": [],
        "current_question_index": 0,
        "student_answer": "",
        "feedback_output": {},
        "session_score": 0.0,
        "weak_topics": [],
        "messages": [],
        # API-layer tracking fields (not in agents/state.py — stored in Redis only)
        "topics_covered": [],
        "all_chapter_topics": all_topics,
    }

    updates = await _invoke_teaching_agent(agent_fn, initial_state)
    state = {**initial_state, **updates}

    await save_session(session_id, state)

    remaining = _remaining_topics_from_state(state, [topic])

    return TeachingResponse(
        session_id=session_id,
        subject=body.subject,
        chapter=body.chapter,
        topic=topic,
        teaching_output=state.get("teaching_output", {}),
        retrieved_chunks=state.get("retrieved_context", []),
        next_topics=remaining,
    )


# ---------------------------------------------------------------------------
# POST /session/next-topic
# ---------------------------------------------------------------------------


@router.post("/next-topic")
async def next_topic(body: NextTopicRequest):
    """
    Advance the session to the next topic in the chapter.

    - Marks completed_topic in the session state.
    - If more topics remain → invokes subject agent → returns TeachingResponse.
    - If chapter is complete → returns ChapterCompleteResponse (ready_for_quiz=true).
    """
    state = await load_session(body.session_id)

    # Record the completed topic (deduped)
    topics_covered: list[str] = state.get("topics_covered", [])
    if body.completed_topic not in topics_covered:
        topics_covered.append(body.completed_topic)
    state["topics_covered"] = topics_covered

    subject: str = state["subject"]
    grade: int = state["grade"]
    chapter: str = state["chapter"]

    remaining = _remaining_topics_from_state(state, topics_covered)

    if not remaining:
        # Chapter complete — signal quiz
        state["mode"] = "quiz"
        await save_session(body.session_id, state)

        chapter_summary = {
            "chapter": chapter,
            "subject": subject,
            "grade": grade,
            "topics_covered": topics_covered,
            "session_score": state.get("session_score", 0.0),
            "weak_topics": state.get("weak_topics", []),
        }
        return ChapterCompleteResponse(
            session_id=body.session_id,
            chapter_summary=chapter_summary,
            topics_covered=topics_covered,
        )

    # More topics available — teach the next one
    next_t = remaining[0]
    state["topic"] = next_t
    state["mode"] = "teaching"
    state["teaching_output"] = {}
    state["retrieved_context"] = []

    agent_fn = _SUBJECT_AGENTS.get(subject)
    if agent_fn is None:
        raise HTTPException(status_code=400, detail=f"Unsupported subject: {subject}")

    updates = await _invoke_teaching_agent(agent_fn, state)
    state = {**state, **updates}

    await save_session(body.session_id, state)

    still_remaining = _remaining_topics_from_state(state, topics_covered + [next_t])

    return TeachingResponse(
        session_id=body.session_id,
        subject=subject,
        chapter=chapter,
        topic=next_t,
        teaching_output=state.get("teaching_output", {}),
        retrieved_chunks=state.get("retrieved_context", []),
        next_topics=still_remaining,
    )


@router.post("/question", response_model=TeachingResponse)
async def ask_topic_question(body: SessionQuestionRequest) -> TeachingResponse:
    state = await load_session(body.session_id)
    return await _reteach_current_topic(
        body.session_id,
        state,
        user_message=(
            f"The student asks: {body.question}\n"
            "Answer this directly while staying on the same topic and grade level."
        ),
    )


@router.post("/explain-differently", response_model=TeachingResponse)
async def explain_differently(body: ExplainDifferentlyRequest) -> TeachingResponse:
    state = await load_session(body.session_id)
    return await _reteach_current_topic(
        body.session_id,
        state,
        user_message=(
            "Re-explain the same topic in a different way.\n"
            f"Student guidance: {body.hint}"
        ),
    )
