# Architecture

Code Archaeologist reconstructs recent Git history from a public GitHub repository and keeps that evidence connected to every finding.

```
Browser
    ↓
Next.js
    ↓
FastAPI
    ↓
Git Analyzer
    ↓
Temporary Clone
    ↓
Git CLI
    ↓
Structured Evidence
    ↓
Analysis Session Store
    ↓
Evidence retrieval
    ↓
Optional grounded Gemini
    ↓
Evolution flowchart + butterfly effect + notes + investigation workspace
```

Development uses `uvicorn --reload` and `next dev`. Anything demonstrated should use production mode instead — see `scripts/prepare-demo.ps1` and `scripts/demo.ps1` — so nothing recompiles or reloads mid-demo.

## Why Git CLI is used

Git already stores commits, authors, timestamps, and file-level diff statistics. The analyzer calls `git` with argument arrays (`subprocess.run(..., shell=False)`) so history comes from Git itself rather than a reconstructed parser of working-tree files. The current source tree cannot answer “what changed last week” on its own.

## Clone safety

`POST /analyze` accepts only `https://github.com/owner/repository` URLs. The backend rejects other hosts, schemes, credentials, extra path segments, and query strings. The normalized URL is passed as a single subprocess argument. User input is never concatenated into a shell command.

Clone uses:

- `--depth` equal to the commit window (30)
- `--single-branch`
- `--no-tags`
- `GIT_TERMINAL_PROMPT=0` and an empty credential helper so private repositories fail instead of hanging on a password prompt

Timeouts apply to clone and to follow-up Git commands.

## Why clone data is temporary

The clone exists only long enough to extract structured evidence. It lives in a Python temporary directory and is deleted in a `finally` block after success or failure. Query requests do not need the working tree.

## Analysis sessions

Each successful analysis returns an `analysis_id`. The API keeps repository metadata, summary statistics, commit evidence, and a short investigation history in memory and writes the same payload to `tmp/sessions`. Reloading the API does not drop a live investigation. Sessions still expire after 45 minutes and are capped by `max_sessions`. Expired IDs return a message asking the user to analyze again.

## Why queries do not reclone

`POST /query` looks up the session and runs the deterministic query engine against stored evidence. That keeps follow-up questions fast and avoids extra GitHub traffic.

## Evidence grounding

The query engine matches questions to intents (most-changed files, largest commits, contributors, recent activity, file history, author search, hash lookup, butterfly effect, overview, before-commit, keyword search). Answers include the supporting commits.

Retrieval is lightweight and lexical: commit messages, file paths, authors, short hashes, change magnitude, recency, and explicit user-selected context. There is no embedding model or vector store. When a question matches nothing lexically, retrieval returns a bounded, diverse sample — the most recent commits plus the highest-churn commits — and states that the window is limited, so the explanation layer never runs with zero evidence.

If `GEMINI_API_KEY` is set, Gemini may rewrite the answer using only the retrieved evidence JSON. It is not given the whole repository or any file contents. Analyzing a repository never calls Gemini; quota is reserved for explicit Ask questions. Identical questions in a session reuse a bounded in-memory cache. All Gemini calls in the process share one lock so Ask buttons cannot burst the free-tier quota. HTTP 429 is retried at most once, then the deterministic retrieval is returned.

The deterministic explanation is always attached to the response, so a failure at the model layer degrades the answer instead of emptying it. When AI does not contribute, the response reports `mode: ai-unavailable`, `ai_used: false`, and a reason (`not_configured`, `invalid_key`, `rate_limited`, `provider_error`), and the UI labels the text as retrieved from Git history rather than AI. A rate-limit notice is a capacity message, not a repository failure.

## Ask scope

UI filter state and AI context are separate by design. The main Ask bar is always repository-wide; selecting a commit in the flowchart or filtering the history file list changes only what is displayed. A commit or file becomes AI context only through an explicit inline action (Ask AI about this commit / file / butterfly). Those inline explanations are not recorded into the conversation history that main follow-up questions rely on.

## Butterfly effect

Butterfly is a deterministic historical relationship calculation over the analyzed window, implemented in `backend/app/services/butterfly.py` and mirrored in `frontend/lib/butterfly.ts` for the flowchart overlay. Both follow the same documented rules:

- the origin is one analyzed commit, located by hash
- chronology is the analyzed commit order, since `git log` returns newest-first; index 0 is newest
- "after this change" is the indices lower than the origin, "before this change" the indices higher
- a relationship exists only when another analyzed commit changed at least one of the origin's file paths
- at most 8 relationships per direction

Timestamp strings are never used for ordering, because commit times can carry different timezone offsets, be rewritten, or tie. Summary date ranges and before-commit queries use the same ordering rule.

Butterfly reports shared file history. It does not claim causation.

## Limitation of recent-commit analysis

The product analyzes the latest 30 commits (shallow clone). Totals, contributors, and file rankings describe that window only. The UI states this explicitly and does not label those figures as whole-repository totals.

Change data is file-level: paths, additions, deletions, and change type. Full unified patch hunks are not extracted or rendered. Rename notation from Git (`old.py => new.py` and `src/{old => new}/file.py`) is resolved to the destination path.
