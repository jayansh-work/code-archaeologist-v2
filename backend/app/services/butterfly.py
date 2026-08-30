"""Butterfly effect: later commits that reused files from an earlier change."""

from __future__ import annotations

from app.models import CommitEvidence, EvidenceItem, QueryResponse


def _shared_paths(left: CommitEvidence, right: CommitEvidence) -> list[str]:
    left_paths = {item.path for item in left.files}
    shared: list[str] = []
    seen: set[str] = set()
    for item in right.files:
        if item.path in left_paths and item.path not in seen:
            seen.add(item.path)
            shared.append(item.path)
    return shared


def _to_evidence(commit: CommitEvidence, note: str | None = None) -> EvidenceItem:
    return EvidenceItem(
        hash=commit.hash,
        short_hash=commit.short_hash,
        author=commit.author,
        timestamp=commit.timestamp,
        message=commit.message,
        additions=commit.additions,
        deletions=commit.deletions,
        files=[item.path for item in commit.files],
        note=note,
    )


def compute_butterfly(
    commits: list[CommitEvidence],
    origin: CommitEvidence,
) -> tuple[list[tuple[CommitEvidence, list[str]]], list[tuple[CommitEvidence, list[str]]]]:
    upstream: list[tuple[CommitEvidence, list[str]]] = []
    downstream: list[tuple[CommitEvidence, list[str]]] = []
    for commit in commits:
        if commit.hash == origin.hash:
            continue
        shared = _shared_paths(origin, commit)
        if not shared:
            continue
        if commit.timestamp < origin.timestamp:
            upstream.append((commit, shared))
        else:
            downstream.append((commit, shared))
    upstream.sort(key=lambda pair: pair[0].timestamp, reverse=True)
    downstream.sort(key=lambda pair: pair[0].timestamp)
    return upstream[:8], downstream[:8]


def butterfly_response(
    commits: list[CommitEvidence],
    origin: CommitEvidence,
) -> QueryResponse:
    files = [item.path for item in origin.files]
    upstream, downstream = compute_butterfly(commits, origin)
    if not files:
        answer = (
            f"Commit {origin.short_hash} recorded no file-level changes, so a butterfly effect "
            "cannot be traced from Git file evidence in this window."
        )
        return QueryResponse(
            mode="repository-search",
            intent="butterfly",
            answer=answer,
            evidence=[_to_evidence(origin)],
        )

    lines = [
        f"Butterfly effect for {origin.short_hash} ({origin.message}).",
        f"This commit touched {len(files)} file{'s' if len(files) != 1 else ''}: {', '.join(files[:8])}.",
    ]
    if upstream:
        lines.append(
            f"{len(upstream)} earlier analyzed commit{'s' if len(upstream) != 1 else ''} "
            "already touched some of the same files."
        )
    if downstream:
        later = ", ".join(
            f"{commit.short_hash} ({', '.join(shared[:3])})" for commit, shared in downstream[:4]
        )
        lines.append(
            f"{len(downstream)} later analyzed commit{'s' if len(downstream) != 1 else ''} "
            f"reused those files: {later}."
        )
    else:
        lines.append("No later analyzed commit reused those files in this window.")
    lines.append("This traces shared file history, not runtime impact or developer intent.")

    evidence = [_to_evidence(origin, note="Origin of this butterfly trace")]
    for commit, shared in upstream[:3]:
        evidence.append(_to_evidence(commit, note=f"Upstream · {', '.join(shared[:4])}"))
    for commit, shared in downstream[:5]:
        evidence.append(_to_evidence(commit, note=f"Downstream · {', '.join(shared[:4])}"))

    related_commits = [origin.short_hash]
    related_commits.extend(commit.short_hash for commit, _shared in upstream[:3])
    related_commits.extend(commit.short_hash for commit, _shared in downstream[:5])
    return QueryResponse(
        mode="repository-search",
        intent="butterfly",
        answer="\n".join(lines),
        evidence=evidence[:12],
        related_commits=related_commits[:8],
        related_files=files[:12],
        follow_ups=[
            "Which files often changed together?",
            "What files are hotspots?",
        ],
    )
