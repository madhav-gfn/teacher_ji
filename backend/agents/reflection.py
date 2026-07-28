"""
Phase 1D: Reflection Agent - gates teaching output only (quiz/feedback skip
reflection entirely, per the cost-guardrail decision in master_plan.md).

Sits between a subject agent and the Supervisor in the graph: checks whether
the just-produced `teaching_output` is grounded in `retrieved_context`,
curriculum-appropriate for the grade, and paced right for the student's
Memory model. A failure routes back to the *same* subject agent exactly once
(`reflection_retry_count` caps it) with the critique appended to its prompt
(see subject_agents.py:_run_subject_agent); a second failure is accepted
anyway so a turn can never loop forever.
"""
from __future__ import annotations

import json
import os

from groq import Groq

from .prompt_registry import render_versioned
from .state import LearningState
from .subject_agents import _format_context, _format_student_memory, call_groq_with_retry

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

REFLECTION_MODEL = "llama-3.1-8b-instant"

_RETRY_NODE_FOR_AGENT = {
    "math_agent": "math_agent",
    "science_agent": "science_agent",
    "sst_agent": "sst_agent",
}

_ACCEPT: LearningState = {
    "teaching_reflection": {},
    "reflection_retry_count": 0,
    "reflection_next": "accept",
}


def reflection_agent(state: LearningState) -> LearningState:
    retrieved_context = state.get("retrieved_context") or []
    if not retrieved_context:
        # The subject agent's canned "NCERT context not found" safety response -
        # not a real teaching attempt, so there is nothing to audit.
        return dict(_ACCEPT)

    teaching_output = state.get("teaching_output") or {}
    topic = state.get("topic", "")
    retry_count = int(state.get("reflection_retry_count", 0))

    system_prompt, prompt_version = render_versioned(
        "reflection",
        teaching_output=json.dumps(teaching_output, ensure_ascii=False),
        context=_format_context(retrieved_context),
        chapter=state.get("chapter", ""),
        topic=topic,
        grade=state["grade"],
        student_memory=_format_student_memory(state, topic),
    )

    try:
        decision = call_groq_with_retry(
            client,
            REFLECTION_MODEL,
            system_prompt,
            "Audit this teaching output now.",
            prompt_name="reflection",
            prompt_version=prompt_version,
        )
        passed = bool(decision.get("passed", True))
        critique = str(decision.get("critique") or "")
    except Exception as exc:
        # Reflection is a quality gate, not a hard dependency - a broken
        # reflection call must never block a teaching turn from completing.
        print(f"Reflection call failed, accepting teaching output as-is: {exc}")
        return dict(_ACCEPT)

    if not passed and retry_count < 1:
        return {
            "teaching_reflection": {"passed": False, "critique": critique},
            "reflection_retry_count": retry_count + 1,
            "reflection_next": "retry",
        }

    return dict(_ACCEPT)


def route_from_reflection(state: LearningState) -> str:
    if state.get("reflection_next") == "retry":
        node = _RETRY_NODE_FOR_AGENT.get(state.get("teaching_agent", ""))
        if node:
            return node
    return "supervisor"
