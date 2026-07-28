# Engineering Log

Raw, chronological notes from building and debugging Daskalos — kept as-is
because the debugging trail is the interesting part. See [README.md](README.md)
for the architecture overview and current state.

---

## Deployment memory limits and the embedding model saga

a fresh issue has come up
my deployment has exeeded the memory limit
so imma try hugging face emmbeddings to get this done
may be this will reduce some load
but  my FAISS database might also be the problem

my HF model is not working its giving some HTTPS error
I am getting this error when trying to use the Hugging Face API for embeddings:

changed the model


it was not the issue
The real problem was model/task mismatch:

sentence-transformers/all-MiniLM-L6-v2 and intfloat/multilingual-e5-small are served by HF Inference as sentence-similarity, not feature-extraction.
my RAG needs raw embedding vectors, so it must use HF feature_extraction.
I switched the code to Hugging Face's official InferenceClient.feature_extraction path and changed the model to one that actually works with my setup: microsoft/harrier-oss-v1-0.6b.



still this doesn't work the backend is throwing 404 error
and render shows failed to generate

Final issue was:

my UI/backend curriculum still had old Class 6 math chapters like Whole Numbers.
my rebuilt PDF/index has current chapters like Number Play, Prime Time, The Other Side of Zero.
Because of that mismatch, retrieval returned no NCERT context.
Then the math prompt asked Groq for a "bold statement", so Groq generated invalid JSON like:
"headline": **"Natural and Whole Numbers Introduction"**


I fixed:

JSON prompts: no markdown/bold/unquoted values.
Groq retry: adds strict JSON correction after JSON-mode rejection.
Teaching retrieval: if chapter-filtered retrieval returns empty, it retries without stale chapter filter.
Quiz retrieval: same fallback.
Class 6 math curriculum in backend and frontend now matches the ingested PDF chapters.
Verified a production-like math agent call succeeds:
dict_keys([...])
Numbers in daily life
5 retrieved chunks

---

## Document upload — studying your own material, not just NCERT PDFs

new feature: let students upload their own material and study it, not just NCERT PDFs.

the whole app was built around subject (math/science/sst) + grade + chapter, with a hardcoded
topic list per chapter in curriculum.py. an uploaded PDF/txt/md has none of that, so I couldn't
just reuse the subject agents as-is.

what I did instead:
- reused the existing chunking logic from rag/ingest.py, just without the chapter-heading
  detection — an upload is chunked page by page into its own FAISS index under
  rag/index/custom/<document_id>.faiss, keyed by document_id instead of subject+grade.
- added a generic document_tutor agent (agents/document_agent.py) that isn't tied to any
  subject — it retrieves from that document's own index and teaches with a subject-agnostic
  JSON schema.
- since there's no curriculum.py entry for a random upload, I added a one-time LLM call right
  after ingestion (extract_topics) that reads a sample of the document and generates its own
  ordered topic list. that list flows into the same custom_topics field the session API already
  had, so the existing topic-by-topic teaching + quiz + feedback loop just works unmodified.
- added a documents table in Postgres so uploads are saved per student and show up as a library,
  not just a one-off session.
- new dependency: python-multipart (FastAPI needs it for multipart file uploads, otherwise
  UploadFile just breaks at runtime with a confusing error).
- kept embeddings on the remote HF path for uploads too — after the memory-limit deploy issue
  earlier, no interest in loading a local embedding model just for this.

---

## Phase 1 — the agentic core (Supervisor, Memory, Tools, Reflection)

See `master_plan.md` for the full phase-by-phase spec and design rationale — the
short version of what shipped is in the README's "Key Design Decisions" section.
Highlights worth keeping here:

- `target_topic` was returned by the Supervisor since it first shipped but was
  never declared in the `LearningState` TypedDict, so LangGraph silently
  dropped it between graph steps — harmless until `revise_prerequisite` needed
  it to survive, caught by a mocked-graph test.
- The API layer originally assumed the topic taught in a turn was always the
  topic requested. A prerequisite redirect breaks that assumption twice over
  (mislabeled response, and the real requested topic silently marked
  "covered" without ever being taught) — fixed by comparing `target_topic`
  against the requested topic rather than trusting `next_action`, which gets
  overwritten to `"complete"` by the time the graph returns regardless of
  whether a mid-turn redirect happened.
- Reflection fails open: if the reflection LLM call itself errors (bad JSON,
  API error), the teaching output is accepted rather than blocking the turn.
  It's a quality gate, not a hard dependency.

---

## Phase 2 — Clerk auth

Wired via Clerk's own CLI (`clerk init`), which pulled its setup skill from
`clerk/skills` on GitHub and installed `@clerk/react`. Backend verification
uses `PyJWT` against the instance's public JWKS endpoint — no `CLERK_SECRET_KEY`
needed backend-side, since verifying a JWT only requires the issuer's public
signing keys, and the Clerk user id doubles directly as `students.student_id`
(no separate mapping table).

One non-obvious snag during local testing: the `<SignIn/>` component's OAuth
redirect briefly lands on `#/sso-callback` and looks stuck for several
seconds while Clerk completes the token exchange — it resolves on its own
and isn't an infinite loop, but it's easy to mistake for a hang the first
time you see it.
