# Reviewer questions

Short answers that match the current implementation. Nothing here is a roadmap item.

## What problem are you solving?

Developers can inspect what code does today. It is harder to inspect how a repository evolved: what changed, when, who recorded it, which files kept being edited, and what evidence supports a claim. Code Archaeologist turns recent Git history into a searchable investigation workspace.

## How is this different from Cursor / Copilot / Claude?

Those tools help write or change code. Code Archaeologist investigates the history of an existing public repository. It clones recent Git history, shows real commits on an evolution graph, calculates same-file Butterfly relationships, and only then optionally asks a configured language model (via OpenRouter) to explain retrieved evidence. The AI does not replace the evidence. It organizes and explains it.

## Where does your data come from?

A temporary shallow `git clone` of a public `https://github.com/owner/repository` URL, then `git log --numstat` and `git log --name-status`. The clone is deleted in a `finally` block. Later questions use the stored analysis session, not another clone.

## Are the commits fake?

No. Hashes, authors, timestamps, messages, file paths, additions, and deletions come from Git. The UI does not invent demo commits.

## Why clone instead of using the GitHub API only?

Git already stores the history. Cloning with the Git CLI gives the same evidence a developer would get locally, without depending on GitHub REST pagination, token scopes, or a reconstructed history from API payloads.

## Why shallow clone?

A full clone of a large repository is slow and unnecessary for a live demo. `--depth` matches the analysis window (30 commits).

## Why only 30 commits?

The product is a recent-history investigation, not a whole-lifetime archive. Thirty commits keep clone time, graph size, and AI context bounded. The UI states that totals describe this window only.

## How do you avoid command injection?

The repository URL is validated first. Only `https://github.com/owner/name` is accepted. The normalized URL is passed as one argument in a `subprocess` argument array. User input is never concatenated into a shell command string.

## What does `shell=False` do?

`subprocess.run(..., shell=False)` executes `git` and its arguments directly. The Windows or Unix shell never parses the repository URL, so characters in a URL cannot become extra commands.

## Why FastAPI?

A small Python API is enough to validate URLs, run Git, store a bounded session, retrieve evidence, and call an OpenRouter-compatible chat model. FastAPI gives typed request/response models and clear error mapping without extra infrastructure.

## Why Next.js?

The investigation UI is a local web app: forms, an evolution graph, and inline findings. Next.js App Router and React are already in the project. The demo path uses a production `next start` build so the judge does not see a development overlay.

## Why React Flow?

The evolution graph needs pan, zoom, `fitView`, selectable nodes, and edges that wrap. React Flow already provides that. Commit nodes remain keyboard-focusable.

## How does the AI work?

Code Archaeologist retrieves repository evidence first. OpenRouter is used to access a configured language model that explains the retrieved evidence. The AI does not generate the underlying commit/file history.

## Do you send the entire repository to the model?

No. The model sees repository metadata, the history-window summary, and up to 12 retrieved commits with file-path lists and diff statistics. File contents and unified patches are not sent.

## What is evidence grounding?

Every finding is attached to the commits the query engine actually retrieved. The UI shows those commits. Clicking a citation selects that real commit in the graph and history.

## How do you reduce hallucination?

Retrieval happens first. The model is forbidden from inventing evidence. If evidence is thin, it must say so. If the model returns empty or invalid text, the UI shows the retrieved Git explanation and labels it as not an AI answer.

## What happens if the model lies?

The evidence panel still lists the real commits. A judge can click a hash and inspect the Git record. The product is designed so a fluent sentence cannot hide the underlying evidence.

## What happens without an API key?

Analysis, the graph, Butterfly, notes, and deterministic answers still work. The finding is labelled as retrieved from Git history, not AI.

## What happens if the AI provider is down?

Same fallback. Git evidence stays visible. The response reports `mode: ai-unavailable` with a reason such as `provider_error` or `rate_limited`.

## What exactly is Butterfly Effect?

A deterministic calculation over the analyzed window: take the selected commit's file paths, then find later and earlier analyzed commits that changed at least one of the same paths. Chronology is the `git log` newest-first order, not timestamp-string comparison.

## Does Butterfly prove causality?

No. It shows shared file history. The UI says so.

## Why do you call it a Butterfly Effect?

A small change can spread. If later saved changes edit the same files, the original change did not stay isolated — that area of the codebase continued evolving. The name is a metaphor for continuation, not a claim of causation.

## Can it analyze private repositories?

No. HTTPS `github.com` public repositories only. Credential prompts are disabled so a private repository fails quickly instead of hanging.

## Can it show full diffs?

No. It shows file-level change statistics: paths, additions, deletions, and change type where Git provides them. Unified patch hunks are not rendered.

## What are the current limitations?

Public GitHub only. Latest 30 commits. Sessions expire after 45 minutes. No private-repo auth. No full patch view. Rename tracking keeps the destination path. Butterfly is same-file, one level deep, capped at 8 links per direction. The AI provider can still rate-limit or reject requests.

## What would you build next?

Optional deeper history with explicit consent, collapsible diff excerpts for selected files, and additional Git hosts using the same validation model. None of those are implemented now.
