from __future__ import annotations

from .state import LearningState

ORCHESTRATOR_ROUTES = {
    "math": "math_agent",
    "science": "science_agent",
    "sst": "sst_agent",
    "quiz": "quiz_generator",
    "feedback": "feedback_agent",
}


def _normalize_subject(subject: str | None) -> str:
    return (subject or "").strip().lower()


def _all_questions_answered(state: LearningState) -> bool:
    questions = state.get("quiz_questions", [])
    current_index = int(state.get("current_question_index", 0))
    return bool(questions) and current_index >= len(questions)


def orchestrator_node(state: LearningState) -> LearningState:
    if (
        state.get("mode") == "quiz"
        and _all_questions_answered(state)
        and float(state.get("session_score", 0.0)) >= 0.8
    ):
        return {"mode": "complete"}
    return {}


def route_from_orchestrator(state: LearningState) -> str:
    mode = state.get("mode", "teaching")
    session_score = float(state.get("session_score", 0.0))

    if mode == "complete":
        return "complete"

    if mode == "quiz" and _all_questions_answered(state):
        if session_score >= 0.8:
            return "complete"
        return "quiz"

    if mode == "teaching" and state.get("teaching_output"):
        return "complete"

    if mode == "quiz" and state.get("quiz_questions"):
        return "complete"

    if mode == "feedback" and state.get("student_answer"):
        return "feedback"

    if mode == "feedback" and state.get("feedback_output"):
        return "complete"

    if mode == "teaching":
        subject = _normalize_subject(state.get("subject"))
        if subject not in ORCHESTRATOR_ROUTES:
            raise ValueError(f"Unsupported subject for teaching mode: {state.get('subject')!r}")
        return subject

    if mode == "quiz":
        return "quiz"

    if mode == "feedback":
        return "feedback"

    raise ValueError(f"Unsupported mode: {mode!r}")
