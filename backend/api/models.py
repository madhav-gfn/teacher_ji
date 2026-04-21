"""
Pydantic v2 request/response models for the NCERT Learning Platform API.

All models validate input on construction. ID fields are plain strings;
numeric bounds (grade 6-8) are enforced via Pydantic constraints.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Session / Teaching
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    student_id: str = Field(..., description="Unique student identifier")
    grade: int = Field(..., ge=6, le=8, description="Student grade: 6, 7, or 8")
    subject: Literal["math", "science", "sst"] = Field(
        ..., description="Subject for this session"
    )
    chapter: str = Field(..., min_length=1, description="NCERT chapter title")
    topic: str = Field(..., min_length=1, description="Starting topic within the chapter")
    custom_topics: list[str] = Field(
        default_factory=list,
        description="Optional custom ordered topic list for this session",
    )


class TeachingResponse(BaseModel):
    session_id: str
    subject: str
    chapter: str
    topic: str
    teaching_output: dict[str, Any] = Field(
        description="Full structured response from the subject agent"
    )
    retrieved_chunks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="NCERT source chunks used for citation",
    )
    next_topics: list[str] = Field(
        default_factory=list,
        description="Remaining topics in this chapter (in order)",
    )


class NextTopicRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    completed_topic: str = Field(
        ..., min_length=1, description="Topic the student just finished"
    )


class SessionQuestionRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    question: str = Field(..., min_length=1, description="Student question about the current topic")


class ExplainDifferentlyRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    hint: str = Field(
        default="Explain this in a different way using a new example and simpler wording.",
        min_length=1,
        description="Hint that guides how the reteaching should differ",
    )


class ChapterCompleteResponse(BaseModel):
    session_id: str
    ready_for_quiz: Literal[True] = True
    chapter_summary: dict[str, Any] = Field(
        description="Summary of all topics covered in the chapter"
    )
    topics_covered: list[str] = Field(
        description="All topics completed during this session"
    )


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------


class StartQuizRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")


class QuizResponse(BaseModel):
    session_id: str
    questions: list[dict[str, Any]] = Field(
        description="List of question objects from quiz_generator"
    )
    total_questions: int


class SubmitAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Active session UUID")
    question_id: int = Field(..., ge=1, description="1-based question index")
    student_answer: str = Field(..., min_length=1, description="Student's answer text")


class FeedbackResponse(BaseModel):
    session_id: str
    question_id: int
    feedback_output: dict[str, Any] = Field(
        description="Full structured feedback from the feedback agent"
    )
    session_score_so_far: float = Field(
        ge=0.0, le=1.0, description="Rolling score: correct / answered"
    )
    questions_remaining: int = Field(ge=0, description="Questions not yet answered")


# ---------------------------------------------------------------------------
# Student Profile
# ---------------------------------------------------------------------------


class QuizHistoryEntry(BaseModel):
    date: str = Field(description="ISO-8601 date string")
    subject: str
    chapter: str
    score: float = Field(ge=0.0, le=1.0)


class StudentProfile(BaseModel):
    student_id: str
    grade: int = Field(ge=6, le=8)
    topics_mastered: dict[str, list[str]] = Field(
        default_factory=dict,
        description="subject → list of mastered topic strings",
    )
    weak_topics: dict[str, list[str]] = Field(
        default_factory=dict,
        description="subject → list of weak topic strings",
    )
    quiz_history: list[QuizHistoryEntry] = Field(default_factory=list)
    total_sessions: int = Field(default=0, ge=0)


class UpdateProfileRequest(BaseModel):
    """Payload for POST /student/{student_id}/update at session end."""

    session_id: str
    subject: str
    chapter: str
    session_score: float = Field(ge=0.0, le=1.0)
    mastered_topics: list[str] = Field(default_factory=list)
    weak_topics: list[str] = Field(default_factory=list)
    quiz_date: str = Field(description="ISO-8601 date, e.g. '2026-04-21'")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    redis: str
    postgres: str
