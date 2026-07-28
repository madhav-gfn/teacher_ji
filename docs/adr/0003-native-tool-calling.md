# 0003 - Native Groq tool-calling instead of a LangGraph ToolNode

**Status:** Accepted (2026-07-25)

## Context

The subject agents (`math_agent`/`science_agent`/`sst_agent`) needed real
tool choice — decide *whether* to search the NCERT index, look up
prerequisites, or verify a calculation, rather than always retrieving
unconditionally before a single fixed generation call. LangGraph ships a
`ToolNode` abstraction for exactly this, built on top of LangChain's
tool-calling conventions. But the codebase already used the raw `groq` SDK
directly everywhere, with no LangChain LLM/tool abstractions in active use —
`langgraph` was the only LangChain-family dependency actually load-bearing.

## Decision

Use Groq's native OpenAI-compatible tool-calling surface
(`tools=`/`tool_calls` on `chat.completions.create`) directly, not a
LangGraph `ToolNode`. `agents/tools.py:TOOL_SPECS` defines the three tools'
JSON schemas; `agents/subject_agents.py:_run_subject_agent` runs a bounded
loop (`MAX_TOOL_ITERATIONS = 4`) where the model sees all three tools up
front with `tool_choice="auto"`, and a final `tool_choice="none"` pass
forces a closing JSON answer once tool use is done.

The old eager "retrieve once, then generate" logic didn't disappear — it
moved *inside* `search_ncert` itself (the chapter-scoped-search-empty →
unfiltered-fallback behavior), so the agent still gets that fallback for
free on a single call, it's just the agent's choice to make that call at
all.

A grounding guarantee is enforced mechanically after the loop, not just
trusted to the prompt: if no `search_ncert` call ever returned a chunk, the
output is replaced with the canned "NCERT context not found" response
regardless of what the model produced — covering a model that skips the
tool despite being told to call it.

## Alternatives considered

- **LangGraph `ToolNode`.** Rejected — it would have pulled in LangChain's
  message/tool abstractions as a second, parallel convention alongside the
  raw `groq` SDK already used for every other LLM call (Supervisor,
  Reflection, quiz, feedback), for a codebase with no other LangChain
  runtime dependency. Consistency with the existing pattern won over the
  marginal convenience of a pre-built node.
- **Keep eager retrieval, add tools only for `python_calculator`/
  `get_prerequisites`.** Rejected — half-tooling `search_ncert` would have
  kept the "always retrieve, regardless of whether it's useful" behavior
  that made the Supervisor's "teach Division before Fractions" story
  impossible to express faithfully; the whole point was giving the agent a
  real choice, not just adding two new capabilities alongside a fixed one.

## Consequences

- Tool calls are only visible to LangSmith tracing (Phase 4A) as nested
  messages inside a node's span, not as independent graph nodes/edges — a
  known gap, since `@traceable` on each tool function was enough to make
  them visible spans without needing graph-level nodes.
- A Groq-specific quirk had to be handled directly: `llama-3.3-70b-versatile`
  occasionally emits a malformed function-call token as literal text
  content (`search_ncert(query=...)` or `<function=search_ncert {...}>`)
  instead of a real `tool_calls` delta. `_run_subject_agent` gives one
  corrective nudge, then forces a final JSON answer — handled at the
  application level since there's no LangChain tool-calling shim doing it
  for free.
