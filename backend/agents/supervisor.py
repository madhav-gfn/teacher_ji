from __future__ import annotations

import json
import os

from groq import Groq

from .prompts import SUPERVISOR_PROMPT, render_prompt
from .state import LearningState
from .subject_agents import call_groq_with_retry

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SUPERVISOR_MODEL = "llama-3.1-8b-instant"

_VALID_ACTIONS = {"teach", "quiz", "feedback", "complete"}

_SUBJECT_NODES = {
    "math": "math_agent",
    "science": "science_agent",
    "sst": "sst_agent",
}

_FALLBACK_ACTION_FOR_MODE = {
    "teaching": "teach",
    "quiz": "quiz",
    "feedback": "feedback",
}


def _normalize_subject(subject: str | None) -> str:
    return (subject or "").strip().lower()


def _all_questions_answered(state: LearningState) -> bool:
    questions = state.get("quiz_questions", [])
    current_index = int(state.get("current_question_index", 0))
    return bool(questions) and current_index >= len(questions)


def _deterministic_action(state: LearningState) -> tuple[str, str] | None:
    """Mechanical, non-LLM routing for turns where there is nothing to decide -
    either grading a pending answer or recognizing this turn's output already
    exists and the graph invocation should stop. Mirrors the previous
    route_from_orchestrator ordering exactly so existing session behavior is
    preserved."""
    mode = state.get("mode", "teaching")

    if mode == "complete":
        return "complete", "Session mode already marked complete."

    if mode == "feedback" and state.get("student_answer"):
        return "feedback", "A student answer is pending evaluation."

    if mode == "quiz" and _all_questions_answered(state):
        if float(state.get("session_score", 0.0)) >= 0.8:
            return "complete", "All quiz questions answered with a passing score."
        return "quiz", "Quiz completed below the mastery threshold; generating another round."

    if mode == "teaching" and state.get("teaching_output"):
        return "complete", "Teaching output already produced for this turn."

    if mode == "quiz" and state.get("quiz_questions"):
        return "complete", "Quiz already generated and awaiting student answers."

    if mode == "feedback" and state.get("feedback_output"):
        return "complete", "Feedback already produced for this turn."

    return None


def _fallback_action(state: LearningState) -> tuple[str, str]:
    mode = state.get("mode", "teaching")
    if mode in _FALLBACK_ACTION_FOR_MODE:
        return _FALLBACK_ACTION_FOR_MODE[mode], f"Deterministic fallback for mode {mode!r}."
    return "complete", f"Deterministic fallback: unrecognized mode {mode!r}."


def _state_summary(state: LearningState) -> str:
    quiz_questions = state.get("quiz_questions", [])
    summary = {
        "mode_requested": state.get("mode", "teaching"),
        "subject": state.get("subject", ""),
        "grade": state.get("grade", ""),
        "chapter": state.get("chapter", ""),
        "current_topic": state.get("topic", ""),
        "topics_covered_so_far": state.get("topics_covered", []),
        "weak_topics": state.get("weak_topics", []),
        "session_score": state.get("session_score", 0.0),
        "teaching_output_already_produced": bool(state.get("teaching_output")),
        "quiz_questions_generated": len(quiz_questions),
        "quiz_questions_answered": sum(1 for q in quiz_questions if q.get("evaluation")),
        "student_answer_pending": bool(state.get("student_answer")),
        "using_uploaded_document": bool(state.get("document_id")),
    }
    return json.dumps(summary, ensure_ascii=False)


def supervisor_node(state: LearningState) -> LearningState:
    deterministic = _deterministic_action(state)
    if deterministic is not None:
        next_action, reasoning = deterministic
        return {"next_action": next_action, "supervisor_reasoning": reasoning}

    try:
        decision = call_groq_with_retry(
            client,
            SUPERVISOR_MODEL,
            render_prompt(SUPERVISOR_PROMPT, state_summary=_state_summary(state)),
            "Decide the next action for this turn.",
        )
        next_action = str(decision.get("next_action", "")).strip()
        if next_action not in _VALID_ACTIONS:
            raise ValueError(f"Supervisor returned unsupported next_action: {next_action!r}")
    except Exception as exc:
        next_action, reasoning = _fallback_action(state)
        return {
            "next_action": next_action,
            "supervisor_reasoning": f"LLM decision unavailable ({exc}); used deterministic fallback: {reasoning}",
        }

    return {
        "next_action": next_action,
        "target_topic": str(decision.get("target_topic") or state.get("topic", "")),
        "supervisor_reasoning": str(decision.get("reasoning", "")),
    }


def route_from_supervisor(state: LearningState) -> str:
    next_action = state.get("next_action")

    if next_action == "complete":
        return "complete"

    if next_action == "teach":
        if state.get("document_id"):
            return "document_tutor"
        subject = _normalize_subject(state.get("subject"))
        if subject not in _SUBJECT_NODES:
            raise ValueError(f"Unsupported subject for teaching mode: {state.get('subject')!r}")
        return _SUBJECT_NODES[subject]

    if next_action == "quiz":
        return "quiz_generator"

    if next_action == "feedback":
        return "feedback_agent"

    raise ValueError(f"Unsupported next_action from Supervisor: {next_action!r}")
