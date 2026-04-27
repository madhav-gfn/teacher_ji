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
    json_instruction = (
        "Return ONLY one syntactically valid JSON object. "
        "Use double-quoted JSON strings, arrays, booleans, and null only. "
        "Do not use markdown, bold syntax, comments, numbered text outside strings, or trailing commas."
    )
    messages = [
        {"role": "system", "content": f"{system_prompt}\n\n{json_instruction}"},
        {"role": "user", "content": user_message},
    ]
    for attempt in range(1, max_attempts + 1):
        raw = ""
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except (RateLimitError, APIStatusError) as e:
            print(f"Retry {attempt}/{max_attempts}: API error - {e}")
            if attempt < max_attempts:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The previous generation was rejected because it was not valid JSON. "
                            "Return the same content as strict JSON only. Put all prose inside quoted string values."
                        ),
                    }
                )
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


def _no_context_output(subject: str, chapter: str, topic: str) -> dict:
    message = (
        f"No NCERT context was found for topic '{topic}' in chapter '{chapter}'. "
        "Please choose a chapter/topic that exists in the ingested textbook index."
    )
    if subject == "math":
        return {
            "headline": "NCERT context not found",
            "explanation": message,
            "ncert_example": "No NCERT example is available because retrieval returned no matching textbook chunk.",
            "analogy": "It is like opening the wrong chapter in a textbook: the answer cannot be grounded until the correct page is found.",
            "common_mistake": "A common mistake is using a chapter name from a different textbook edition.",
            "guiding_question": "Which exact chapter title appears in the textbook index for this topic?",
            "topics_covered": [],
        }
    if subject == "science":
        return {
            "headline": "NCERT context not found",
            "explanation": message,
            "real_world_example": "No example is available because retrieval returned no matching textbook chunk.",
            "analogy": "It is like trying to observe an experiment without the required material.",
            "diagram_description": "No diagram can be grounded without a matching NCERT passage.",
            "guiding_question": "Which exact chapter title appears in the textbook index for this topic?",
            "topics_covered": [],
        }
    return {
        "headline": "NCERT context not found",
        "story": message,
        "key_facts": [
            "No matching NCERT context was retrieved.",
            "The requested chapter may not match the ingested textbook edition.",
            "The answer was not generated to avoid unsupported content.",
            "Use a chapter title present in the current index.",
            "Rebuild or update the index if the textbook source changes.",
        ],
        "mnemonic": "MATCH: Match Asked Topic to Current Handbook.",
        "timeline": [],
        "connection_to_present": "Textbook editions change, so digital learning tools must use the same chapter names as the indexed book.",
        "guiding_question": "Which exact chapter title appears in the textbook index for this topic?",
        "topics_covered": [],
    }


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
    if not retrieved_context:
        fallback_query = (
            f"{state.get('chapter', '')}. {state.get('topic', '')}. "
            f"{_retrieval_query(state)}"
        )
        retrieved_context = retrieve(
            fallback_query,
            state["subject"],
            state["grade"],
            chapter=None,
            top_k=5,
        )

    context = _format_context(retrieved_context)
    if not retrieved_context:
        teaching_output = _no_context_output(
            state["subject"],
            state.get("chapter", ""),
            state.get("topic", ""),
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
