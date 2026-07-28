# Contributing to TeacherJi

This is currently a single-maintainer portfolio project, but it's built to
be readable and extendable — this doc is for anyone (including future-me)
picking it back up.

## Project layout

- `backend/agents/` — the LangGraph state machine: Supervisor, Learning
  Agents (math/science/sst/document_tutor), Reflection, quiz/feedback.
  Start with `agents/graph.py` for the wiring, then `agents/state.py` for
  the shared `LearningState` schema.
- `backend/api/` — FastAPI routes, Clerk JWT auth, Postgres/Redis access.
- `backend/rag/` — FAISS ingestion (`ingest.py`) and retrieval
  (`retriever.py`).
- `backend/eval/` — standalone evaluation scripts (`rag_eval.py`,
  `reflection_eval.py`) that hit real infra, not mocks.
- `frontend/src/` — React + TypeScript + Vite. `pages/` are route-level
  screens driven by `store/sessionStore.ts`'s `mode` field (not a URL
  router); `components/` are shared pieces reused across pages.
- `docs/adr/` — architecture decision records for the load-bearing calls in
  `agents/` (see [docs/adr/README.md](docs/adr/README.md)).
- `master_plan.md` — the phased roadmap this project was actually built
  against, with a changelog entry per completed phase. Read this before
  `archie.md`/`plan.md` (the original planning docs it supersedes) if you
  want the real build history.

## Local setup

See the [Quickstart](README.md#quickstart-local-development) section in the
README. Short version: `backend/` needs a Python 3.11+ venv and
`requirements-dev.txt` (adds `pytest` on top of the runtime deps);
`frontend/` needs `npm install`. Both need their own `.env` — see
`.env.example` at the repo root and `frontend/.env.local` respectively.

## Running tests

```bash
# backend unit + integration tests (mocked Groq, no live API calls)
cd backend && pytest

# or from the repo root
make test

# frontend type-check + build
cd frontend && npm run build

# live end-to-end smoke test against a running backend (real Groq/DB calls)
python scripts/test_e2e.py   # or: make test-e2e
```

CI (`.github/workflows/ci.yml`) runs the backend pytest suite and the
frontend build on every push/PR to `main`.

When adding a new agent-layer behavior, prefer a mocked-Groq unit test in
`backend/tests/` over a live call — the existing tests
(`test_supervisor.py`, `test_reflection.py`, `test_tools.py`,
`test_graph_integration.py`) show the pattern: monkeypatch the module's
`call_groq_with_retry` (or `_create_completion` for the tool-calling path)
rather than mocking the `groq` SDK's HTTP layer directly.

## Making a change

1. Check `master_plan.md` first — if what you're doing extends a phase
   already marked done, add to that phase's changelog entry rather than
   leaving the change undocumented. If it's genuinely new scope, a short
   new phase/section is more useful than burying it in an unrelated one.
2. If the change is an architectural decision (not a bug fix or small
   feature) that future-you would want the reasoning for later, add an ADR
   under `docs/adr/` — see the existing ones for the format (Context /
   Decision / Alternatives considered / Consequences).
3. Run the backend pytest suite and the frontend build before considering
   a change done. Neither is optional — both are wired into CI.
4. For frontend UI changes, check both color schemes: the app supports
   light/dark mode via Tailwind's `dark:` variant (toggled by
   `src/components/ThemeToggle.tsx`, class-based via `tailwind.config.cjs`'s
   `darkMode: "class"`). A new component that only looks right in one mode
   is an incomplete change.
5. Keep prompt changes intentional: `agents/prompt_registry.py` tags every
   LLM call with the prompt version that produced it (for LangSmith
   tracing). Bump a template's version in the registry when you change its
   *behavior*, not on a pure typo fix.

## Code style

- Backend: type-hinted Python, `from __future__ import annotations`, no
  framework abstractions beyond what's already in use (raw `groq` SDK, not
  `langchain-groq`; LangGraph only for the state graph itself — see
  [docs/adr/0003-native-tool-calling.md](docs/adr/0003-native-tool-calling.md)
  for why).
- Frontend: TypeScript, Tailwind utility classes (no CSS-in-JS), Zustand for
  client state, TanStack Query for server state. New teaching-output/chat
  text that can contain math or Markdown should render through
  `components/Markdown.tsx`, not a raw `<p>`.
- No comments explaining *what* code does — name things so the code reads
  on its own. A comment is for a non-obvious *why* (a workaround, a subtle
  invariant, a constraint from an external API) — the existing codebase is
  a good reference for the bar here.
