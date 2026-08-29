# Code Archaeologist

Software-forensics tool for exploring how a public GitHub repository evolved — using real commits, files, authors, timestamps, and diffs.

## What it is

Code Archaeologist is a local developer tool. You paste a public GitHub URL, the app clones a shallow copy, extracts recent Git history, then lets you inspect that evidence and ask questions about it.

The AI does not replace the evidence. It organizes and explains the evidence. Without an API key, repository search still works.

## Problem

Developers can inspect what code does today. It is harder to answer:

- What changed?
- When did it change?
- Who changed it?
- Which files evolved together?
- What evidence exists for a change?

## Solution

The product has two stages:

1. **Excavate** — analyze a public GitHub repository (latest 30 commits).
2. **Investigate** — ask questions against the stored evidence for that analysis. The repository is not cloned again.

## Working capabilities

- Validate public `https://github.com/owner/repository` URLs
- Shallow-clone and extract real Git history
- Show commit hashes, messages, authors, timestamps, files, additions, and deletions
- Compact repository summary for the analyzed window
- Expand a commit to inspect changed files
- Filter/search the commit list locally
- Ask the repository (deterministic search, no API key required)
- Optional Gemini answers grounded in retrieved evidence when `GEMINI_API_KEY` is set

## Architecture

See [docs/architecture.md](docs/architecture.md).

```
Browser → Next.js → FastAPI → Git analyzer → temporary clone → Git CLI
       → structured evidence → in-memory session → query engine
       → optional grounded AI → investigation view
```

## Tech stack

- **Frontend:** Next.js, React, TypeScript, CSS
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
| `GEMINI_API_KEY` | Optional. Enables grounded AI answers. |
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
| POST | `/query` | Search stored evidence for an analysis session |

## Analysis flow

1. Frontend validates the URL, then `POST /analyze`.
2. Backend validates again (this is the security boundary).
3. A temporary directory is created, the public repo is shallow-cloned, Git history is parsed, then the clone is deleted.
4. Structured evidence is stored in memory under `analysis_id`.
5. The investigation workspace renders real commits and a summary of the analyzed window.

## Repository query flow

1. After a successful analysis, **Ask the repository** appears.
2. `POST /query` uses the current `analysis_id`.
3. The query engine classifies the question and searches stored evidence.
4. Findings are shown with clickable evidence that opens the matching commit.

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
- In-memory sessions (lost on restart, expire after 45 minutes)
- No private-repo auth
- No full-file diffs in the UI (file paths and numstat only)
- Optional AI is evidence-bounded; it cannot prove developer intent

## Roadmap

- Optional deeper history with explicit user consent
- Collapsible diff excerpts for selected files
- Durable session storage if multi-user hosting is needed
- Additional Git hosts after the same validation model

## Demo instructions

1. Start backend, then frontend, with the commands above.
2. Open `http://127.0.0.1:3000`.
3. Paste `https://github.com/octocat/Hello-World` (or another small public repo).
4. Click **Analyze repository**.
5. Inspect the summary and expand a commit.
6. Ask **Which files changed the most?**
7. Ask **Find commits mentioning README**.
8. Click an evidence row to open that commit.

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
