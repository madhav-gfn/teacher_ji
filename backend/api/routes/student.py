"""
Student profile routes.

Endpoints:
    GET  /student/{student_id}          → retrieve persistent profile from Postgres
    POST /student/{student_id}/update   → merge session results into profile, upsert
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_student_id, require_owner
from api.db import get_student, get_student_memory, upsert_student
from api.models import StudentProfile, UpdateProfileRequest

router = APIRouter(prefix="/student", tags=["student"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /student/{student_id}
# ---------------------------------------------------------------------------


@router.get("/{student_id}", response_model=StudentProfile)
async def get_student_profile(
    student_id: str,
    current_student_id: str = Depends(get_current_student_id),
) -> StudentProfile:
    """
    Retrieve a student's persistent profile from Postgres.
    Returns 404 if no record exists yet.
    """
    require_owner(student_id, current_student_id)
    row = await get_student(student_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No profile found for student '{student_id}'.",
        )

    memory = await get_student_memory(student_id)
    return StudentProfile(
        student_id=student_id,
        grade=row["grade"],
        learning_style=memory["learning_style"],
        mastery=memory["mastery"],
        confidence=memory["confidence"],
        weak_topics=memory["weak_topics"],
        revision_due=memory["revision_due"],
        quiz_history=memory["quiz_history"],
        total_sessions=memory["total_sessions"],
    )


# ---------------------------------------------------------------------------
# POST /student/{student_id}/update
# ---------------------------------------------------------------------------


@router.post("/{student_id}/update", response_model=StudentProfile)
async def update_student_profile(
    student_id: str,
    body: UpdateProfileRequest,
    current_student_id: str = Depends(get_current_student_id),
) -> StudentProfile:
    """
    Merge a completed session's results into the persistent Memory model.

    This is the coarse, end-of-session counterpart to the per-question rolling
    updates already applied by `update_mastery_from_feedback` during the quiz
    (see api/routes/quiz.py:submit_answer) — it reconciles the session's final
    mastered/weak lists into the same mastery/confidence maps and records the
    session in quiz_history.

    - mastered_topics push mastery/confidence up and clear weak_topics/revision_due.
    - weak_topics push mastery down (unless also in mastered_topics) and add to
      weak_topics/revision_due.
    - Appends a quiz_history entry, increments total_sessions, upserts to Postgres.
    """
    require_owner(student_id, current_student_id)
    subject = body.subject.strip().lower()

    # Load existing profile (type-guarded against pre-Phase-1B rows) or start fresh
    existing = await get_student(student_id)
    profile = await get_student_memory(student_id)
    if existing:
        grade: int = existing["grade"]
    else:
        # Infer grade from the session request body (UpdateProfileRequest doesn't
        # carry grade, so we'll need to look it up; use a safe default and
        # trust the Postgres record after the first session sets it properly).
        grade = 6  # placeholder — overwritten if we loaded from DB

    mastery: dict[str, float] = dict(profile.get("mastery", {}))
    confidence: dict[str, float] = dict(profile.get("confidence", {}))
    weak_topics: list[str] = list(profile.get("weak_topics", []))
    revision_due: list[str] = list(profile.get("revision_due", []))
    quiz_history: list[dict] = list(profile.get("quiz_history", []))
    total_sessions: int = profile.get("total_sessions", 0)

    mastered_set = {t.strip().lower() for t in body.mastered_topics}

    # ---- Mastered topics: push scores up, clear from weak/revision -------
    for topic in body.mastered_topics:
        concept = topic.strip().lower()
        if not concept:
            continue
        mastery[concept] = max(mastery.get(concept, 0.0), 0.9)
        confidence[concept] = max(confidence.get(concept, 0.0), 0.9)
    weak_topics = [t for t in weak_topics if t not in mastered_set]
    revision_due = [t for t in revision_due if t not in mastered_set]

    # ---- Weak topics: push scores down, flag for revision -----------------
    for topic in body.weak_topics:
        concept = topic.strip().lower()
        if not concept or concept in mastered_set:
            continue
        mastery[concept] = min(mastery.get(concept, 0.5), 0.4)
        confidence[concept] = min(confidence.get(concept, 0.5), 0.4)
        if concept not in weak_topics:
            weak_topics.append(concept)
        if concept not in revision_due:
            revision_due.append(concept)

    # ---- Quiz history entry --------------------------------------------
    quiz_history.append(
        {
            "date": body.quiz_date or date.today().isoformat(),
            "subject": subject,
            "chapter": body.chapter,
            "score": body.session_score,
        }
    )

    total_sessions += 1

    updated_profile = {
        "learning_style": profile["learning_style"],
        "mastery": mastery,
        "confidence": confidence,
        "weak_topics": weak_topics,
        "revision_due": revision_due,
        "quiz_history": quiz_history,
        "total_sessions": total_sessions,
    }

    await upsert_student(student_id, grade, updated_profile)
    logger.info(
        "Profile updated for student '%s', subject=%s, score=%.2f",
        student_id,
        subject,
        body.session_score,
    )

    return StudentProfile(
        student_id=student_id,
        grade=grade,
        learning_style=updated_profile["learning_style"],
        mastery=mastery,
        confidence=confidence,
        weak_topics=weak_topics,
        revision_due=revision_due,
        quiz_history=quiz_history,
        total_sessions=total_sessions,
    )
