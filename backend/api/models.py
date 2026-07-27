"""
Pydantic v2 request/response models for the NCERT Learning Platform API.

All models validate input on construction. ID fields are plain strings;
numeric bounds (grade 6-8) are enforced via Pydantic constraints.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Session / Teaching
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    document_id: str | None = Field(
        default=None,
        description="Uploaded document ID — set this to study your own material "
        "instead of an NCERT chapter",
    )
    grade: int | None = Field(
        default=None, ge=6, le=8, description="Student grade: 6, 7, or 8"
    )
    subject: Literal["math", "science", "sst"] | None = Field(
        default=None, description="Subject for an NCERT session (omit when document_id is set)"
    )
    chapter: str | None = Field(
        default=None, min_length=1, description="NCERT chapter title (omit when document_id is set)"
    )
    topic: str | None = Field(
        default=None,
        min_length=1,
        description="Starting topic. Auto-selected from custom_topics / the document's "
        "topic list if omitted.",
    )
    custom_topics: list[str] = Field(
        default_factory=list,
        description="Optional custom ordered topic list for this session",
    )

    @model_validator(mode="after")
    def _check_source(self) -> "StartSessionRequest":
        if self.document_id:
            return self
        missing = [
            name
            for name, value in (("subject", self.subject), ("chapter", self.chapter), ("grade", self.grade))
            if not value
        ]
        if missing:
            raise ValueError(
                f"Missing required field(s) for an NCERT session: {', '.join(missing)}. "
                "Provide document_id instead to study your own uploaded material."
            )
        return self


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
    session_id: str = Field(..., min_length=1, description="Active session UUID")
    completed_topic: str = Field(
        ..., min_length=1, description="Topic the student just finished"
    )


class SessionQuestionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Active session UUID")
    question: str = Field(..., min_length=1, description="Student question about the current topic")


class ExplainDifferentlyRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Active session UUID")
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
    session_id: str = Field(..., min_length=1, description="Active session UUID")


class QuizResponse(BaseModel):
    session_id: str
    questions: list[dict[str, Any]] = Field(
        description="List of question objects from quiz_generator"
    )
    total_questions: int


class SubmitAnswerRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Active session UUID")
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
    """The Phase 1B Memory model — a structured, per-concept learner profile
    (see archie.md "Student Knowledge Model"), not just a session log."""

    student_id: str
    grade: int = Field(ge=6, le=8)
    learning_style: str = Field(default="text")
    mastery: dict[str, float] = Field(
        default_factory=dict,
        description="concept → rolling mastery score in [0, 1]",
    )
    confidence: dict[str, float] = Field(
        default_factory=dict,
        description="concept → rolling confidence score in [0, 1]",
    )
    weak_topics: list[str] = Field(
        default_factory=list,
        description="concepts currently below the mastery threshold",
    )
    revision_due: list[str] = Field(
        default_factory=list,
        description="concepts flagged needs_revision that haven't recovered yet",
    )
    quiz_history: list[QuizHistoryEntry] = Field(default_factory=list)
    total_sessions: int = Field(default=0, ge=0)


class UpdateProfileRequest(BaseModel):
    """Payload for POST /student/{student_id}/update at session end."""

    session_id: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    chapter: str = Field(..., min_length=1)
    session_score: float = Field(ge=0.0, le=1.0)
    mastered_topics: list[str] = Field(default_factory=list)
    weak_topics: list[str] = Field(default_factory=list)
    quiz_date: str = Field(description="ISO-8601 date, e.g. '2026-04-21'")


# ---------------------------------------------------------------------------
# Documents (student-uploaded study material)
# ---------------------------------------------------------------------------


class DocumentSummary(BaseModel):
    document_id: str
    title: str
    filename: str
    topic_count: int
    chunk_count: int
    created_at: str = Field(description="ISO-8601 timestamp string")


class DocumentDetail(DocumentSummary):
    topics: list[str] = Field(default_factory=list)


class UploadDocumentResponse(DocumentDetail):
    pass


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    redis: str
    postgres: str
