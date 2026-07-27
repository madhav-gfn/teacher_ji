"""
Quiz routes — quiz generation and per-answer feedback.

Endpoints:
    POST /quiz/start          → generates all questions for the chapter
    POST /quiz/submit-answer  → evaluates one answer, returns feedback
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from agents.graph import run_session
from agents.state import LearningState
from api.auth import get_current_student_id, require_owner
from api.db import load_session, save_session, update_mastery_from_feedback
from api.models import (
    FeedbackResponse,
    QuizResponse,
    StartQuizRequest,
    SubmitAnswerRequest,
)

router = APIRouter(prefix="/quiz", tags=["quiz"])
logger = logging.getLogger(__name__)

_JSON_RETRY_MESSAGE = (
    "Your previous response was not valid JSON. "
    "Return ONLY the JSON object, nothing else."
)


# ---------------------------------------------------------------------------
# Agent invocation helpers (shared pattern with session.py)
# ---------------------------------------------------------------------------


def _append_retry_message(state: LearningState) -> LearningState:
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": _JSON_RETRY_MESSAGE})
    return {**state, "messages": messages}


async def _invoke_graph(state: LearningState) -> dict[str, Any]:
    """Run the Supervisor-led LangGraph (agents/graph.py) in a thread pool for
    one turn, with a JSON-error retry."""
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


# ---------------------------------------------------------------------------
# POST /quiz/start
# ---------------------------------------------------------------------------


@router.post("/start", response_model=QuizResponse)
async def start_quiz(
    body: StartQuizRequest,
    current_student_id: str = Depends(get_current_student_id),
) -> QuizResponse:
    """
    Generate quiz questions for the current chapter.

    Uses the session's accumulated retrieved_context and weak_topics.
    Sets mode='quiz', resets question index, stores all questions in state.
    The frontend pages through questions client-side; each answer is submitted
    individually via /quiz/submit-answer.
    """
    state = await load_session(body.session_id)
    require_owner(state["student_id"], current_student_id)

    state["mode"] = "quiz"
    state["current_question_index"] = 0
    state["student_answer"] = ""
    state["feedback_output"] = {}

    state = await _invoke_graph(state)

    questions: list[dict] = state.get("quiz_questions", [])
    if not questions:
        raise HTTPException(
            status_code=500,
            detail="Quiz generator returned no questions. Please try again.",
        )

    await save_session(body.session_id, state)

    return QuizResponse(
        session_id=body.session_id,
        questions=questions,
        total_questions=len(questions),
    )


# ---------------------------------------------------------------------------
# POST /quiz/submit-answer
# ---------------------------------------------------------------------------


@router.post("/submit-answer", response_model=FeedbackResponse)
async def submit_answer(
    body: SubmitAnswerRequest,
    current_student_id: str = Depends(get_current_student_id),
) -> FeedbackResponse:
    """
    Evaluate a student's answer for a specific question.

    - question_id is 1-based (matches the question_id field in QuizResponse).
    - Sets current_question_index to question_id - 1 before invoking the agent.
    - Updates weak_topics based on concept_strength verdict:
        'mastered'       → remove from weak_topics
        'needs_revision' or 'developing' → keep or add to weak_topics
    - Updates session_score (rolling: correct / answered).
    """
    state = await load_session(body.session_id)
    require_owner(state["student_id"], current_student_id)

    questions: list[dict] = state.get("quiz_questions", [])
    if not questions:
        raise HTTPException(
            status_code=400,
            detail="No quiz questions found for this session. Call /quiz/start first.",
        )

    question_index = body.question_id - 1  # convert to 0-based
    if question_index < 0 or question_index >= len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"question_id {body.question_id} is out of range (1–{len(questions)}).",
        )

    state["student_answer"] = body.student_answer
    state["current_question_index"] = question_index
    state["mode"] = "feedback"

    state = await _invoke_graph(state)

    # ---- Weak-topic bookkeeping ----------------------------------------
    # feedback_agent already appends new weak topics; here we remove mastered ones.
    feedback_out: dict = state.get("feedback_output", {})
    answered_question = questions[question_index]
    concept_tested: str = str(answered_question.get("concept_tested", "")).strip()
    concept_strength: str = feedback_out.get("concept_strength", "")
    is_correct: bool = bool(feedback_out.get("is_correct", False))

    weak_topics: list[str] = list(state.get("weak_topics", []))
    if concept_tested and concept_strength == "mastered":
        weak_topics = [t for t in weak_topics if t.strip().lower() != concept_tested.lower()]
        state["weak_topics"] = weak_topics

    # Phase 1B Memory Agent: roll this answer's outcome into the student's
    # persistent mastery/confidence model — computed after every feedback_agent
    # call, not just at session end — and refresh the session's in-memory copy
    # so the next Supervisor/Learning Agent turn in this session sees it.
    if concept_tested:
        state["student_memory"] = await update_mastery_from_feedback(
            state["student_id"],
            state["grade"],
            concept_tested,
            is_correct,
            concept_strength,
        )

    # Restore to quiz mode so the Supervisor sees a consistent state on the next turn
    state["mode"] = "quiz"

    await save_session(body.session_id, state)

    # questions_remaining = total questions not yet answered
    answered_count = sum(1 for q in state.get("quiz_questions", []) if q.get("evaluation"))
    questions_remaining = len(state.get("quiz_questions", [])) - answered_count

    return FeedbackResponse(
        session_id=body.session_id,
        question_id=body.question_id,
        feedback_output=feedback_out,
        session_score_so_far=float(state.get("session_score", 0.0)),
        questions_remaining=max(questions_remaining, 0),
    )
