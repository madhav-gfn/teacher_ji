# 0001 - LLM-driven Supervisor instead of a rule-based router

**Status:** Accepted (2026-07-25)

## Context

The original pipeline picked the next step (teach → quiz → feedback →
complete) with an if/else router keyed on session mode. It worked, but it
could never do the thing the project's grade actually hinges on: notice that
a student is weak in a prerequisite and redirect to a refresher before the
requested topic, or otherwise adapt the plan to the student rather than just
to the session's mechanical state.

## Decision

Replace the router with `agents/supervisor.py:supervisor_node`, an LLM
decision node on a small/fast model (`llama-3.1-8b-instant`, for cost
control — the teaching/quiz calls stay on `llama-3.3-70b-versatile`). It
reads a JSON summary of the session state, the student's persistent Memory
model (ADR-0004), and prerequisite mastery for the current topic, and
returns `{"next_action", "target_topic", "reasoning"}`.

Turns that have nothing to decide — grading a pending answer, or the current
turn's output already exists — stay on deterministic, non-LLM routing
(`_deterministic_action`). The LLM is only invoked when there's an actual
choice to make; this keeps the added latency/cost bounded to the turns where
it buys something.

The LLM's `revise_prerequisite` choice is never trusted blindly:
`_eligible_prerequisite_topics` computes the actual set of valid redirect
targets (confirmed sub-threshold mastery, not already revised this session)
and the node silently downgrades to `"teach"` if the model's choice isn't in
that set. A model that hallucinates a topic, picks an unassessed one, or
repeats an already-revised one can't strand the student off-topic.

## Alternatives considered

- **Keep the if/else router, add a special case for prerequisites.** Rejected
  — it would hard-code exactly one adaptive behavior instead of giving the
  system a general mechanism to decide when adaptation is warranted. It's
  also the difference the project needed: a system that plans, vs. one that
  executes a fixed sequence.
- **Let the Supervisor's decision be trusted outright.** Rejected after
  building it — an LLM router can hallucinate a target topic or misjudge
  eligibility, and a bad redirect is worse than no redirect. The eligibility
  check exists specifically because the first version trusted the model and
  that failure mode was easy to reproduce.

## Consequences

- Every turn costs one extra small-model call (unless it's a deterministic
  turn), which is the accepted cost guardrail per `master_plan.md`.
- The Supervisor's output shape (`next_action`, `target_topic`) had to be
  added to `LearningState` (`agents/state.py`) — LangGraph only persists
  schema-declared keys, and `target_topic` silently evaporated across graph
  steps until this was caught by a test and fixed.
- `api/routes/session.py`'s response/bookkeeping logic had to stop assuming
  "the topic taught this turn is the one requested," since a redirect breaks
  that assumption. See `_was_redirected_to_prerequisite` and
  `_actually_taught_topic`.
