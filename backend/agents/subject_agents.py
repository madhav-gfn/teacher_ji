from __future__ import annotations

import json
import os
import time

from groq import APIStatusError, Groq, RateLimitError

from .prompts import (
    MATH_AGENT_PROMPT,
    SCIENCE_AGENT_PROMPT,
    SST_AGENT_PROMPT,
    render_prompt,
)
from .state import LearningState
from .tools import TOOL_SPECS, execute_tool_call

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TEACHING_MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ITERATIONS = 4


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


def _format_student_memory(state: LearningState, topic: str) -> str:
    """Phase 1B: render the student's persistent Memory model (loaded once at
    session start, see api/routes/session.py) as a compact per-topic summary
    for injection into the Learning Agent's system prompt."""
    memory = state.get("student_memory") or {}
    concept = topic.strip().lower()
    mastery = memory.get("mastery", {}).get(concept)
    confidence = memory.get("confidence", {}).get(concept)
    weak_topics = {t.strip().lower() for t in memory.get("weak_topics", [])}
    revision_due = {t.strip().lower() for t in memory.get("revision_due", [])}

    flags = []
    if concept in weak_topics:
        flags.append("weak_topic")
    if concept in revision_due:
        flags.append("revision_due")

    summary = {
        "learning_style": memory.get("learning_style", "text"),
        "mastery_on_this_topic": mastery if mastery is not None else "unknown (no prior data)",
        "confidence_on_this_topic": confidence if confidence is not None else "unknown (no prior data)",
        "flags": flags or ["none"],
    }
    return json.dumps(summary, ensure_ascii=False)


def _retrieval_query(state: LearningState) -> str:
    topic = str(state.get("topic", "")).strip()
    user_request = _last_user_request(state.get("messages", []))
    if not user_request:
        return topic
    return f"{topic}. {user_request}"


def _create_completion(max_attempts: int = 3, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except (RateLimitError, APIStatusError) as exc:
            last_exc = exc
            print(f"Retry {attempt}/{max_attempts}: API error - {exc}")
            if attempt < max_attempts:
                time.sleep(2)
    raise last_exc


def _assistant_tool_call_message(message, tool_calls) -> dict:
    return {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in tool_calls
        ],
    }


def _dedupe_chunks(chunks: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for chunk in chunks:
        key = (chunk.get("chapter_title"), chunk.get("page_start"), chunk.get("text"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def _finalize_json(conversation: list[dict], model: str, max_attempts: int = 3) -> dict:
    """Force a final JSON answer once tool use is done - used both to close out
    the loop normally and to repair a non-JSON final message."""
    for attempt in range(1, max_attempts + 1):
        response = _create_completion(
            model=model,
            messages=conversation,
            temperature=0.1,
            tools=TOOL_SPECS,
            tool_choice="none",
        )
        raw = response.choices[0].message.content or ""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"Retry {attempt}/{max_attempts}: JSON parse failed")
            conversation.append({"role": "assistant", "content": raw})
            conversation.append(
                {
                    "role": "user",
                    "content": "That was not valid JSON. Return ONLY one valid JSON object now. No markdown, no tool calls, no extra text.",
                }
            )
    raise RuntimeError("Agent failed to produce valid JSON after tool use.")


def _run_subject_agent(state: LearningState, prompt_template: str, agent_name: str) -> LearningState:
    subject = state["subject"]
    grade = state["grade"]
    chapter = state.get("chapter", "")
    topic = state.get("topic", "")

    system_prompt = render_prompt(
        prompt_template,
        grade=grade,
        chapter=chapter,
        topic=topic,
        student_memory=_format_student_memory(state, topic),
    )
    conversation: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _build_user_message(state)},
    ]

    reflection = state.get("teaching_reflection") or {}
    if reflection.get("critique"):
        conversation.append(
            {
                "role": "user",
                "content": (
                    "Your previous answer failed a pedagogical review. Critique: "
                    f"{reflection['critique']}\n"
                    "Revise your answer to address this critique. Call tools again if you need to."
                ),
            }
        )

    retrieved_context: list[dict] = []
    teaching_output: dict | None = None

    for _ in range(MAX_TOOL_ITERATIONS):
        response = _create_completion(
            model=TEACHING_MODEL,
            messages=conversation,
            tools=TOOL_SPECS,
            tool_choice="auto",
            temperature=0.1,
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            raw = message.content or ""
            try:
                teaching_output = json.loads(raw)
            except json.JSONDecodeError:
                conversation.append({"role": "assistant", "content": raw})
                conversation.append(
                    {
                        "role": "user",
                        "content": "That was not valid JSON. Return ONLY one valid JSON object now. No markdown, no tool calls, no extra text.",
                    }
                )
                teaching_output = _finalize_json(conversation, TEACHING_MODEL)
            break

        conversation.append(_assistant_tool_call_message(message, tool_calls))
        for tool_call in tool_calls:
            result, chunks = execute_tool_call(tool_call, subject=subject, grade=grade, chapter=chapter)
            retrieved_context.extend(chunks)
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    else:
        conversation.append(
            {
                "role": "user",
                "content": "You have used enough tools. Respond now with ONLY the final JSON object.",
            }
        )
        teaching_output = _finalize_json(conversation, TEACHING_MODEL)

    retrieved_context = _dedupe_chunks(retrieved_context)
    if not retrieved_context:
        # Grounding guarantee: never present teaching content that wasn't
        # actually backed by a search_ncert result, even if the model tried
        # to skip calling it.
        teaching_output = _no_context_output(subject, chapter, topic)

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
        "teaching_agent": agent_name,
        "messages": messages,
    }


def math_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, MATH_AGENT_PROMPT, "math_agent")


def science_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, SCIENCE_AGENT_PROMPT, "science_agent")


def sst_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, SST_AGENT_PROMPT, "sst_agent")
