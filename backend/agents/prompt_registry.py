"""
Phase 4C: versioned prompt registry.

prompts.py still owns the actual template text (no reason to move working
strings into YAML/JSON for a single-developer project) - what this module
adds is a stable name + integer version per template, so every LLM call can
be tagged with exactly which prompt version produced its output. That tag
flows into the LangSmith trace (see agents/subject_agents.py:call_groq_with_retry
and _create_completion, both of which accept prompt_name/prompt_version) -
this is what Phase 4A's "tag traces with the version that produced them"
needed the registry for.

Bump the version here whenever a template's *behavior* changes (not on pure
typo fixes) - that's what makes "which prompt version produced this output"
a meaningful question to ask of a trace later, e.g. when comparing two
versions' reflection pass rates.
"""
from __future__ import annotations

from dataclasses import dataclass

from .prompts import (
    FEEDBACK_AGENT_PROMPT,
    GENERIC_TUTOR_PROMPT,
    MATH_AGENT_PROMPT,
    QUIZ_GENERATOR_PROMPT,
    REFLECTION_PROMPT,
    SCIENCE_AGENT_PROMPT,
    SST_AGENT_PROMPT,
    SUPERVISOR_PROMPT,
    TOPIC_EXTRACTION_PROMPT,
    render_prompt,
)


@dataclass(frozen=True)
class PromptEntry:
    name: str
    version: int
    template: str


_REGISTRY: dict[str, PromptEntry] = {
    entry.name: entry
    for entry in (
        PromptEntry("math_agent", 1, MATH_AGENT_PROMPT),
        PromptEntry("science_agent", 1, SCIENCE_AGENT_PROMPT),
        PromptEntry("sst_agent", 1, SST_AGENT_PROMPT),
        PromptEntry("generic_tutor", 1, GENERIC_TUTOR_PROMPT),
        PromptEntry("quiz_generator", 1, QUIZ_GENERATOR_PROMPT),
        PromptEntry("feedback_agent", 1, FEEDBACK_AGENT_PROMPT),
        PromptEntry("supervisor", 1, SUPERVISOR_PROMPT),
        PromptEntry("reflection", 1, REFLECTION_PROMPT),
        PromptEntry("topic_extraction", 1, TOPIC_EXTRACTION_PROMPT),
    )
}


def get_prompt(name: str) -> PromptEntry:
    return _REGISTRY[name]


def render_versioned(name: str, **values: object) -> tuple[str, int]:
    """Render the current version of a registered prompt. Returns
    (rendered_text, version) - callers pass the version through to
    call_groq_with_retry/_create_completion so it lands on the trace."""
    entry = _REGISTRY[name]
    return render_prompt(entry.template, **values), entry.version
