from __future__ import annotations

from typing import Literal, TypedDict


class LearningState(TypedDict, total=False):
    session_id: str
    student_id: str
    grade: int
    subject: str
    chapter: str
    topic: str
    mode: Literal["teaching", "quiz", "feedback", "complete"]
    retrieved_context: list[dict]
    teaching_output: dict
    quiz_questions: list[dict]
    current_question_index: int
    student_answer: str
    feedback_output: dict
    session_score: float
    weak_topics: list[str]
    messages: list[dict]
    topics_covered: list[str]
    all_chapter_topics: list[str]
