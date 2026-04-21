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

from fastapi import APIRouter, HTTPException

from agents.quiz_agent import feedback_agent, quiz_generator
from agents.state import LearningState
from api.db import load_session, save_session
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


async def _invoke_agent(agent_fn, state: LearningState) -> dict[str, Any]:
    """Run a synchronous agent in a thread pool with a JSON-error retry."""
    try:
        return await asyncio.to_thread(agent_fn, state)
    except (json.JSONDecodeError, KeyError, ValueError) as first_err:
        logger.warning("Agent %s first attempt failed: %s", agent_fn.__name__, first_err)
        retry_state = _append_retry_message(state)
        try:
            return await asyncio.to_thread(agent_fn, retry_state)
        except Exception as second_err:
            logger.error("Agent %s retry failed: %s", agent_fn.__name__, second_err)
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


# ---------------------------------------------------------------------------
# POST /quiz/start
# ---------------------------------------------------------------------------


@router.post("/start", response_model=QuizResponse)
async def start_quiz(body: StartQuizRequest) -> QuizResponse:
    """
    Generate quiz questions for the current chapter.

    Uses the session's accumulated retrieved_context and weak_topics.
    Sets mode='quiz', resets question index, stores all questions in state.
    The frontend pages through questions client-side; each answer is submitted
    individually via /quiz/submit-answer.
    """
    state = await load_session(body.session_id)

    state["mode"] = "quiz"
    state["current_question_index"] = 0
    state["student_answer"] = ""
    state["feedback_output"] = {}

    updates = await _invoke_agent(quiz_generator, state)
    state = {**state, **updates}

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
async def submit_answer(body: SubmitAnswerRequest) -> FeedbackResponse:
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

    updates = await _invoke_agent(feedback_agent, state)
    state = {**state, **updates}

    # ---- Weak-topic bookkeeping ----------------------------------------
    # feedback_agent already appends new weak topics; here we remove mastered ones.
    feedback_out: dict = state.get("feedback_output", {})
    answered_question = questions[question_index]
    concept_tested: str = str(answered_question.get("concept_tested", "")).strip()
    concept_strength: str = feedback_out.get("concept_strength", "")

    weak_topics: list[str] = list(state.get("weak_topics", []))
    if concept_tested and concept_strength == "mastered":
        weak_topics = [t for t in weak_topics if t.strip().lower() != concept_tested.lower()]
        state["weak_topics"] = weak_topics

    # Restore to quiz mode so orchestrator is consistent if graph is invoked later
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
