# Live demo guide

Tested against the public repository:

`https://github.com/jayansh-work/code-archaeologist-v2`

The live analysis on 30 Aug 2026 returned **10 real commits**, **80 changed files**, and **1 contributor** in the latest-30 window. Those numbers will move as this repository gains commits. The commit hashes below were present in that window.

## Best Butterfly commit

**Select `6b34b50`** — `feat: add connected investigation workspace with evolution graph`

Why this one, from the actual analyzed window:

- It is an older commit in the graph, not the newest tip.
- It changed the investigation workspace, Gemini, notes, and query engine.
- **5 later analyzed commits** reused those files: `cd99136`, `5d89474`, `7596d99`, `94472c6`, `edc84e8`.
- That later set includes the Butterfly feature itself and the inline-AI placement fix, so the After this change list is visually obvious.

Backup if you want the Butterfly *feature* as the origin: **`94472c6`** (`feat: add butterfly effect and a wrapping evolution flowchart`). It has one later continuation (`edc84e8`) on `frontend/components/ButterflyPanel.tsx` and related files.

Do not pick `1471803` (only `.gitignore`) or the newest commit (`edc84e8` has no later continuation).

## Tested questions

These were actually sent to `POST /query` after analyzing the self-repository. After a short rate-limit window, Gemini returned `mode: grounded-ai` with `ai_used: true` and citations that matched real analyzed hashes.

Use these in the main Ask bar (repository-wide):

1. **What are the most important changes in the analyzed history?**
   Gemini cited `7f37406` (investigation workspace), `7463189` (analysis API), `6b34b50` (evolution graph), and `94472c6` (Butterfly flowchart).
2. **How did the AI integration evolve?**
   Gemini traced Gemini from `7463189` through the workspace (`6b34b50`), missing-key copy (`cd99136`), and inline answers (`edc84e8`).
3. **Which files changed the most?**
   Returned file-level totals for this window (`frontend/app/globals.css`, `backend/app/services/query_engine.py`, `backend/app/services/gemini.py`, `frontend/components/InvestigationApp.tsx`, `README.md`, and lockfiles). The first live attempt hit a Gemini rate limit and still showed this ranking as retrieved Git evidence.

Useful extras that also returned real evidence:

- **Which contributors appear most in this window?**
- **Explain this repository to someone new to the project.**

After selecting `6b34b50`, use the Butterfly panel button **Ask AI about this butterfly** rather than typing a butterfly question in the main bar. A live inline query for that commit returned `ai_used: true` and named the later commits `cd99136`, `5d89474`, `7596d99`, `94472c6`, and `edc84e8`. The main bar is repository-wide and will not silently use the selected commit.

## 30-second emergency demo

1. Open `http://127.0.0.1:3000`.
2. Say: "Software has a history. Code Archaeologist makes that history searchable."
3. Paste `https://github.com/jayansh-work/code-archaeologist-v2` and analyze.
4. Point at the real commit list and stats. Say: "These are analyzed Git commits, not fake demo data."
5. Open Repository evolution. Select **`6b34b50`**.
6. Point at **After this change**. Say: "Later work kept editing the same files. That is shared history, not claimed causation."

## 90-second normal demo

Do the 30-second path, then:

7. Click **Ask AI about this butterfly**. The answer stays in the Butterfly panel.
8. In the main Ask bar, type: **What are the most important changes in the analyzed history?**
9. Click a cited hash. The matching commit becomes selected.

Say: "The AI organizes the evidence. It does not replace it."

## 3-minute full demo

1. Open the app. Mention How it works if a judge wants the pipeline first.
2. Analyze `https://github.com/jayansh-work/code-archaeologist-v2`.
3. Show repository statistics and the "latest 30 commits" caveat.
4. Open Repository evolution. Oldest work starts top-left; arrows point toward newer commits.
5. Select **`6b34b50`**. Show author, timestamp, files, additions/deletions.
6. Show Butterfly Effect. Emphasize **After this change**. Read the caveat out loud.
7. Ask AI about that butterfly. Keep the answer under the button.
8. Main Ask: **How did the AI integration evolve?**
9. Follow-up: **Which commit is the strongest evidence for that?**
10. Click a citation. Show the graph node selected.
11. Optional: **Which files changed the most?** then filter history by a related file.

If a judge clicks around, let them. Main Ask stays repository-wide. Inline Ask stays under the control that asked.

## What to say

- "These are the analyzed commits, not fake demo data."
- "Butterfly Effect shows whether later changes continued touching the same area of the codebase. It shows historical relationships, not claimed causation."
- "The AI does not replace the evidence. It organizes and explains the evidence."

## Fallback if Gemini is unavailable or rate-limited

Do not apologize or stall.

1. Analyze the self-repository. The graph and notes still appear.
2. Select `6b34b50` and walk Butterfly. That calculation is deterministic and does not need Gemini.
3. Ask **Which files changed the most?** The retrieved Git ranking still appears, labelled as retrieved from Git history, not AI.
4. Click **Retry with AI** only if you have a few seconds. If it stays rate-limited, keep going with evidence.

The free Gemini tier is easy to exhaust while rehearsing. Git evidence is the demo. AI is the explanation layer.

## Fallback if GitHub is slow

1. If a clone times out, say so and retry once.
2. Use `https://github.com/octocat/Hello-World` only to prove the pipeline against a tiny public repo. It has almost no Butterfly continuation — do not use it as the headline demo.
3. If the network is down, do not pretend. Show How it works and Architecture, then retry the self-repository.

## Startup for judging

```powershell
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
powershell -ExecutionPolicy Bypass -File scripts\prepare-demo.ps1
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

App: `http://127.0.0.1:3000`  
API: `http://127.0.0.1:8000/health`

Stop only the processes the demo script started:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1
```
