# Risk Assessment Workbench

A prototype for a bank's Financial Crimes Risk Management (FCRM) function: a single governed
workflow that carries a proposed change (new product, feature, vendor, geography, or customer
segment) from intake → RAG-informed multi-agent risk assessment → analyst decision, replacing the
email/Word/Excel/SharePoint trail the real process currently runs on.

## What's here

- **Frontend**: a static HTML/CSS/JS page (no build step, Tailwind via CDN), gated behind login,
  with three tabs — **Upload**, **Result** (Agent Analysis stacked above the Final Result), and
  **All Jobs** — plus a Job Detail page reachable from All Jobs.
- **Backend**: a Python/FastAPI service with basic username/password auth, a RAG lookup over an
  authored FCRM knowledge base, three independent LLM-based risk assessors (one per specialist
  prompt) fanned out per case, and a master agent (judge) that merges their opinions into one
  final result.
- **Knowledge base**: eight markdown articles we authored on core FCRM topics, chunked (with a
  word-count ceiling + overlap for any oversized section) and embedded into a local Chroma vector
  store.
- **Persistence**: SQLite (`backend/workbench.db`) — cases, decisions, users, and sessions all
  survive a backend restart.

## Directory layout

```
DDA/
├── index.html, app.js, styles.css     # static frontend (auth screen, Upload / Result / All Jobs tabs, Job Detail page)
├── knowledge/*.md                     # 8 authored FCRM knowledge articles (RAG corpus)
├── requirements.txt                   # fastapi, uvicorn, chromadb, httpx, python-dotenv, ...
├── .env.example                       # provider API key template (copy to .env)
├── scripts/
│   ├── test_backend.py                # end-to-end smoke test: auth flow + case pipeline + scope guardrail
│   ├── test_providers_stub.py         # exercises the real provider HTTP wire format against a local stub
│   └── eval_retrieval.py              # labeled query set scored against the retriever (precision/hit-rate eval)
├── .claude/launch.json                # "static-preview" (port 4173) + "api-server" (port 8000) configs
└── backend/
    ├── main.py                        # FastAPI app, CORS, startup-time KB ingestion
    ├── config.py                      # paths, CORS origins, provider specs, chunking params, per-slot provider/temperature map
    ├── models.py                      # Pydantic schemas (Case, Assessment, JudgeVerdict, CaseResult, auth, ...)
    ├── auth.py                        # PBKDF2 password hashing + opaque session-token helpers
    ├── deps.py                        # get_current_user() dependency (reads the session token)
    ├── store.py                       # SQLite-backed store: cases, users, sessions
    ├── routers/
    │   ├── auth.py                     # POST /api/auth/signup, /login, /reset-password, /logout, GET /me
    │   ├── cases.py                    # POST/GET/DELETE /api/cases, GET /api/cases (list)
    │   ├── agents.py                   # POST /api/cases/{id}/run, GET /api/cases/{id}/agents
    │   └── decisions.py                # POST /api/cases/{id}/decision
    ├── rag/
    │   ├── chunker.py                  # heading-based markdown chunking, with a word-count ceiling + overlap
    │   ├── ingest.py                   # builds/loads the Chroma collection from knowledge/*.md
    │   └── retriever.py                # query_knowledge_base(query_text, k) -> relevant chunks
    ├── llm/
    │   ├── providers.py                # HTTP clients for Groq (x3 keys), xAI Grok, OpenAI, Anthropic + provider_status()
    │   ├── client.py                   # complete(slot, system, user, mock_fn) -> LLMResult; live-with-mock-fallback
    │   └── mock_llm.py                 # deterministic offline fallback (keyword risk heuristic + majority-vote judge)
    └── agents/
        ├── scope_guard.py              # intake gatekeeper: is this submission in scope for this bank's FCRM review?
        ├── assessor.py                 # one independent FCRM-analyst LLM call per ensemble slot
        └── master_agent.py             # runs the scope guard, then the 3 child agents, then a judge call
```

## Architecture: how a case flows through the system

1. **Auth gate** — the whole app sits behind login. A user signs up with username + email +
   password (`POST /api/auth/signup`), or resets a forgotten password by email with no
   verification step (`POST /api/auth/reset-password`, by design for this prototype). Logging in
   with a username that doesn't exist returns a 404 so the frontend can prompt "sign up instead."
   A successful login/signup returns an opaque session token (`backend/auth.py`, PBKDF2-hashed
   passwords, tokens stored in a `sessions` table — not a signed/stateless JWT); the frontend
   keeps it in `localStorage` and sends it as a bearer token on every request, checked by
   `backend/deps.py:get_current_user()`. Logging out — and logging back in as a different session
   — clears all cached Upload/Agent/Result state client-side, so each login starts fresh; past
   work is still reachable via All Jobs.
2. **Upload tab** — product owner fills in title / change type / description and attaches
   supporting files, then submits. `POST /api/cases` creates a `Case` row in SQLite with
   `status="submitted"`, recording the creator from the logged-in session. Clicking "New Request"
   clears all cached Upload/Agent/Result state before starting the next submission.
3. **Scope guardrail** — before anything else, `POST /api/cases/{id}/run` calls
   `agents/scope_guard.py:check_scope()`, which asks an LLM (falling back to a deterministic
   keyword check) whether the submission is actually a plausible bank product/feature/vendor/
   geography/customer-segment/process change worth an FCRM risk review for *this* bank. If not,
   the pipeline stops right there — all 3 child agents and the master agent are marked `skipped`,
   no further LLM calls are made, and `CaseResult.out_of_scope=True` with a `scope_reason`. This
   keeps the ensemble scoped to this bank's financial-crime risk problem only, rather than acting
   as a general-purpose LLM endpoint.
4. **RAG lookup** — for in-scope cases, the pipeline builds a query from the case's title/
   description/filenames and calls `rag/retriever.py`, which searches the Chroma collection built
   from `knowledge/*.md` (embedded with Chroma's bundled local `all-MiniLM-L6-v2` model — no API
   key needed for embeddings). `rag/chunker.py` splits each article on `##` headings, then further
   splits any section over `CHUNK_MAX_WORDS` (180) into overlapping word-count windows
   (`CHUNK_OVERLAP_WORDS=40`) so one oversized section can never become a single, low-precision
   retrieval chunk — retrieval quality against this corpus is checked by `scripts/eval_retrieval.py`
   (see Testing below).
5. **Three independent child agents** — `agents/assessor.py` is called once per ensemble slot
   (`agent1`, `agent2`, `agent3`), each with its own dedicated Groq API key/rate limit. What makes
   them independent is each agent's own **specialist system prompt** (`SLOT_SPECIALISTS` in
   `assessor.py`): agent1 is a Sanctions & AML Typology Specialist, agent2 a Regulatory & CDD
   Specialist, agent3 a Third-Party & Geographic Risk Specialist — each given the case plus the
   retrieved policy excerpts, and each independently returning a structured `Assessment`
   (risk_rating, recommendation, summary, conditions, rationale) — this is the "get the opinion"
   step.
6. **Master Agent (judge)** — `agents/master_agent.py` sends all three child-agent assessments to
   a fourth LLM call (the judge, also provider-backed) which picks or synthesizes the single final
   verdict. Risk ratings are also tallied as a vote count (`CaseResult.votes`) so a human reviewer
   can see how much the three child agents agreed.
7. **Result tab** — after submitting, the user lands here and sees, stacked on one page: **Agent
   Analysis** (each child agent's status/output as the pipeline runs) above the **Final Result**
   (the merged `CaseResult` — risk rating, recommendation, summary, conditions, vote breakdown, and
   judge rationale). An out-of-scope case shows an "Out of Scope" badge and the scope guard's
   reason instead, with no Accept/Reject decision needed. Re-opening the Result tab (e.g. after
   approving from Job Detail) re-fetches from the API so it never shows a stale decision.
8. **Decision** — the analyst clicks Accept/Reject; `POST /api/cases/{id}/decision` records it
   (only allowed once `status == "complete"`), capturing the approver's name and a timestamp from
   the logged-in session.
9. **All Jobs tab / Job Detail page** — `GET /api/cases` lists every submitted case (title, type,
   status, risk rating, decision, timestamp). Clicking a job opens a Job Detail page that shows,
   stacked on one page, the original request, the agent processing, and the result — including who
   approved it and when, persisted so reopening it later still shows the same approver/timestamp.
   A case can also be deleted (`DELETE /api/cases/{id}`).

## LLM strategy: real providers with automatic mock fallback

The one seam every agent call goes through is `backend/llm/client.py:complete()`. For a given
ensemble slot it looks up that slot's assigned provider (`backend/config.py:SLOT_PROVIDERS`) and:

- If the provider has an API key configured **and** the live call succeeds → returns the real
  response (`mode="live"`).
- If the key is missing, or the call errors/times out → **silently falls back** to the
  deterministic mock (`mode="mock"`) so the pipeline never breaks because a provider is
  unavailable.

This means the app runs fully offline out of the box (everything mocked) and gets progressively
more "real" as you add keys to `.env` — no code changes required, and partial configuration (e.g.
only `GROQ_API_KEY_1`) is fine; only the slots assigned to that provider go live.

Current default: all 5 slots (`agent1`→`groq1`, `agent2`→`groq2`, `agent3`→`groq3`,
`master_agent`→`groq1`, `scope_guard`→`groq2`) run on Groq (groq.com — OpenAI-compatible fast
inference; not the same service as xAI's "Grok", despite the similar name) using model
`openai/gpt-oss-120b`, with each of the 3 child agents on its own dedicated API key
(`GROQ_API_KEY_1`/`_2`/`_3`) for independent rate-limit headroom. That model is a reasoning model —
`reasoning_effort: "low"` is set on Groq's `OpenAICompatProvider` calls so enough of
`LLM_MAX_TOKENS` (2000) is left for the actual JSON answer instead of being consumed entirely by
its internal reasoning trace. The unused `grok`/`openai`/`anthropic` provider specs are kept in
`PROVIDER_SPECS` (not deleted) so adding those keys back later is a `.env`-only change.

`backend/llm/mock_llm.py` is kept intentionally (not deleted) as the offline fallback and test
harness: a keyword-based risk heuristic (`HIGH_RISK_KEYWORDS` / `MEDIUM_RISK_KEYWORDS`, e.g.
"cross-border", "sanction", "cash", "vendor", "PEP") with a small per-slot severity nudge so the
three mock opinions plausibly disagree, plus a majority-vote mock judge — exercising the same
code paths a real disagreement would.

## Knowledge base topics (`knowledge/`)

AML program overview, KYC/CDD/EDD, sanctions screening, the new-product/change risk assessment
framework, third-party & vendor risk, cross-border payments risk, SAR filing, and customer risk
segmentation — authored specifically to give the RAG step something real to retrieve against.
Chunked via `rag/chunker.py` (heading splits + a 180-word ceiling with 40-word overlap for any
oversized section — none of the current 32 chunks are affected, since they all max out around
116 words; the ceiling exists for future, longer documents).

## API reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/signup` | Create a user (username, email, password) |
| POST | `/api/auth/login` | Log in; 404 if the username doesn't exist (prompts signup) |
| POST | `/api/auth/reset-password` | Reset a password by username/email, no verification step |
| GET | `/api/auth/me` | Current logged-in user |
| POST | `/api/auth/logout` | Invalidate the current session token |
| POST | `/api/cases` | Create a case (multipart: `title`, `change_type`, `description`, `files[]`) |
| GET | `/api/cases` | List all cases (for the All Jobs tab) |
| GET | `/api/cases/{id}` | Fetch a case's status + final result + decision |
| DELETE | `/api/cases/{id}` | Delete a case |
| DELETE | `/api/cases` | Bulk-delete all cases (used by test/cleanup scripts) |
| POST | `/api/cases/{id}/run` | Run the RAG + 3-child-agent + master-agent (judge) pipeline |
| GET | `/api/cases/{id}/agents` | Fetch recorded per-agent results (for reopening a past job) |
| POST | `/api/cases/{id}/decision` | Record `approved`/`rejected` + approver name/timestamp (only once `status == complete`) |
| GET | `/api/health` | Health check |
| GET | `/api/llm/providers` | Which providers are configured (`configured: true/false`) — no keys returned |

## Running it locally

```bash
# one-time setup
cd /Users/rakesh.yakkundi/Documents/DDA
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optionally fill in GROQ_API_KEY_1/2/3, GROK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY

# terminal 1 — backend
source .venv/bin/activate && uvicorn backend.main:app --reload --port 8000

# terminal 2 — frontend
python3 scripts/dev_server.py   # static server with no-store caching, port 4173
```

Then open `http://localhost:4173`, sign up, and log in. With no `.env` keys, every LLM call falls
back to the mock — the full pipeline still runs end-to-end.

## Testing

```bash
source .venv/bin/activate
python3 -m scripts.test_providers_stub   # provider HTTP wire-format, no real keys needed
python3 -m scripts.eval_retrieval        # retrieval quality: hit-rate of the retriever against a labeled query set
uvicorn backend.main:app --port 8000 &
python3 -m scripts.test_backend          # full pipeline smoke test: auth + case pipeline + scope guardrail
```

`test_backend.py`'s "mock ensemble produces varied ratings" assertion is documented as mock-mode
only — with real Groq keys loaded, the 3 live specialist models can legitimately agree, which is
expected and not a regression.

## Known limitations (by design, for this prototype stage)

- Basic auth only — PBKDF2-hashed passwords and opaque session tokens, no password-reset
  verification email, no role-based permissions (any logged-in user can decide or delete any
  case).
- No real document parsing — uploaded file *names* are recorded and used as RAG query signal;
  file *contents* aren't extracted or read.
- CORS is hardcoded to `localhost:4173` — update `CORS_ORIGINS` in `backend/config.py` for any
  other frontend origin.
- SQLite is fine for a single-instance prototype; a multi-instance deployment would need a real
  database server.
