"""
Student profile routes.

Endpoints:
    GET  /student/{student_id}          → retrieve persistent profile from Postgres
    POST /student/{student_id}/update   → merge session results into profile, upsert
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, HTTPException

from api.db import get_student, upsert_student
from api.models import StudentProfile, UpdateProfileRequest

router = APIRouter(prefix="/student", tags=["student"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /student/{student_id}
# ---------------------------------------------------------------------------


@router.get("/{student_id}", response_model=StudentProfile)
async def get_student_profile(student_id: str) -> StudentProfile:
    """
    Retrieve a student's persistent profile from Postgres.
    Returns 404 if no record exists yet.
    """
    row = await get_student(student_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No profile found for student '{student_id}'.",
        )

    return StudentProfile(
        student_id=row["student_id"],
        grade=row["grade"],
        topics_mastered=row.get("topics_mastered", {}),
        weak_topics=row.get("weak_topics", {}),
        quiz_history=row.get("quiz_history", []),
        total_sessions=row.get("total_sessions", 0),
    )


# ---------------------------------------------------------------------------
# POST /student/{student_id}/update
# ---------------------------------------------------------------------------


@router.post("/{student_id}/update", response_model=StudentProfile)
async def update_student_profile(
    student_id: str,
    body: UpdateProfileRequest,
) -> StudentProfile:
    """
    Merge a completed session's results into the persistent student profile.

    - Adds mastered_topics to profile['topics_mastered'][subject] (deduped).
    - Merges weak_topics into profile['weak_topics'][subject] (deduped).
      Topics that appear in mastered_topics are removed from weak_topics.
    - Appends a quiz_history entry.
    - Increments total_sessions.
    - Upserts to Postgres.
    """
    subject = body.subject.strip().lower()

    # Load existing profile or start fresh
    existing = await get_student(student_id)
    if existing:
        profile: dict = dict(existing)
        grade: int = existing["grade"]
    else:
        profile = {
            "topics_mastered": {},
            "weak_topics": {},
            "quiz_history": [],
            "total_sessions": 0,
        }
        # Infer grade from the session request body (UpdateProfileRequest doesn't
        # carry grade, so we'll need to look it up; use a safe default and
        # trust the Postgres record after the first session sets it properly).
        grade = 6  # placeholder — overwritten if we loaded from DB

    topics_mastered: dict[str, list[str]] = profile.get("topics_mastered", {})
    weak_topics_map: dict[str, list[str]] = profile.get("weak_topics", {})
    quiz_history: list[dict] = profile.get("quiz_history", [])
    total_sessions: int = profile.get("total_sessions", 0)

    # ---- Merge mastered topics ------------------------------------------
    current_mastered: list[str] = topics_mastered.get(subject, [])
    for topic in body.mastered_topics:
        if topic not in current_mastered:
            current_mastered.append(topic)
    topics_mastered[subject] = current_mastered

    # ---- Merge weak topics (remove newly mastered ones) -----------------
    current_weak: list[str] = weak_topics_map.get(subject, [])
    mastered_set = {t.strip().lower() for t in body.mastered_topics}
    # Add new weak topics not yet mastered
    for topic in body.weak_topics:
        if topic.strip().lower() not in mastered_set and topic not in current_weak:
            current_weak.append(topic)
    # Remove any topic now mastered
    current_weak = [t for t in current_weak if t.strip().lower() not in mastered_set]
    weak_topics_map[subject] = current_weak

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
        "topics_mastered": topics_mastered,
        "weak_topics": weak_topics_map,
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
        topics_mastered=topics_mastered,
        weak_topics=weak_topics_map,
        quiz_history=quiz_history,
        total_sessions=total_sessions,
    )
