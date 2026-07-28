# Architecture Decision Records

Records of the decisions that shaped Phase 1 (the agentic core — see
`master_plan.md`). Each one covers a single decision: the context that forced
it, what was chosen, what was explicitly rejected, and the trade-off accepted.

- [0001 - LLM-driven Supervisor instead of a rule-based router](0001-llm-supervisor.md)
- [0002 - Reflection gates teaching output only](0002-reflection-scope.md)
- [0003 - Native Groq tool-calling instead of a LangGraph ToolNode](0003-native-tool-calling.md)
- [0004 - Structured, persistent Memory model](0004-persistent-memory-model.md)

New ADRs are numbered sequentially and never renumbered or deleted — a
superseded decision gets a new ADR that says so, so the history stays intact.
