# Daskalos v3 — Master Plan 2: Pivot to a Coding Tutor

> Supersedes `master_plan.md` for scope going forward — that file stays as-is,
> it's the build history for the NCERT version. Locked to decisions made on
> 2026-07-29:
> - **7 tracks**, not a subject × language matrix: 2 concept tracks
>   (**Programming Fundamentals**, **OOP**) + 5 **thin** language tracks
>   (**Python, JavaScript, Java, C++, C#**).
> - **Thin language tracks**: each assumes Fundamentals is already mastered
>   and teaches only that language's syntax/idioms mapped onto the Fundamentals
>   concept list. No re-teaching "what is a loop" five times. Gated behind
>   Fundamentals-track mastery; the OOP-flavored topics inside a language
>   track are additionally gated behind OOP-track mastery.
> - **No RAG.** NCERT needed retrieval because the model can't be trusted on
>   textbook-specific facts. Mainstream language syntax doesn't have that
>   problem, and code has a ground truth text never had: *run it*. The
>   Reflection Agent's grounding check moves from "matches a retrieved chunk"
>   to "the code was actually executed and produced the claimed output."
>   This deletes the ingestion-pipeline problem entirely instead of solving it.
> - **Piston** (open-source sandboxed code execution, self-hostable) replaces
>   `python_calculator` as the one new load-bearing tool — covers all 5
>   languages behind one HTTP API with built-in timeouts/resource limits.
> - **Supervisor, Memory Agent, Reflection Agent, auth, chat panel, streaming,
>   dashboard all carry over unchanged.** This is a content/tooling pivot on
>   top of an architecture that was already generic — not a rewrite.
> - **⚠️ Rigor, not middle-school framing.** Explicitly overturned from an
>   earlier direction floated in this doc's own conversation history: content
>   is pitched at real CS-curriculum rigor (CS50/MIT 6.0001/Real
>   Python/Eloquent JavaScript/learncpp.com/Effective Java-caliber precision
>   and idiom), not simplified or age-softened. Concrete implementation
>   consequence, called out again inline in Phase 1: the Reflection Agent's
>   `curriculum_appropriate` check must be calibrated toward "correct,
>   precise, idiomatic" as the bar, not "simple." A prompt written with an
>   implicit "explain like they're 12" framing will make Reflection actively
>   reject good, rigorous teaching output as too-advanced — that's a prompt
>   bug to watch for, not a feature.
>
> Every phase ends with something deployed and working — same discipline as
> `master_plan.md`.

---

## Phase 0 — Generalize `subject` → `Track` (~2-3 days)

*Goal: stop hardcoding three subjects before adding four more. This is
plumbing, not content — do it once, cleanly, before Phase 1's content lands
on top of it.*

- Replace the `math_agent` / `science_agent` / `sst_agent` trio
  (`agents/subject_agents.py`) with a single config-driven `track_agent(track_config)`.
  The three functions are already near-duplicates apart from their prompt and
  tool list — this collapses them instead of growing to seven copies.
- Define a `Track` config shape (`api/tracks.py`, replacing `api/curriculum.py`):
  ```json
  {
    "id": "python",
    "kind": "language",            // "concept" | "language"
    "display_name": "Python",
    "topics": ["variables", "conditionals", "..."],
    "prerequisites": {"...": ["..."]},   // intra-track, same shape as today's prerequisites.py
    "gate": {"requires_track": "fundamentals", "min_mastery": 0.6}
  }
  ```
  Concept tracks (`fundamentals`, `oop`) omit `gate`. Language tracks set it;
  their OOP-flavored topics carry a per-topic override
  (`"requires_track": "oop"`) rather than gating the whole track on OOP.
- `get_prerequisites` (`agents/tools.py`) and the Supervisor's eligibility
  check (`agents/supervisor.py:_eligible_prerequisite_topics`) already operate
  on an abstract topic/prerequisite shape — verify they don't assume
  `subject in {math, science, sst}` anywhere and generalize the couple of
  spots that do.
- Retire the NCERT-specific plumbing this makes dead: `rag/ingest.py`,
  the FAISS indexes under `rag/index/`, `data/ncert/`, and `search_ncert`
  itself (superseded by execution-based grounding in Phase 2). Don't delete
  outright in this phase — stub `search_ncert` as a no-op tool and remove for
  real once Phase 2 lands, so nothing is broken mid-phase.
- `LearningState`'s `subject`/`chapter` fields become `track_id` (drop
  `chapter` — tracks don't have chapters, just an ordered topic list).

**Deployable after this phase:** same UI, same behavior, but the backend
is now shaped for seven tracks instead of three hardcoded subjects — no new
content live yet.

---

## Phase 1 — Concept Tracks: Programming Fundamentals + OOP (the fulcrum, ~3-4 days)

*Goal: this is the phase that actually proves the pivot works. Everything
else is packaging around it — same role Phase 1 played in `master_plan.md`.*

- Author the **Programming Fundamentals** topic list (~8-9 concepts,
  pseudocode-first, no single language required): variables & data types →
  input/output → operators & expressions → conditionals → loops → functions
  & parameters → arrays/lists → strings → reading error messages. Each topic
  gets the same `teaching_output` shape as today (headline, explanation,
  analogy, example) — analogy/example are pseudocode or plain-English, not
  tied to a language.
- Author the **OOP** topic list (~7-8 concepts), gated on Fundamentals mastery
  ≥ 0.6: classes & objects → constructors & instance state → encapsulation →
  methods & `self`/`this` → inheritance → polymorphism → abstraction →
  composition vs. inheritance.
- New track-agent prompt for `kind: "concept"` tracks: no tools required
  (no `search_ncert`, no code execution yet), teach directly from the
  concept + the student's Memory model, same as before minus retrieval.
- **Reflection Agent's grounding check changes for concept tracks**: since
  there's no retrieved context to check against, this follows the same
  pattern `reflection.py` already uses for the empty-context case (1D in
  `master_plan.md`) — skip the grounding sub-check, keep the
  curriculum-appropriateness and right-difficulty checks. Nothing new to
  build here, just route concept tracks onto an existing code path.
- **⚠️ Calibrate `curriculum_appropriate` for rigor, not simplicity.** This is
  the one prompt in the whole pivot most likely to silently undo the rigor
  decision above: `REFLECTION_PROMPT`'s difficulty/appropriateness check was
  originally tuned for a specific NCERT grade band, and if it's ported over
  with any implicit "keep it simple for a young student" framing, it will
  reject correct, idiomatic teaching output for being "too advanced" —
  actively fighting the goal instead of serving it. Write and eval this
  prompt against the rigor bar (CS50/Real Python/Eloquent JS-caliber), not a
  simplified one, and seed `reflection_eval.py`-style test cases that
  specifically catch over-simplification, not just under-grounding.
- Cross-track gating goes live: attempting to start `oop` before Fundamentals
  mastery clears the threshold returns a "not ready yet" response rather than
  teaching — checked once at `/session/start`, not mid-session.

**Deployable after this phase:** a student can pick Fundamentals or OOP and
get taught, quizzed, and mastery-tracked with zero language-specific content
yet. This is the moment to sanity-check the whole pivot before spending time
on 5x language content.

---

## Phase 2 — Code Execution Tool: Piston Integration (~2-3 days)

*Goal: the one genuinely new/hard piece. Do it in isolation before wiring it
into teaching content, so sandbox bugs don't get confused with prompt bugs.*

- `run_code(language, code, stdin="")` tool (`agents/tools.py`), calling a
  Piston instance (`POST /api/v2/execute`). Start against the public Piston
  API for development; plan to self-host (Docker, it's a single container)
  before any real traffic — the public instance is rate-limited and not
  meant for production load.
- Wrap it the same way `python_calculator` was wrapped: no bare `eval`/`exec`
  in-process, ever. Piston's isolation (per-run containers, CPU/memory/wall-time
  limits) is the actual security boundary — this tool is a thin HTTP client
  over it, not a sandbox itself.
- Map the 5 track languages to Piston's runtime names (`python`, `javascript`,
  `java`, `cpp`, `csharp` — confirm exact runtime/version strings against
  Piston's `/api/v2/runtimes` before hardcoding).
- Failure modes to handle explicitly (mirrors the care `subject_agents.py`
  already takes around Groq failures): Piston timeout, Piston unreachable,
  compile error vs. runtime error vs. correct-but-wrong-output — these are
  three different signals the track agent needs to react to differently
  (a compile error means "my example is broken," a wrong-output result on a
  student submission means "the student's code is wrong").
- **This is what powers the new grounding check**: for language tracks, the
  Reflection Agent's grounding sub-check becomes "was `run_code` called on
  this example, and did it execute without error" instead of a retrieval
  check. If the teaching output includes a code example that was never
  actually run, that's now a hard reflection failure, not a maybe.

**Deployable after this phase:** `run_code` works standalone (test it
directly against known-good/known-bad snippets in all 5 languages) — not
yet wired into a teaching flow.

---

## Phase 3 — Five Language Tracks (~3-4 days)

*Goal: content authoring + wiring, now that Phase 1 proved the concept-track
path and Phase 2 proved the execution tool.*

- For each language (Python/JS/Java/C++/C#), author a thin topic list that
  maps 1:1 onto Fundamentals' 8-9 concepts ("variables in Python," "loops in
  JavaScript," ...) plus the OOP-in-that-language mirror of the OOP list,
  each OOP-flavored topic tagged with the per-topic `requires_track: "oop"`
  gate from Phase 0's schema.
- Track-agent prompt for `kind: "language"` tracks: given a Fundamentals/OOP
  concept the student already (per Memory model) has some mastery of, produce
  the syntax-specific explanation + a runnable example, then **call
  `run_code`** to verify the example before presenting it — this is the
  loop that makes the new grounding check meaningful, not just possible.
- Cross-track gate enforcement for all 5 language tracks (Phase 1 already
  built and proved this for the OOP track; this is applying it four more
  times against the same code path, not new logic).

**Deployable after this phase:** all 7 tracks live, gating works, every code
example shown to a student has actually been executed.

---

## Phase 4 — Code-Challenge Agent (replaces quiz/feedback, ~2 days)

*Goal: `quiz_generator`/`feedback_agent` assumed multiple-choice. Coding
needs "write code, run it, check the output" instead.*

- `challenge_generator` (replaces `quiz_agent.py:quiz_generator` for these
  tracks): produces a short problem statement + expected stdout for given
  test input, scoped to the topic just taught.
- `challenge_feedback` (replaces `feedback_agent`): takes the student's
  submitted code, runs it via `run_code` against the same test input,
  diffs actual vs. expected stdout. Correct/incorrect is a code fact, not an
  LLM judgment call — the LLM's job is generating the human-readable
  feedback message (what went wrong, a hint), not deciding pass/fail.
- Mastery/EMA update on submission reuses the exact mechanism Memory Agent
  already has (1B in `master_plan.md`) — a code challenge result is just
  another correctness signal feeding the same rolling update.

**Deployable after this phase:** full teach → challenge → feedback → mastery
loop works for all 7 tracks, backend-complete.

---

## Phase 5 — Frontend: Editor, Track Picker, Challenge UI (~3-4 days)

- **Track picker** replaces `SelectionPage`'s grade/subject/chapter picker:
  7 cards (2 concept, 5 language), the 5 language cards visually locked
  (with the mastery threshold shown, e.g. "Unlocks at 60% Fundamentals
  mastery") until the gate clears — reuses `GET /student/{id}`'s mastery
  data that already powers `ResultsPage`, no new endpoint needed.
- **Embedded code editor** (Monaco or CodeMirror — Monaco if VS Code-familiar
  syntax highlighting/autocomplete matters more than bundle size, CodeMirror
  if bundle size matters more given the existing ~900KB KaTeX warning from
  `master_plan.md` Phase 3D) with a Run button wired to a new
  `POST /session/run-code` passthrough to the `run_code` tool, so students
  can experiment freely, not just watch examples.
- **Challenge UI**: editor + Run + Submit, rendering `challenge_feedback`'s
  output (pass/fail, expected vs. actual, hint) — same visual language as
  today's `FeedbackPanel`, new content shape.
- KaTeX/Markdown rendering (`Markdown.tsx`, Phase 3D) already handles fenced
  code blocks for the *explanation* text — verify syntax highlighting per
  language works (it likely already does via `rehype`/`remark`'s default
  code handling; confirm rather than assume).

**Deployable after this phase:** fully usable coding tutor end to end.

---

## Phase 6 — Polish (~2 days)

- Tests: mocked-Piston unit tests for `run_code`'s three failure modes
  (Phase 2), mocked-Groq tests for the concept-track and language-track
  agents (mirrors the existing pattern in `backend/tests/`), an integration
  test driving a full track through the graph.
- New ADR: `0005-execution-based-grounding.md` — documents the RAG → code-execution
  swap as a deliberate architecture decision (context: NCERT-style
  retrieval doesn't fit code; alternatives considered: RAG over language
  docs, no grounding at all; consequence: grounding is now “did it run,” not
  “does it match a source,” which is stronger for code and doesn't
  generalize back to prose).
- README/`master_plan.md` cross-links updated so a reader lands on the right
  history — `master_plan.md` stays the NCERT build log, this file is the
  pivot log, README points at both.

**Deployable after this phase:** portfolio-ready v3.

---

## Updated Stack

| Component | v2 (NCERT) | v3 (Coding) |
|---|---|---|
| Grounding | FAISS + NCERT PDF ingestion | `run_code` execution (Piston) |
| Subject/Track content | 3 hardcoded subjects | 7 `Track` configs |
| New external dep | HuggingFace Inference (embeddings) | Piston (self-hosted Docker) |
| Everything else (Supervisor, Memory, Reflection, Clerk, Redis, Postgres, Groq, LangSmith) | unchanged | unchanged |

---

## Why Phase 1 + Phase 2 are the fulcrum

Phase 0 is necessary plumbing and Phases 3-6 are largely applying an already-proven
pattern five more times plus UI. The two phases that actually change what
this project *is* are Phase 1 (proving concept-only tracks work without any
retrieval) and Phase 2 (execution as a stronger-than-RAG grounding source).
Once those two are live, the remaining phases are volume, not risk — which
is exactly the order to sequence them in.
