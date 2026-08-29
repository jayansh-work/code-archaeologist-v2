# Code Archaeologist

Software-forensics tool for exploring how a public GitHub repository evolved — using real commits, files, authors, timestamps, and diffs.

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
3. **Investigate** — ask natural-language questions. Evidence is retrieved first; Gemini explains it when `GEMINI_API_KEY` is set.

## Working capabilities

- Validate public `https://github.com/owner/repository` URLs
- Shallow-clone and extract real Git history
- Show commit hashes, messages, authors, timestamps, files, additions, and deletions
- Interactive repository-evolution graph (real commits only)
- Archaeologist notes from the analyzed window, with optional AI additions
- Expand a commit to inspect changed files
- Filter/search the commit list locally
- Ask Code Archaeologist in natural language after analysis
- Evidence-grounded Gemini answers when `GEMINI_API_KEY` is set
- Git analysis, graph, and history remain usable if Gemini is unavailable

## Architecture

See [docs/architecture.md](docs/architecture.md).

```
Browser → Next.js → FastAPI → Git analyzer → temporary clone → Git CLI
       → structured evidence → session store → query engine
       → optional grounded Gemini → investigation workspace
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

Optional Windows helper (opens two terminals):

```powershell
.\scripts\dev.ps1
```

## Environment variables

Copy examples; do not commit real `.env` files.

**Backend** (`backend/.env.example`)

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Enables Ask Code Archaeologist. Copy `backend/.env.example` to `backend/.env` and set the key. Git analysis still works when unset. |
| `GEMINI_MODEL` | Optional model id (default `gemini-2.0-flash`). |
| `CORS_ORIGINS` | Allowed browser origins. Local default is localhost/127.0.0.1 port 3000. |

**Frontend** (`frontend/.env.example`)

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | API origin. Falls back to `http://127.0.0.1:8000`. |
| `NEXT_PUBLIC_GITHUB_REPO_URL` | Header GitHub link. |

The app works without a Gemini key.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/info` | Product metadata and implemented capabilities |
| POST | `/analyze` | Clone and extract recent Git history |
| POST | `/query` | Retrieve evidence, then optionally ask Gemini |
| POST | `/notes` | Optional AI notes for an existing analysis |

## Analysis flow

1. Frontend validates the URL, then `POST /analyze`.
2. Backend validates again (this is the security boundary).
3. A temporary directory is created, the public repo is shallow-cloned, Git history is parsed, then the clone is deleted.
4. Structured evidence is stored under `analysis_id` (memory plus local JSON so API reloads keep the session).
5. The investigation workspace shows repository stats, the Ask bar, the evolution graph, notes, and commit history.

## Repository query flow

1. After a successful analysis, **Ask Code Archaeologist** appears.
2. `POST /query` uses the current `analysis_id`.
3. The query engine retrieves relevant commits and files first.
4. If `GEMINI_API_KEY` is set, Gemini explains only that evidence. Follow-up questions keep a short session history.
5. Findings cite real hashes. Clicking a citation selects the commit in the graph and history.

If Gemini is missing or fails, the UI shows that AI investigation is temporarily unavailable. Retrieved Git evidence stays visible.

Queries do not clone the repository.

## Security decisions

- No `shell=True` with user input
- HTTPS GitHub URLs only
- Timeouts on Git operations
- Temporary clones cleaned up after use
- CORS limited to local frontend origins
- API keys via environment only
- User-facing errors omit local filesystem paths

## Current limitations

- Public GitHub repositories only
- Latest 30 commits (shallow history)
- Sessions expire after 45 minutes (kept across API reloads on disk)
- No private-repo auth
- No full-file diffs in the UI (file paths and numstat only)
- Gemini answers are evidence-bounded; they cannot prove developer intent

## Roadmap

- Optional deeper history with explicit user consent
- Collapsible diff excerpts for selected files
- Additional Git hosts after the same validation model

## Demo instructions

1. Start backend, then frontend, with the commands above.
2. Open `http://127.0.0.1:3000`. The landing line is **Software has a history. Make it searchable.**
3. Paste `https://github.com/octocat/Hello-World` (or another small public repo).
4. Click **Analyze repository**.
5. Inspect repository stats, then **Repository evolution**. Click a commit node.
6. Read **Archaeologist notes**.
7. Ask **What are the most important changes in this repository?**
8. Click an evidence hash to select that commit in the graph and history.
9. Ask **Explain this commit to someone new to the codebase.**

For steps 7–9 to return an AI finding, set `GEMINI_API_KEY` in `backend/.env`. Without a key, Git evidence still appears and the graph remains usable.

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
