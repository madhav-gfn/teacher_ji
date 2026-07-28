# 0002 - Reflection Agent gates teaching output only

**Status:** Accepted (2026-07-25)

## Context

A second LLM pass that audits an agent's output before the student sees it
is the mechanism that catches ungrounded, off-grade, or badly-paced answers.
Applied everywhere, it doubles the LLM call count for the whole session; the
project runs on Groq's free tier, so cost/rate-limit headroom is a real
constraint, not a hypothetical one.

## Decision

`agents/reflection.py:reflection_agent` sits between a subject agent
(`math_agent`/`science_agent`/`sst_agent`) and the Supervisor, and checks
only `teaching_output` — whether it's grounded in `retrieved_context`,
curriculum-appropriate for the grade, and paced right per the student's
Memory model. `quiz_generator` and `feedback_agent` route straight back to
the Supervisor and never pass through reflection.

A failure routes back to the *same* subject agent exactly once
(`reflection_retry_count` caps it at 1), with the critique appended to the
conversation so the retried agent knows exactly what to fix. A second
failure is accepted anyway — a turn must always terminate.

Two additional guardrails, found necessary while building this: if
`retrieved_context` is empty (the subject agent's own canned "NCERT context
not found" safety response), reflection is skipped entirely — there's
nothing real to audit, and spending a call on it buys nothing. And if the
reflection call itself throws (bad JSON, API error), it fails open and
accepts the teaching output rather than blocking the turn — reflection is a
quality gate, not a hard dependency, matching the same posture LangSmith
tracing (ADR-adjacent, Phase 4) takes toward its own failures.

## Alternatives considered

- **Reflect every agent output, including quiz/feedback.** Rejected — halves
  available headroom under the free-tier rate limit for a check that matters
  most where an ungrounded or off-grade *explanation* would actually mislead
  a student. A wrong quiz question is caught by the student getting it
  "wrong" against a bad key; a wrong explanation is silently absorbed.
- **Unbounded retry until reflection passes.** Rejected — a strict
  pedagogical bar (see the Phase 4B eval's 50% precision finding) combined
  with unbounded retry risks a turn that never terminates or burns arbitrary
  latency/cost. One bounded retry, then accept, was chosen deliberately over
  chasing a perfect pass rate.

## Consequences

- Teaching turns cost one extra small-model call in the common case, two on
  a reflection failure. Quiz/feedback turns are unaffected.
- The Phase 4B eval later measured this prompt's actual precision at 50%
  (it over-rejects grounded-but-paraphrased answers and under-scaffolded
  answers for students with no mastery data at all) — a real calibration gap
  in `REFLECTION_PROMPT`, tracked as a known gap rather than fixed under
  Phase 4, since tuning agent behavior is this ADR's/Phase 1D's scope, not
  the evaluation phase's.
