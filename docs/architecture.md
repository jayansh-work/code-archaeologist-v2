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
Repository Query Engine
    ↓
Optional Grounded AI
    ↓
Frontend Investigation View
```

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

Each successful analysis returns an `analysis_id`. The API keeps repository metadata, summary statistics, and commit evidence in an in-memory store with a TTL (45 minutes) and a maximum session count. Restarting the API clears sessions. Expired IDs return a message asking the user to analyze again.

## Why queries do not reclone

`POST /query` looks up the session and runs the deterministic query engine against stored evidence. That keeps follow-up questions fast and avoids extra GitHub traffic.

## Evidence grounding

The query engine matches questions to intents (most-changed files, largest commits, contributors, recent activity, file history, author search, hash lookup, keyword search). Answers include the supporting commits.

If `GEMINI_API_KEY` is set, Gemini may rewrite the answer using only the retrieved evidence JSON. It is not given the whole repository. If the key is missing or the model call fails, deterministic search still works.

## Limitation of recent-commit analysis

The product analyzes the latest 30 commits (shallow clone). Totals, contributors, and file rankings describe that window only. The UI states this explicitly and does not label those figures as whole-repository totals.
