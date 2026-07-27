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

from fastapi import APIRouter, Depends, HTTPException

from agents.graph import run_session
from agents.state import LearningState
from api.auth import get_current_student_id, require_owner
from api.curriculum import get_chapter_topics
from api.db import apply_reexplanation_signal, get_document, get_student_memory, load_session, save_session
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

_JSON_RETRY_MESSAGE = (
    "Your previous response was not valid JSON. "
    "Return ONLY the JSON object, nothing else."
)


# ---------------------------------------------------------------------------
# Graph invocation helpers
# ---------------------------------------------------------------------------


def _append_retry_message(state: LearningState) -> LearningState:
    """Return a copy of state with the JSON-retry nudge appended to messages."""
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": _JSON_RETRY_MESSAGE})
    return {**state, "messages": messages}


async def _invoke_graph(state: LearningState) -> dict[str, Any]:
    """
    Run the Supervisor-led LangGraph (agents/graph.py) in a thread pool for one turn.

    The Supervisor decides the next action and the graph dispatches to the
    matching agent node, returning the full merged LearningState. Retries once
    if the run raises a JSON-related error.
    """
    try:
        return await asyncio.to_thread(run_session, state)
    except (json.JSONDecodeError, KeyError, ValueError) as first_err:
        logger.warning("Graph run first attempt failed: %s", first_err)
        retry_state = _append_retry_message(state)
        try:
            return await asyncio.to_thread(run_session, retry_state)
        except Exception as second_err:
            logger.error("Graph run failed after retry: %s", second_err)
            raise HTTPException(
                status_code=500,
                detail="Agent failed to generate valid response. Please try again.",
            )
    except Exception as err:
        logger.error("Graph run unexpected error: %s", err)
        raise HTTPException(
            status_code=500,
            detail="Agent failed to generate valid response. Please try again.",
        )


def _response_subject(state: dict[str, Any]) -> str:
    """The subject string returned to the frontend — "custom" for uploaded
    material (frontend routes on this), otherwise the real NCERT subject."""
    if state.get("document_id"):
        return "custom"
    return state["subject"]


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


def _was_redirected_to_prerequisite(state: dict[str, Any], requested_topic: str) -> bool:
    """Whether the Supervisor (agents/supervisor.py) redirected this turn to
    teach a prerequisite refresher instead of the requested topic.

    Can't check state["next_action"] for this - by the time the graph
    finishes, the Supervisor's second (post-teaching) visit has already
    overwritten it to "complete" as the turn's terminal action, same as a
    normal "teach" turn. target_topic diverging from the requested topic is
    the only signal that survives to the end of the invocation.
    """
    target_topic = str(state.get("target_topic") or "").strip().lower()
    return bool(target_topic) and target_topic != requested_topic.strip().lower()


def _actually_taught_topic(state: dict[str, Any], requested_topic: str) -> str:
    """What was actually taught this turn - the prerequisite if redirected,
    otherwise the requested topic. Surfacing this (not always the requested
    topic) keeps the response from being mislabeled after a redirect."""
    if _was_redirected_to_prerequisite(state, requested_topic):
        return str(state["target_topic"])
    return requested_topic


def _covered_topics_for_state(
    state: dict[str, Any], requested_topic: str, already_covered: list[str]
) -> list[str]:
    """Topics to treat as done for next-topic progression. Excludes
    requested_topic when this turn was redirected to a prerequisite refresher
    instead, so the student is still taught the real topic on the next call
    rather than having it silently skipped."""
    if _was_redirected_to_prerequisite(state, requested_topic):
        return list(already_covered)
    return [*already_covered, requested_topic]


async def _reteach_current_topic(
    session_id: str,
    state: dict[str, Any],
    *,
    user_message: str,
    is_reexplanation_request: bool = False,
) -> TeachingResponse:
    reteach_state = _append_user_message(state, user_message)
    reteach_state["mode"] = "teaching"
    reteach_state["teaching_output"] = {}

    if is_reexplanation_request:
        updated_memory = await apply_reexplanation_signal(
            reteach_state["student_id"],
            reteach_state["grade"],
            reteach_state["topic"],
        )
        reteach_state["student_memory"] = updated_memory

    reteach_state = await _invoke_graph(reteach_state)

    await save_session(session_id, reteach_state)

    return TeachingResponse(
        session_id=session_id,
        subject=_response_subject(reteach_state),
        chapter=reteach_state["chapter"],
        topic=_actually_taught_topic(reteach_state, reteach_state["topic"]),
        teaching_output=reteach_state.get("teaching_output", {}),
        retrieved_chunks=reteach_state.get("retrieved_context", []),
        next_topics=_remaining_topics_from_state(
            reteach_state,
            _covered_topics_for_state(
                reteach_state, reteach_state["topic"], list(reteach_state.get("topics_covered", []))
            ),
        ),
    )


# ---------------------------------------------------------------------------
# POST /session/start
# ---------------------------------------------------------------------------


@router.post("/start", response_model=TeachingResponse)
async def start_session(
    body: StartSessionRequest,
    current_student_id: str = Depends(get_current_student_id),
) -> TeachingResponse:
    """
    Create a new learning session.

    Two mutually exclusive session sources (enforced by StartSessionRequest):
    - NCERT: subject + grade + chapter → topic list from NCERT_CURRICULUM,
      taught by the matching subject agent.
    - Uploaded material: document_id → topic list generated at upload time
      (agents/document_agent.py:extract_topics), taught by document_tutor.

    1. Generates a UUID session_id.
    2. Resolves the topic list and teaching agent for the chosen source.
    3. Builds the initial LearningState and runs the agent for topic #1.
    4. Stores state in Redis (TTL 4 h).
    5. Returns TeachingResponse with the agent output and remaining topics.
    """
    session_id = str(uuid.uuid4())

    if body.document_id:
        document = await get_document(body.document_id)
        if document is None:
            raise HTTPException(status_code=404, detail=f"Document '{body.document_id}' not found.")

        response_subject = "custom"
        state_subject = "the uploaded material"
        chapter = document["title"]
        all_topics = list(body.custom_topics) or list(document["topics"])
        grade = body.grade or 8
    else:
        response_subject = body.subject
        state_subject = body.subject
        chapter = body.chapter
        all_topics = list(body.custom_topics) or get_chapter_topics(body.subject, body.grade, body.chapter)
        grade = body.grade

        if not all_topics:
            logger.warning(
                "Chapter '%s' not found in curriculum for %s class%s. Proceeding without topic list.",
                body.chapter,
                body.subject,
                body.grade,
            )

    # Use provided topic if it's valid, otherwise default to the first known topic
    topic = body.topic if body.topic else (all_topics[0] if all_topics else "Introduction")
    if topic not in all_topics:
        all_topics = [topic, *all_topics]

    # Phase 1B Memory Agent: load the student's persistent learning profile once
    # per session and carry it in state so every Supervisor/Learning Agent turn
    # for this session sees it (see agents/supervisor.py, agents/subject_agents.py).
    student_memory = await get_student_memory(current_student_id)

    initial_state: LearningState = {
        "student_id": current_student_id,
        "grade": grade,
        "subject": state_subject,
        "chapter": chapter,
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
        "document_id": body.document_id or "",
        "student_memory": student_memory,
    }

    state = await _invoke_graph(initial_state)

    await save_session(session_id, state)

    remaining = _remaining_topics_from_state(state, _covered_topics_for_state(state, topic, []))

    return TeachingResponse(
        session_id=session_id,
        subject=response_subject,
        chapter=chapter,
        topic=_actually_taught_topic(state, topic),
        teaching_output=state.get("teaching_output", {}),
        retrieved_chunks=state.get("retrieved_context", []),
        next_topics=remaining,
    )


# ---------------------------------------------------------------------------
# POST /session/next-topic
# ---------------------------------------------------------------------------


@router.post("/next-topic")
async def next_topic(
    body: NextTopicRequest,
    current_student_id: str = Depends(get_current_student_id),
):
    """
    Advance the session to the next topic in the chapter.

    - Marks completed_topic in the session state.
    - If more topics remain → invokes subject agent → returns TeachingResponse.
    - If chapter is complete → returns ChapterCompleteResponse (ready_for_quiz=true).
    """
    state = await load_session(body.session_id)
    require_owner(state["student_id"], current_student_id)

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

    state = await _invoke_graph(state)

    await save_session(body.session_id, state)

    still_remaining = _remaining_topics_from_state(
        state, _covered_topics_for_state(state, next_t, topics_covered)
    )

    return TeachingResponse(
        session_id=body.session_id,
        subject=_response_subject(state),
        chapter=chapter,
        topic=_actually_taught_topic(state, next_t),
        teaching_output=state.get("teaching_output", {}),
        retrieved_chunks=state.get("retrieved_context", []),
        next_topics=still_remaining,
    )


@router.post("/question", response_model=TeachingResponse)
async def ask_topic_question(
    body: SessionQuestionRequest,
    current_student_id: str = Depends(get_current_student_id),
) -> TeachingResponse:
    state = await load_session(body.session_id)
    require_owner(state["student_id"], current_student_id)
    return await _reteach_current_topic(
        body.session_id,
        state,
        user_message=(
            f"The student asks: {body.question}\n"
            "Answer this directly while staying on the same topic and grade level."
        ),
    )


@router.post("/explain-differently", response_model=TeachingResponse)
async def explain_differently(
    body: ExplainDifferentlyRequest,
    current_student_id: str = Depends(get_current_student_id),
) -> TeachingResponse:
    state = await load_session(body.session_id)
    require_owner(state["student_id"], current_student_id)
    return await _reteach_current_topic(
        body.session_id,
        state,
        user_message=(
            "Re-explain the same topic in a different way.\n"
            f"Student guidance: {body.hint}"
        ),
        is_reexplanation_request=True,
    )
