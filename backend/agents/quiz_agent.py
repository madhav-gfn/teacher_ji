from __future__ import annotations

import os

from groq import Groq
from rag.retriever import retrieve

from .prompts import FEEDBACK_AGENT_PROMPT, QUIZ_GENERATOR_PROMPT, render_prompt
from .state import LearningState
from .subject_agents import call_groq_with_retry

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MIN_CHUNK_WORDS = 20


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No NCERT context retrieved."

    useful = [c for c in chunks if len(str(c.get("text", "")).split()) >= MIN_CHUNK_WORDS]
    if not useful:
        return "No NCERT context retrieved."

    return "\n\n".join(
        (
            f"[Chunk {index}] Chapter {chunk.get('chapter_num') or '?'}: "
            f"{chunk.get('chapter_title') or 'Unknown chapter'} | "
            f"Page {chunk.get('page_start') or '?'}\n"
            f"{str(chunk.get('text', '')).strip()}"
        )
        for index, chunk in enumerate(useful, start=1)
    )


def _normalize_questions(questions: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for index, question in enumerate(questions, start=1):
        current = dict(question)
        current["question_id"] = int(current.get("question_id", index))
        current["question_type"] = "mcq"
        normalized.append(current)
    return normalized


def _difficulty_for(state: LearningState) -> str:
    score = float(state.get("session_score", 0.0))
    if score >= 0.8:
        return "hard"
    if score >= 0.4:
        return "medium"
    return "easy"


def _num_questions_for(state: LearningState) -> int:
    weak_topics = state.get("weak_topics", [])
    if weak_topics:
        return min(max(len(weak_topics), 3), 3)
    return 3


def _get_context(state: LearningState) -> list[dict]:
    context = state.get("retrieved_context", [])
    if context:
        return context
    context = retrieve(
        state["topic"],
        state["subject"],
        state["grade"],
        state.get("chapter"),
        top_k=8,
    )
    if context:
        return context
    return retrieve(
        f"{state.get('chapter', '')}. {state.get('topic', '')}",
        state["subject"],
        state["grade"],
        chapter=None,
        top_k=8,
    )


def _last_user_message(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def quiz_generator(state: LearningState) -> LearningState:
    retrieved_context = _get_context(state)
    context = _format_context(retrieved_context)
    difficulty = _difficulty_for(state)
    num_questions = _num_questions_for(state)
    system_prompt = render_prompt(
        QUIZ_GENERATOR_PROMPT,
        grade=state["grade"],
        subject=state["subject"],
        context=context,
        chapter=state["chapter"],
        weak_topics=", ".join(state.get("weak_topics", [])) or "None",
        difficulty=difficulty,
        num_questions=num_questions,
    )
    user_request = _last_user_message(state.get("messages", [])) or (
        f"Generate a quiz for chapter '{state.get('chapter', '')}' and topic '{state.get('topic', '')}'."
    )
    quiz_payload = call_groq_with_retry(
        client,
        "llama-3.3-70b-versatile",
        system_prompt,
        user_request,
    )
    quiz_questions = _normalize_questions(list(quiz_payload.get("questions", [])))

    messages = list(state.get("messages", []))
    messages.append(
        {
            "role": "assistant",
            "name": "quiz_generator",
            "content": quiz_questions,
        }
    )
    return {
        "retrieved_context": retrieved_context,
        "quiz_questions": quiz_questions,
        "current_question_index": 0,
        "student_answer": "",
        "feedback_output": {},
        "messages": messages,
    }


def feedback_agent(state: LearningState) -> LearningState:
    questions = list(state.get("quiz_questions", []))
    current_index = int(state.get("current_question_index", 0))
    if current_index >= len(questions):
        raise IndexError("current_question_index is out of range for quiz_questions.")

    current_question = dict(questions[current_index])
    system_prompt = render_prompt(
        FEEDBACK_AGENT_PROMPT,
        question=current_question.get("question", ""),
        correct_answer=current_question.get("correct_answer", ""),
        explanation=current_question.get("explanation", ""),
        student_answer=state.get("student_answer", ""),
        grade=state["grade"],
        subject=state["subject"],
    )
    feedback_output = call_groq_with_retry(
        client,
        "llama-3.3-70b-versatile",
        system_prompt,
        "Evaluate this answer.",
    )

    current_question["student_answer"] = state.get("student_answer", "")
    current_question["evaluation"] = feedback_output
    questions[current_index] = current_question

    answered_questions = [question for question in questions if question.get("evaluation")]
    correct_count = sum(
        1 for question in answered_questions if question["evaluation"].get("is_correct") is True
    )
    session_score = correct_count / len(answered_questions) if answered_questions else 0.0

    weak_topics = list(dict.fromkeys(state.get("weak_topics", [])))
    concept_tested = str(current_question.get("concept_tested", "")).strip()
    concept_strength = feedback_output.get("concept_strength")
    if concept_tested and concept_strength in {"developing", "needs_revision"}:
        weak_topics.append(concept_tested)
        weak_topics = list(dict.fromkeys(weak_topics))

    messages = list(state.get("messages", []))
    messages.append(
        {
            "role": "assistant",
            "name": "feedback_agent",
            "content": feedback_output,
        }
    )
    return {
        "quiz_questions": questions,
        "current_question_index": min(current_index + 1, len(questions)),
        "student_answer": "",
        "feedback_output": feedback_output,
        "session_score": session_score,
        "weak_topics": weak_topics,
        "mode": "quiz",
        "messages": messages,
    }
