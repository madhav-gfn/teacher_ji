# 0004 - Structured, persistent Memory model

**Status:** Accepted (2026-07-22)

## Context

The `students` Postgres table (`profile JSONB`) already existed, but was
only written at session end and never meaningfully shaped a new session —
every session effectively started fresh, with no way for "this student
struggled with Division last week" to change anything about how the next
session teaches Fractions.

## Decision

Upgrade the profile to a structured model, computed and updated after every
`feedback_agent` call (quiz correctness) *and* every re-explanation request
(`/session/explain-differently`) as a rolling function — not just scored
once at session end:

```json
{
  "learning_style": "visual",
  "mastery": {"division": 0.42, "fractions": 0.81},
  "confidence": {"division": 0.39, "fractions": 0.84},
  "weak_topics": ["division"],
  "revision_due": ["fractions"]
}
```

Loaded once at `/session/start` and carried in `LearningState` for the rest
of the session, so it's available to the Supervisor's state summary and
every Learning Agent's prompt without a re-fetch per turn. This is the data
ADR-0001's prerequisite-eligibility check and ADR-0002's pacing check both
read from.

## Alternatives considered

- **Re-fetch from Postgres on every turn.** Rejected — the model doesn't
  change mid-session in a way that matters turn-to-turn (mastery updates
  happen at feedback/re-explanation boundaries, not mid-explanation), so a
  per-turn round-trip would add latency for no behavioral benefit. Loading
  once at session start and carrying it in graph state was simpler and
  cheaper.
- **Score only at session end (the original behavior).** Rejected — this is
  the exact behavior being replaced; it's why "adapts using persistent
  memory" wasn't true of the system before this decision.

## Consequences

- `quiz_generator` still only looks at this session's `weak_topics`, not the
  persistent `mastery`/`revision_due` maps — carried forward as a known gap,
  not fixed here.
- `learning_style` has no signal source yet and is stuck at the `"text"`
  default — the field exists in the schema for when a signal is added, but
  nothing currently writes anything else to it.
- The frontend's results page rendered a fake mastery formula instead of
  this real data until Phase 3A closed that gap — flagged as "explicitly
  Phase 3's job" in this decision's own changelog entry at the time.
