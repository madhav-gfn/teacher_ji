"""
Generic tutor agent for student-uploaded documents.

Unlike math_agent/science_agent/sst_agent, this agent is not tied to a fixed
subject or a hardcoded NCERT curriculum. It teaches from whatever the student
uploaded, retrieving grounded context from that document's own FAISS index
(see rag/retriever.py:retrieve_document) and emitting the generic teaching
schema defined by GENERIC_TUTOR_PROMPT.

extract_topics() runs once at upload time (see api/routes/documents.py) to
turn a freshly-ingested document into a short ordered topic list, which then
drives the same topic-by-topic teaching flow used for NCERT chapters.
"""
from __future__ import annotations

import os

from groq import Groq
from rag.retriever import retrieve_document

from .prompt_registry import render_versioned
from .state import LearningState
from .subject_agents import (
    _build_user_message,
    _format_context,
    _format_student_memory,
    _retrieval_query,
    call_groq_with_retry,
)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TOPIC_SAMPLE_CHUNKS = 12
TOPIC_SAMPLE_CHARS = 6000


def _no_context_output(chapter: str, topic: str) -> dict:
    message = (
        f"No matching content was found for topic '{topic}' in '{chapter}'. "
        "Try re-uploading the document or picking a different topic from its topic list."
    )
    return {
        "headline": "Content not found in your document",
        "explanation": message,
        "example": "No example is available because retrieval returned no matching passage.",
        "analogy": "It is like searching an index for a page that was never printed.",
        "key_points": [],
        "common_mistake": "",
        "guiding_question": "Which topic from the document's topic list would you like to try instead?",
        "topics_covered": [],
    }


def document_tutor(state: LearningState) -> LearningState:
    document_id = state.get("document_id")
    if not document_id:
        raise ValueError("document_tutor requires 'document_id' in state.")

    retrieved_context = retrieve_document(
        _retrieval_query(state),
        document_id,
        top_k=5,
    )

    if not retrieved_context:
        teaching_output = _no_context_output(state.get("chapter", ""), state.get("topic", ""))
        messages = list(state.get("messages", []))
        messages.append(
            {
                "role": "assistant",
                "name": "document_tutor",
                "content": teaching_output,
            }
        )
        return {
            "retrieved_context": retrieved_context,
            "teaching_output": teaching_output,
            "messages": messages,
        }

    context = _format_context(retrieved_context)
    system_prompt, prompt_version = render_versioned(
        "generic_tutor",
        grade=state.get("grade") or "general",
        context=context,
        chapter=state.get("chapter", ""),
        topic=state.get("topic", ""),
        student_memory=_format_student_memory(state, state.get("topic", "")),
    )
    teaching_output = call_groq_with_retry(
        client,
        "llama-3.3-70b-versatile",
        system_prompt,
        _build_user_message(state),
        prompt_name="generic_tutor",
        prompt_version=prompt_version,
    )

    messages = list(state.get("messages", []))
    messages.append(
        {
            "role": "assistant",
            "name": "document_tutor",
            "content": teaching_output,
        }
    )
    return {
        "retrieved_context": retrieved_context,
        "teaching_output": teaching_output,
        "messages": messages,
    }


def extract_topics(chunks: list[dict], filename: str) -> tuple[str, list[str]]:
    """Ask the LLM to organize freshly-ingested chunks into a title + ordered topic list.

    Raises ValueError if no topics could be extracted (caller should fall back
    to a single "Overview" topic rather than failing the whole upload).
    """
    sample_chunks = chunks[:TOPIC_SAMPLE_CHUNKS]
    sample = "\n\n".join(str(chunk.get("text", "")).strip() for chunk in sample_chunks)
    sample = sample[:TOPIC_SAMPLE_CHARS]

    system_prompt, prompt_version = render_versioned("topic_extraction", filename=filename, sample=sample)
    payload = call_groq_with_retry(
        client,
        "llama-3.3-70b-versatile",
        system_prompt,
        "Generate the title and topic list now.",
        prompt_name="topic_extraction",
        prompt_version=prompt_version,
    )

    title = str(payload.get("title") or filename).strip() or filename
    topics = [str(topic).strip() for topic in payload.get("topics", []) if str(topic).strip()]
    if not topics:
        raise ValueError("Topic extraction returned no topics.")
    return title, topics
