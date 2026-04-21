from __future__ import annotations

import json
import os
import time

from groq import APIStatusError, Groq, RateLimitError
from rag.retriever import retrieve

from .prompts import (
    MATH_AGENT_PROMPT,
    SCIENCE_AGENT_PROMPT,
    SST_AGENT_PROMPT,
    render_prompt,
)
from .state import LearningState

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def call_groq_with_retry(client, model, system_prompt, user_message, max_attempts=3):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    for attempt in range(1, max_attempts + 1):
        raw = ""
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except (RateLimitError, APIStatusError) as e:
            print(f"Retry {attempt}/{max_attempts}: API error - {e}")
            if attempt < max_attempts:
                time.sleep(2)
        except json.JSONDecodeError:
            print(f"Retry {attempt}/{max_attempts}: JSON parse failed")
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": "Return ONLY valid JSON. No markdown, no explanation.",
                }
            )
    raise RuntimeError("Agent failed after 3 attempts")


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No NCERT context retrieved."

    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        chapter_num = chunk.get("chapter_num") or "?"
        chapter_title = chunk.get("chapter_title") or "Unknown chapter"
        page_start = chunk.get("page_start") or "?"
        text = str(chunk.get("text", "")).strip()
        lines.append(
            f"[Chunk {index}] Chapter {chapter_num}: {chapter_title} | Page {page_start}\n{text}"
        )
    return "\n\n".join(lines)


def _last_user_request(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [str(part.get("text", "")).strip() for part in content if isinstance(part, dict)]
            joined = " ".join(part for part in parts if part)
            if joined:
                return joined
    return ""


def _build_user_message(state: LearningState) -> str:
    user_request = _last_user_request(state.get("messages", []))
    if not user_request:
        user_request = (
            f"Teach the topic '{state.get('topic', '')}' from chapter '{state.get('chapter', '')}'."
        )
    return (
        f"Student request: {user_request}\n"
        f"Focus on chapter '{state.get('chapter', '')}' and topic '{state.get('topic', '')}'."
    )


def _retrieval_query(state: LearningState) -> str:
    topic = str(state.get("topic", "")).strip()
    user_request = _last_user_request(state.get("messages", []))
    if not user_request:
        return topic
    return f"{topic}. {user_request}"


def _run_subject_agent(state: LearningState, prompt_template: str, agent_name: str) -> LearningState:
    retrieved_context = retrieve(
        _retrieval_query(state),
        state["subject"],
        state["grade"],
        state["chapter"],
        top_k=5,
    )
    context = _format_context(retrieved_context)
    system_prompt = render_prompt(
        prompt_template,
        grade=state["grade"],
        context=context,
        chapter=state["chapter"],
        topic=state["topic"],
    )
    teaching_output = call_groq_with_retry(
        client,
        "llama-3.3-70b-versatile",
        system_prompt,
        _build_user_message(state),
    )

    messages = list(state.get("messages", []))
    messages.append(
        {
            "role": "assistant",
            "name": agent_name,
            "content": teaching_output,
        }
    )
    return {
        "retrieved_context": retrieved_context,
        "teaching_output": teaching_output,
        "messages": messages,
    }


def math_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, MATH_AGENT_PROMPT, "math_agent")


def science_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, SCIENCE_AGENT_PROMPT, "science_agent")


def sst_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, SST_AGENT_PROMPT, "sst_agent")
