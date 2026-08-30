# Code Archaeologist

Software-forensics tool for exploring how a public GitHub repository evolved — using real commits, changed files, authors, timestamps, and diff statistics.

## What it is

Code Archaeologist is a local developer tool. You paste a public GitHub URL, the app clones a shallow copy, extracts recent Git history, then lets you inspect that evidence and ask questions about it.

The AI does not replace the evidence. It organizes and explains retrieved Git history. Without an API key, analysis, the graph, and commit evidence still work.

## Problem

Developers can inspect what code does today. It is harder to answer:

- What changed?
- When did it change?
- Who changed it?
- Which files evolved together?
- What evidence exists for a change?

## Solution

The product has three layers:

1. **Excavate** — analyze a public GitHub repository (latest 30 commits).
2. **Visualize** — inspect an interactive evolution graph of those commits.
3. **Investigate** — ask natural-language questions. Evidence is retrieved first; OpenRouter is used only to explain that evidence when `OPENROUTER_API_KEY` is set.

## Working capabilities

- Validate public `https://github.com/owner/repository` URLs
- Shallow-clone and extract real Git history
- Show commit hashes, messages, authors, timestamps, changed file paths, additions, and deletions
- Interactive repository-evolution flowchart (real commits only, arrows wrap to stay on the page)
- Butterfly effect: later commits that reused the same files as a selected change
- Archaeologist notes from the analyzed window (deterministic Git evidence only; AI requests are reserved for Ask Code Archaeologist)
- Expand a commit to inspect changed files
- Filter/search the commit list locally
- Ask Code Archaeologist in natural language after analysis
- Evidence-grounded AI answers when `OPENROUTER_API_KEY` is set
- Git analysis, graph, and history remain usable if the AI provider is unavailable

The UI shows **file-level change statistics** (paths, additions, deletions, change type). It does
not render full unified patch hunks.

## Ask scope

Two deliberately separate things:

| Control | Scope | Conversation history |
| --- | --- | --- |
| **Ask Code Archaeologist** (main bar) | Whole analyzed repository | Recorded, so follow-ups work |
| **Ask AI about this commit** | That commit only | Not recorded |
| **Explain this file** | That file only | Not recorded |
| **Ask AI about this butterfly** | That commit's butterfly trace | Not recorded |

Selecting a commit in the flowchart or typing in the history file filter changes **only what you
see**. Neither becomes AI context, so a general question is never silently biased by whatever
happens to be highlighted.

Inline answers appear directly under the control that asked, so a local question never scrolls you
somewhere else. Asking about the same commit or file from two places (the details panel and the
history row) shares one result rather than firing two requests.

## Butterfly effect semantics

Butterfly is a deterministic Git calculation, not a prediction:

1. Take the selected commit.
2. Take the file paths it changed.
3. Find analyzed commits **after** it that changed at least one of the same paths.
4. Find analyzed commits **before** it that had already changed those paths.

Chronology comes from the order `git log` returns, never from comparing timestamp strings, because
commit timestamps can carry different timezone offsets, be rewritten, or tie.

This shows shared file history. It does **not** prove one change caused another.

## Architecture

See [docs/architecture.md](docs/architecture.md).

```
Browser → Next.js → FastAPI → Git analyzer → temporary clone → Git CLI
       → structured evidence → session store → query engine
       → optional grounded AI explanation → investigation workspace
```

## Tech stack

- **Frontend:** Next.js, React, TypeScript, CSS, React Flow
- **Backend:** Python, FastAPI, Uvicorn, Pydantic
- **History:** system Git CLI via `subprocess` argument arrays

No database, Redis, Docker, or auth in this version.

## Requirements

- Git
- Python 3.11+ (developed with 3.14)
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- Network access to GitHub for cloning public repositories

## Installation

From the repository root:

```powershell
cd backend
uv sync --group dev
```

```powershell
cd frontend
npm install
```

## Running backend

```powershell
cd backend
uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On some Windows setups, Application Control can block `uvicorn.exe`. `python -m uvicorn` is the tested command.

## Running frontend

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open: `http://127.0.0.1:3000`

Optional Windows helper (opens two terminals, refuses to start if a port is busy):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

## Demo mode (recommended for anything being presented)

`next dev` recompiles on every keystroke and shows a development error overlay. Neither belongs in
front of an audience, and rebuilding `.next` while a dev server holds it is what produces errors
like `Cannot find module './833.js'`. Use production mode instead.

```powershell
# 1. Check the machine. Never prints your API key.
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1

# 2. Tests, lint, typecheck, production build. Stops at the first failure.
powershell -ExecutionPolicy Bypass -File scripts\prepare-demo.ps1

# 3. Start: backend without --reload, frontend from the production build.
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1

# 4. Stop only the processes step 3 started.
powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1
```

| Script | What it does |
| --- | --- |
| `scripts\doctor.ps1` | PASS/WARN/FAIL table: Git, Python, uv, Node, npm, ports 8000/3000, `backend\.env`, whether an OpenRouter key is configured (never its value), dependencies, build freshness, and live `/health` |
| `scripts\prepare-demo.ps1` | `uv run pytest -q`, `npm run lint`, `npm run typecheck`, `npm run build`. Prints `DEMO BUILD READY` only if all four pass |
| `scripts\demo.ps1` | Verifies ports 8000 and 3000 are free, starts `uvicorn` without `--reload` and `next start`, waits for both to answer, records its own PIDs in `tmp\demo\pids.json` |
| `scripts\stop-demo.ps1` | Stops only the recorded PIDs, re-checking each one's start time so a recycled PID is never killed |

No script ever terminates a process it did not start. If a port is occupied, you get the PID and
process name and are asked to close it yourself.

### If the frontend build gets into a bad state

`.next` must not be deleted while a Next process is using it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1   # confirm port 3000 is free
Remove-Item -Recurse -Force frontend\.next
powershell -ExecutionPolicy Bypass -File scripts\prepare-demo.ps1
```

## Environment variables

Copy examples; do not commit real `.env` files.

**Backend** (`backend/.env.example`)

| Variable | Purpose |
| --- | --- |
| `OPENROUTER_API_KEY` | Enables Ask Code Archaeologist. Copy `backend/.env.example` to `backend/.env` and set the key. Git analysis still works when unset. |
| `OPENROUTER_MODEL` | OpenRouter model slug (default `openai/gpt-4o-mini`). Change this without editing code. |
| `OPENROUTER_FALLBACK_MODELS` | Optional short comma-separated fallback slugs if the primary model is unavailable. |
| `OPENROUTER_APP_NAME` | Optional `X-Title` attribution header (default `Code Archaeologist`). |
| `OPENROUTER_SITE_URL` | Optional. If set, sent as `HTTP-Referer`. Do not invent a public domain. |
| `CORS_ORIGINS` | Allowed browser origins. Local default is localhost/127.0.0.1 port 3000. |

**Frontend** (`frontend/.env.example`)

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | API origin. Falls back to `http://127.0.0.1:8000`. |
| `NEXT_PUBLIC_GITHUB_REPO_URL` | Header GitHub link. |

The app works without an OpenRouter key. Code Archaeologist retrieves repository evidence first. OpenRouter is used to access a configured language model that explains the retrieved evidence. The AI does not generate the underlying commit/file history. OpenRouter does not remove rate limits; free `:free` model slugs can still be limited.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/info` | Product metadata and implemented capabilities |
| POST | `/analyze` | Clone and extract recent Git history |
| POST | `/query` | Retrieve evidence, then optionally ask the configured AI model |
| POST | `/notes` | Optional AI notes for an existing analysis |

## Analysis flow

1. Frontend validates the URL, then `POST /analyze`.
2. Backend validates again (this is the security boundary).
3. A temporary directory is created, the public repo is shallow-cloned, Git history is parsed, then the clone is deleted.
4. Structured evidence is stored under `analysis_id` (memory plus local JSON so API reloads keep the session).
5. The investigation workspace shows repository stats, the Ask bar, the evolution flowchart, butterfly effect, notes, and commit history.

## Repository query flow

1. After a successful analysis, **Ask Code Archaeologist** appears.
2. `POST /query` uses the current `analysis_id`.
3. The query engine retrieves relevant commits and files first. If nothing matches the wording, it
   returns a bounded, diverse sample (recent plus highest-churn commits) rather than sending the
   model no context at all.
4. If `OPENROUTER_API_KEY` is set, the configured model explains only that evidence. Follow-up questions keep a short
   session history; inline explanations deliberately do not.
5. Findings cite real hashes. Clicking a citation selects the commit in the graph and history.

Queries do not clone the repository.

### When AI is unavailable

The response always carries the deterministic Git explanation, so the finding panel is never blank.
It is labelled `retrieved from Git history, not AI` and reports why:

| Reason | Meaning |
| --- | --- |
| `not_configured` | No key in `backend/.env` |
| `invalid_credentials` | The AI provider rejected the configured credentials |
| `insufficient_credits` | The AI provider reported insufficient credits |
| `model_unavailable` | The configured model (and short fallback list) was unavailable |
| `provider_timeout` | The AI request timed out |
| `rate_limited` | Request limit reached. Git evidence stays on screen. Use **Retry AI** only if you want another model call. |
| `provider_error` | The model returned nothing usable |

Analyzing a repository does **not** call the AI provider. Identical questions in
the same session reuse a bounded in-memory cache. Concurrent Ask buttons share one
provider slot. On HTTP 429 the API waits once if Retry-After is short, retries once,
then serves the retrieved Git explanation. The UI labels that as AI request limit
reached, not as a repository failure. OpenRouter does not magically remove rate limits.

Requests never block each other's UI: the flowchart, commit history, and notes stay usable while a
query is running.

## Security decisions

- Git runs through `subprocess` argument arrays with `shell=False`; no `shell=True` anywhere
- The repository URL is never interpolated into a shell command string
- HTTPS `github.com` URLs only; no other hosts, protocols, or local paths
- URLs containing credentials are rejected
- `GIT_TERMINAL_PROMPT=0` and an empty credential helper, so a private repository fails fast
  instead of hanging on a password prompt
- Timeouts on every Git operation, and a wall-clock budget on the AI call chain
- Temporary clones removed in a `finally` block
- CORS limited to local frontend origins
- API keys read from the environment only; `.env` is git-ignored and never persisted into sessions
- User-facing errors omit local filesystem paths and never include stack traces

## Current limitations

- Public GitHub repositories only
- Latest 30 commits (shallow history), so all statistics describe that window, not the repository
- Sessions expire after 45 minutes (kept across API reloads on disk)
- No private-repo auth
- File-level change statistics only. Full unified patch hunks are not rendered
- Rename tracking preserves the destination path; the previous path is parsed but not displayed
- Butterfly relationships are same-file only, one level deep, capped at 8 per direction
- AI answers are evidence-bounded; they cannot prove developer intent
- AI providers can still rate-limit or reject requests; Git evidence remains the fallback

## Roadmap

Not implemented yet:

- Optional deeper history with explicit user consent
- Collapsible diff excerpts for selected files
- Additional Git hosts after the same validation model

## Demo guide

See [docs/demo.md](docs/demo.md) for tested 30-second, 90-second, and 3-minute runs, including the
exact repository, the best butterfly commit, and questions that were actually verified.

Reviewer questions and answers: [docs/reviewer-qa.md](docs/reviewer-qa.md).

## Tests

```powershell
cd backend
uv run pytest
```

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```
