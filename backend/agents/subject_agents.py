from __future__ import annotations

import json
import os
import re
import time
from contextvars import ContextVar
from types import SimpleNamespace
from typing import Callable

from groq import APIError, Groq
from langsmith import traceable

from .prompt_registry import render_versioned
from .state import LearningState
from .tools import TOOL_SPECS, execute_tool_call

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TEACHING_MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ITERATIONS = 4

# Phase 3B: SSE streaming for the teaching-generation step only (Supervisor/
# Reflection/quiz/feedback stay non-streamed, per master_plan.md's Phase 3
# scope). A ContextVar rather than a state field or function argument because
# it needs to reach a Groq call several stack frames down without threading a
# callback through every function signature in between - and because
# api/routes/session.py sets it around a `run_session()` call that executes
# in a worker thread via `asyncio.to_thread`, which explicitly copies the
# calling context (including ContextVars) into that thread, so this "just
# works" across the sync/async boundary with no explicit hand-off code.
# Default None means "no one is listening" - every existing call path is
# completely unaffected unless a route opts in.
stream_sink: ContextVar[Callable[[str], None] | None] = ContextVar("stream_sink", default=None)

# Phase 3B follow-up fix: llama-3.3-70b-versatile occasionally emits a tool
# call as literal text content instead of a real `tool_calls` delta (the same
# malformed-generation quirk _run_subject_agent's corrective-retry already
# handles - see the comment there, e.g. `<function=search_ncert {...}>` seen
# live). Non-streaming callers never notice, since that raw text just fails
# json.loads and gets silently retried - but a live token stream would
# otherwise show the user that internal-looking fragment as it's typed out.
# Buffered long enough to classify (a real answer starts with `{`), then
# either forwarded normally or suppressed for the rest of that message.
_TOOL_NAMES = "|".join(re.escape(spec["function"]["name"]) for spec in TOOL_SPECS)
# Matches both a bare malformed call (search_ncert(...)) and one wrapped in
# the <function=...> token seen live - the "function=" wrapper is optional.
_MALFORMED_TOOL_CALL_PREFIX = re.compile(rf"^\s*(?:<?/?function\s*=?\s*)?({_TOOL_NAMES})\s*[\(\{{]")
_PREFIX_SNIFF_CHARS = 40


def _stream_chat_completion(groq_client, **kwargs):
    """Consume a Groq streaming response, forwarding content deltas to the
    active stream_sink as they arrive, and return an object shaped like a
    normal (non-streaming) ChatCompletion response - `.choices[0].message`
    with `.content`/`.tool_calls` - so callers can't tell the difference."""
    sink = stream_sink.get()
    stream = groq_client.chat.completions.create(**kwargs, stream=True)

    content_parts: list[str] = []
    tool_call_parts: dict[int, dict[str, str | None]] = {}
    pending_prefix = ""
    classified = False
    suppress = False

    def _maybe_forward(text: str) -> None:
        nonlocal pending_prefix, classified, suppress
        if sink is None or suppress:
            return
        if classified:
            sink(text)
            return
        pending_prefix += text
        if len(pending_prefix) < _PREFIX_SNIFF_CHARS:
            return
        classified = True
        if _MALFORMED_TOOL_CALL_PREFIX.match(pending_prefix):
            suppress = True
            return
        sink(pending_prefix)

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            content_parts.append(delta.content)
            _maybe_forward(delta.content)
        for tool_call_delta in delta.tool_calls or []:
            entry = tool_call_parts.setdefault(
                tool_call_delta.index, {"id": None, "name": "", "arguments": ""}
            )
            if tool_call_delta.id:
                entry["id"] = tool_call_delta.id
            if tool_call_delta.function:
                if tool_call_delta.function.name:
                    entry["name"] = (entry["name"] or "") + tool_call_delta.function.name
                if tool_call_delta.function.arguments:
                    entry["arguments"] = (entry["arguments"] or "") + tool_call_delta.function.arguments

    if sink is not None and not suppress and not classified and pending_prefix:
        # Stream ended before we hit the sniff threshold (a short answer) -
        # flush whatever was buffered rather than dropping it silently.
        sink(pending_prefix)

    reconstructed_tool_calls = [
        SimpleNamespace(
            id=entry["id"],
            function=SimpleNamespace(name=entry["name"], arguments=entry["arguments"]),
        )
        for _, entry in sorted(tool_call_parts.items())
    ]
    message = SimpleNamespace(
        content="".join(content_parts) or None,
        tool_calls=reconstructed_tool_calls or None,
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def call_groq_with_retry(
    client,
    model,
    system_prompt,
    user_message,
    max_attempts=3,
    prompt_name: str | None = None,
    prompt_version: int | None = None,
    allow_streaming: bool = False,
):
    json_instruction = (
        "Return ONLY one syntactically valid JSON object. "
        "Use double-quoted JSON strings, arrays, booleans, and null only. "
        "Do not use markdown, bold syntax, comments, numbered text outside strings, or trailing commas."
    )
    messages = [
        {"role": "system", "content": f"{system_prompt}\n\n{json_instruction}"},
        {"role": "user", "content": user_message},
    ]

    # Traced separately from the retry loop so LangSmith sees one LLM span per
    # actual API call, and never sees `client` (not JSON-serializable) - only
    # the model name and message list, mirroring the OpenAI-compatible shape
    # LangSmith already knows how to pull token usage from. prompt_name/
    # prompt_version (Phase 4C, agents/prompt_registry.py) land in metadata so
    # a trace answers "which prompt version produced this?" directly.
    @traceable(
        run_type="llm",
        name="groq_chat_completion",
        metadata={
            "ls_model_name": model,
            "ls_provider": "groq",
            "prompt_name": prompt_name,
            "prompt_version": prompt_version,
        },
    )
    def _completion(*, messages):
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        # allow_streaming is an explicit per-call opt-in (only document_tutor's
        # teaching call passes it), not a blanket "stream whenever a sink is
        # active" - otherwise Supervisor/Reflection/quiz/feedback calls made
        # during the same graph run would leak raw decision JSON into the
        # same visible stream, which master_plan.md explicitly rules out.
        if allow_streaming and stream_sink.get() is not None:
            return _stream_chat_completion(client, **kwargs)
        return client.chat.completions.create(**kwargs)

    for attempt in range(1, max_attempts + 1):
        raw = ""
        try:
            response = _completion(messages=messages)
            raw = response.choices[0].message.content
            return json.loads(raw)
        except APIError as e:
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


@traceable(
    run_type="llm",
    name="groq_chat_completion_tools",
    metadata={"ls_model_name": TEACHING_MODEL, "ls_provider": "groq"},
)
def _create_completion(max_attempts: int = 3, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            # Every call site through here is a math/science/sst subject
            # agent's teaching-generation loop (see _run_subject_agent) - the
            # one path master_plan.md wants streamed - so, unlike
            # call_groq_with_retry, no separate opt-in flag is needed: it's
            # always safe to stream when a sink is active.
            if stream_sink.get() is not None:
                return _stream_chat_completion(client, **kwargs)
            return client.chat.completions.create(**kwargs)
        except APIError as exc:
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


def _finalize_json(
    conversation: list[dict],
    model: str,
    max_attempts: int = 3,
    prompt_name: str | None = None,
    prompt_version: int | None = None,
) -> dict:
    """Force a final JSON answer once tool use is done - used both to close out
    the loop normally and to repair a non-JSON final message."""
    for attempt in range(1, max_attempts + 1):
        response = _create_completion(
            model=model,
            messages=conversation,
            temperature=0.1,
            tools=TOOL_SPECS,
            tool_choice="none",
            langsmith_extra={"metadata": {"prompt_name": prompt_name, "prompt_version": prompt_version}},
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


def _run_subject_agent(state: LearningState, prompt_name: str, agent_name: str) -> LearningState:
    subject = state["subject"]
    grade = state["grade"]
    chapter = state.get("chapter", "")
    topic = state.get("topic", "")

    # Phase 1A/1E: the Supervisor can redirect this turn to teach a
    # foundational prerequisite instead of the requested topic (see
    # supervisor.py:_eligible_prerequisite_topics). When it does,
    # `target_topic` names the prerequisite - teach that instead, and note it
    # so the Supervisor doesn't redirect to the same prerequisite again this
    # session (state["revised_prerequisites"], set below).
    is_prerequisite_revision = state.get("next_action") == "revise_prerequisite" and bool(
        state.get("target_topic")
    )
    if is_prerequisite_revision:
        topic = state["target_topic"]

    # Phase 4C: render via the versioned registry so prompt_version can be
    # tagged onto every Groq call this turn makes (LangSmith trace metadata).
    system_prompt, prompt_version = render_versioned(
        prompt_name,
        grade=grade,
        chapter=chapter,
        topic=topic,
        student_memory=_format_student_memory(state, topic),
    )
    if is_prerequisite_revision:
        user_message = (
            f"The student is about to learn '{state.get('topic', '')}', but first needs a quick "
            f"refresher on the foundational topic '{topic}' (their mastery on it is currently low). "
            f"Teach '{topic}' now - it may belong to a different chapter than '{chapter}', so ground it "
            f"in whichever {subject} NCERT content actually covers it."
        )
    else:
        user_message = _build_user_message(state)

    conversation: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    reflection = state.get("teaching_reflection") or {}
    is_reflection_retry = bool(reflection.get("critique"))
    if is_reflection_retry:
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

    # On a reflection-triggered retry, keep whatever this same turn already
    # retrieved successfully rather than starting from zero - a rocky
    # tool-calling round on the retry (see the malformed-tool-call recovery
    # below) must not throw away real context the first attempt already got.
    retrieved_context: list[dict] = list(state.get("retrieved_context", [])) if is_reflection_retry else []
    teaching_output: dict | None = None
    tool_call_recovery_attempted = False

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            # max_attempts=1: Groq/llama-3.3-70b-versatile occasionally emits a
            # malformed function-call token (seen live, e.g. a stray space in
            # `<function=search_ncert {...}>`) that its own server-side
            # validation then rejects with a 400. Retrying with the *same*
            # messages just reproduces it near-deterministically at this
            # temperature, so don't burn attempts here - handle it below with
            # an actual corrective nudge instead.
            response = _create_completion(
                max_attempts=1,
                model=TEACHING_MODEL,
                messages=conversation,
                tools=TOOL_SPECS,
                tool_choice="auto",
                temperature=0.1,
                langsmith_extra={"metadata": {"prompt_name": prompt_name, "prompt_version": prompt_version}},
            )
        except APIError as exc:
            if not tool_call_recovery_attempted:
                tool_call_recovery_attempted = True
                print(f"Tool call malformed ({exc}); nudging the model to retry it properly.")
                conversation.append(
                    {
                        "role": "user",
                        "content": (
                            "Your last tool call was malformed and rejected by the API. "
                            "Call the tool again using the real function-calling mechanism "
                            "only - never write the call as literal text in your response."
                        ),
                    }
                )
                continue
            # Already gave it one real chance to fix its own malformed call -
            # stop trying to call more tools and force a final answer from
            # whatever context was gathered so far (tool_choice="none" below
            # shouldn't hit the same failure mode).
            print(f"Tool call failed again after a corrective retry ({exc}); forcing a final JSON answer instead.")
            teaching_output = _finalize_json(conversation, TEACHING_MODEL, prompt_name=prompt_name, prompt_version=prompt_version)
            break
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
                teaching_output = _finalize_json(conversation, TEACHING_MODEL, prompt_name=prompt_name, prompt_version=prompt_version)
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
        teaching_output = _finalize_json(conversation, TEACHING_MODEL, prompt_name=prompt_name, prompt_version=prompt_version)

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
    result: LearningState = {
        "retrieved_context": retrieved_context,
        "teaching_output": teaching_output,
        "teaching_agent": agent_name,
        "messages": messages,
    }
    if is_prerequisite_revision:
        result["revised_prerequisites"] = list(
            dict.fromkeys([*state.get("revised_prerequisites", []), topic.strip().lower()])
        )
    return result


def math_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, "math_agent", "math_agent")


def science_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, "science_agent", "science_agent")


def sst_agent(state: LearningState) -> LearningState:
    return _run_subject_agent(state, "sst_agent", "sst_agent")
