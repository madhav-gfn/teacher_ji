# TeacherJi — Master Phased Revamp Plan

> Synthesizes `plan.md` (evaluation + phase structure) and `archie.md` (target agentic architecture), locked to the decisions made on 2026-07-20:
> - **Supervisor**: LLM-driven decision node (not rule-based), using a small/fast model for cost control.
> - **Reflection**: gates teaching output only, not quiz/feedback — caps the extra-LLM-call cost.
> - **Phase 1 tools**: `search_ncert`, `get_prerequisites`, `python_calculator` (diagram generation deferred).
> - **Auth**: Clerk. **UI**: chat panel added alongside existing card UI, not a rewrite. **Backend host**: Hugging Face Spaces (Render's 512MB limit is already the cause of the current broken deploy).
> - **Priority**: the agentic core (Phase 1 below) ships before auth/polish — it's the thing that changes the project's grade, everything else is packaging.

Every phase ends with something deployed and working — never a half-migrated state.

---

## Phase 0 — Stabilize the Free Deployment (prerequisite, ~1 day)
*Goal: stop fighting infra before touching architecture. Current Render deploy already exceeded memory — fix the foundation first.*

- Move backend hosting from Render → **Hugging Face Spaces (Docker SDK)**. Free CPU-basic tier gives materially more headroom than Render's 512MB, which is what triggered the HF-embeddings detour in the first place.
- Add a `Dockerfile` for the Spaces build; confirm FAISS index artifacts (`rag/index/*.faiss`, `*_meta.json`) are either committed or rebuilt on container start — don't let ingestion be a manual local-only step the deployed container can't reproduce.
- Keep embeddings on the remote HF Inference `feature_extraction` path (already decided against loading a local model — correct call under a memory-constrained free host).
- Repo hygiene: remove `myenv/` and `dist/` from git, add to `.gitignore`; pin all versions in `requirements.txt`; complete `.env.example`.
- Frontend stays on Vercel free, `VITE_API_URL` pointed at the new Spaces URL.

**Deployable after this phase:** identical functionality to today, just running reliably on the intended free stack.

---

## Phase 1 — The True Agentic Core (highest priority, ~5-7 days)
*Goal: this is the phase that actually changes the project's grade. Everything else is packaging around this.*

### 1A. Supervisor node (replaces the if/else router)

Today, `route_from_orchestrator()` in `orchestrator.py` is pure Python — it never asks a model anything, it just switches on a `mode` string. That's the single biggest reason this reads as "RAG with routing," not agentic AI.

Replace it with an LLM decision node:
- Model: `llama-3.1-8b-instant` (fast/cheap — this call happens on every turn, so it shouldn't be the 70B model).
- Input: current `LearningState` + the student's Memory model (1B below) + relevant prerequisite edges (1C).
- Output: strict JSON — `{"next_action": "teach" | "revise_prerequisite" | "quiz" | "reflect_retry" | "complete", "target_topic": str, "reasoning": str}`.
- `graph.py`'s conditional edges now branch on `next_action` from the Supervisor's *reasoning*, not a client-supplied `mode` string. The mode field becomes an input signal, not the sole router.

### 1B. Memory Agent (fixes "each session starts fresh")

The `students` Postgres table already exists (`profile JSONB`) but is only written at session end and never meaningfully shapes a new session. Upgrade it to the structured model `archie.md` specifies:

```json
{
  "learning_style": "visual",
  "mastery": {"division": 0.42, "fractions": 0.81},
  "weak_topics": ["division"],
  "revision_due": ["fractions"],
  "confidence": {"division": 0.39, "fractions": 0.84}
}
```

- Computed/updated after every `feedback_agent` call (mastery is a rolling function of quiz correctness + re-explanation requests), not just at session end.
- Loaded once at `session/start` and injected into every Supervisor and Learning Agent prompt for that session — this is what makes "student previously struggled with Division" actually change behavior instead of just being logged.

### 1C. Tools for the Learning Agent

Currently `math_agent`/`science_agent`/`sst_agent` always do one fixed retrieval + one Groq call — no decision is ever made about *how* to answer. Give them real tool choice (Groq tool-calling or a LangGraph `ToolNode`):

| Tool | What it does | Notes |
|---|---|---|
| `search_ncert(query, chapter?)` | Wraps the existing `retriever.retrieve()` — but now the agent *chooses* to call it rather than it running unconditionally | Smallest lift — mostly a signature change |
| `get_prerequisites(topic)` | Returns prerequisite topics from a curriculum dependency map | **Real content work**: build a small static JSON map per subject/grade (e.g. `division → fractions → decimals → percentages` for math 6-8). This is the single highest-impact addition — it's what lets the Supervisor produce the "teach Division before Fractions" flow that's the centerpiece example in `archie.md` |
| `python_calculator(expression)` | Verifies a computed numeric answer before the math agent presents it | Use a restricted AST-based evaluator, not `eval()` — don't introduce an injection surface for the sake of a demo feature |

*(`generate_diagram` deferred to a later phase — lower interview impact than the three above, per your call.)*

### 1D. Reflection Agent — teaching output only

- After a subject agent produces `teaching_output`, one cheap `llama-3.1-8b-instant` call checks: is this grounded in the retrieved chunks, curriculum-appropriate for the grade, and at the right difficulty per the student's Memory model?
- Fail → one bounded retry of the subject agent with the critique appended to the prompt. No infinite loop; cap at 1 retry to control latency/cost.
- Quiz generation and feedback scoring **skip** reflection — this halves the extra-call cost relative to reflecting everything, per your decision.

### New graph shape

```mermaid
flowchart TD
    START --> SUP[Supervisor\nLLM decision: teach / revise_prereq / quiz / complete]
    SUP -->|revise_prerequisite| LEARN
    SUP -->|teach| LEARN[Learning Agent\nmath/science/sst + tools]
    LEARN -->|search_ncert / get_prerequisites / python_calculator| TOOLS[(Tools)]
    TOOLS --> LEARN
    LEARN --> REFLECT[Reflection Agent\nteaching output only]
    REFLECT -->|fail, retry<=1| LEARN
    REFLECT -->|pass| SUP
    SUP -->|quiz| QUIZ[quiz_generator]
    QUIZ --> SUP
    SUP -->|feedback| FEED[feedback_agent]
    FEED --> MEM[Memory Agent\nupdate mastery model]
    MEM --> SUP
    SUP -->|complete| END
```

**Deployable after this phase:** same UI as today, but sessions now visibly behave differently — a student weak in Division gets redirected to a refresher before Fractions, quiz difficulty shifts with mastery, math answers are calculator-verified, and reasoning is inspectable. This is the demo moment for interviews — record it.

**Cost guardrail:** Supervisor + Reflection both on `8b-instant`, only the actual teaching/quiz generation stays on `70b-versatile`. Log token counts per session before shipping to sanity-check against Groq's free-tier rate limits.

---

## Phase 2 — Auth & Professional Foundation (~2-3 days)

- **Clerk** integration (already decided): replace the `student-${random}` localStorage ID with Clerk-authenticated users; verify Clerk JWTs in FastAPI middleware; map Clerk `user_id` → `students.student_id`.
- **README overhaul**: move the raw dev-journal section into a linked `ENGINEERING_LOG.md` (it's good evidence of debugging skill — just not the first thing a recruiter should see). Add: problem statement, screenshots/demo link, a "Key Design Decisions" section that explicitly walks through the Supervisor → Learning Agent → Memory → Reflection loop from Phase 1, and a "Limitations & Future Work" section.
- Repo hygiene finish: `.env.example` gets Clerk keys; Pydantic validation audit; React error boundary; consistent HTTP error responses.

**Deployable after this phase:** real accounts, a README that actually sells the architecture instead of hiding it.

---

## Phase 3 — Chat Panel + Streaming (~3-4 days)

- Chat panel alongside the existing card UI (decided — not a rewrite): follow-ups and re-explanation requests route through the *same* Supervisor/Learning Agent loop from Phase 1 — a chat message is just another goal the Supervisor plans against, not a separate code path.
- SSE streaming (`StreamingResponse` + Groq `stream=True`) for the Learning Agent's generation step. Supervisor and Reflection stay non-streamed (they're short JSON decisions) — streaming is applied where the user is actually staring at the screen.
- Markdown + KaTeX rendering; progress dashboard pulling mastery-per-topic directly from the Phase 1B Memory model (this is now real data, not a UI mockup).

**Deployable after this phase:** streaming chat UX layered onto the agentic core.

---

## Phase 4 — Observability & Evaluation (~2-3 days)

- **LangSmith** (already in `archie.md`'s stack, pairs natively with LangGraph — simpler than adding Langfuse on top). Trace Supervisor decisions, tool calls, and reflection verdicts explicitly — this doubles as demo material ("here's the trace of the agent choosing to teach a prerequisite first").
- RAG eval script: small labeled set per subject measuring retrieval relevance + answer faithfulness; also evaluate Reflection Agent precision against a seeded set of known-bad outputs.
- Prompt versioning: move `prompts.py` templates into versioned config, tag traces with the version that produced them.

**Deployable after this phase:** inspectable traces + quality metrics — the MLOps signal recruiters look for.

---

## Phase 5 — Polish & Portfolio (~2-3 days)

- UI pass: dark mode, mobile responsive, loading states that reflect **real** agent stages ("Checking what you already know…" → "Deciding what to teach…" → "Verifying explanation…") — honest copy now that these are actual pipeline stages, not decoration.
- Landing page with demo video/GIF, architecture diagram, "Try it free" CTA.
- Tests: unit tests for Supervisor decision parsing, tool functions, reflection pass/fail logic; integration test for the full loop. CI via GitHub Actions.
- ADRs for the Phase 1 architecture decisions; contributing guide.

**Deployable after this phase:** portfolio-ready, interview-ready.

---

## Free Deployment Stack (final)

| Component | Free Option | Notes |
|---|---|---|
| Frontend | Vercel | unchanged |
| Backend | **Hugging Face Spaces (Docker)** | replaces Render — fixes the memory-limit issue from the dev log |
| Postgres | NeonDB | unchanged, now also holds the structured Memory model |
| Redis | Upstash | unchanged, session-scoped state only |
| LLM | Groq | `8b-instant` for Supervisor/Reflection, `70b-versatile` for teaching/quiz |
| Auth | Clerk | per your decision |
| Observability | LangSmith (free tier) | pairs natively with LangGraph |
| Embeddings | HuggingFace Inference | unchanged — correct call to avoid loading a local model on a memory-constrained host |

---

## Why Phase 1 is the fulcrum

Phases 0 and 2-5 are packaging: hosting, accounts, UX, and polish that any well-built RAG app needs. Phase 1 is the only phase that changes what this project *is* — from a deterministic pipeline with an LLM at the end, to a system where a model plans the next action, chooses tools, checks its own output, and adapts using persistent memory. That's the difference between a 5/10 and an 8+/10 in an interview, and it's why it's sequenced first.
