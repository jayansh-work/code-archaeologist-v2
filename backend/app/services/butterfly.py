"""Butterfly effect: whether a change's files kept being edited afterwards.

Chronology comes from the analyzed commit order, not from timestamp
strings. `git log` returns newest-first, so index 0 is the newest
analyzed commit and the last index is the oldest. Commit timestamps can
carry different timezone offsets, be rewritten, or tie, so they are not
a safe ordering key.

Rules shared with `frontend/lib/butterfly.ts`:
- origin is one analyzed commit, found by hash
- "after this change"  = indices lower than the origin index (newer)
- "before this change" = indices higher than the origin index (older)
- a relationship exists only when another analyzed commit touches at
  least one of the origin's file paths
- at most MAX_LINKS relationships per direction
"""

from __future__ import annotations

from app.models import CommitEvidence, EvidenceItem, QueryResponse

MAX_LINKS = 8

CAVEAT = (
    "This shows shared file history. It does not prove one change caused another."
)


def _shared_paths(origin: CommitEvidence, other: CommitEvidence) -> list[str]:
    origin_paths = {item.path for item in origin.files}
    shared: list[str] = []
    seen: set[str] = set()
    for item in other.files:
        if item.path in origin_paths and item.path not in seen:
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


def origin_index(commits: list[CommitEvidence], origin: CommitEvidence) -> int:
    for index, commit in enumerate(commits):
        if commit.hash == origin.hash:
            return index
    return -1


def compute_butterfly(
    commits: list[CommitEvidence],
    origin: CommitEvidence,
) -> tuple[list[tuple[CommitEvidence, list[str]]], list[tuple[CommitEvidence, list[str]]]]:
    """Return (before, after) relationships using analyzed commit order."""
    index = origin_index(commits, origin)
    if index < 0:
        return [], []

    after: list[tuple[CommitEvidence, list[str]]] = []
    for commit in reversed(commits[:index]):
        shared = _shared_paths(origin, commit)
        if shared:
            after.append((commit, shared))

    before: list[tuple[CommitEvidence, list[str]]] = []
    for commit in commits[index + 1 :]:
        shared = _shared_paths(origin, commit)
        if shared:
            before.append((commit, shared))

    return before[:MAX_LINKS], after[:MAX_LINKS]


def butterfly_response(
    commits: list[CommitEvidence],
    origin: CommitEvidence,
) -> QueryResponse:
    files = [item.path for item in origin.files]
    before, after = compute_butterfly(commits, origin)
    if not files:
        return QueryResponse(
            mode="repository-search",
            intent="butterfly",
            answer=(
                f"Commit {origin.short_hash} did not record any changed files, so there is "
                "nothing to follow forward or backward in the analyzed window."
            ),
            evidence=[_to_evidence(origin)],
        )

    lines = [
        "A small change can spread. If later saved changes edit the same files, the original "
        "change did not stay isolated — its area of the codebase continued evolving.",
        (
            f"Commit {origin.short_hash} (\"{origin.message}\") changed "
            f"{len(files)} file{'s' if len(files) != 1 else ''}: {', '.join(files[:8])}."
        ),
    ]
    if after:
        later = ", ".join(
            f"{commit.short_hash} ({', '.join(shared[:3])})" for commit, shared in after[:4]
        )
        lines.append(
            f"After this change, {len(after)} later analyzed commit"
            f"{'s' if len(after) != 1 else ''} edited the same files: {later}."
        )
    else:
        lines.append(
            "After this change, no later analyzed commit edited those files again in this window."
        )
    if before:
        earlier = ", ".join(commit.short_hash for commit, _shared in before[:4])
        lines.append(
            f"Before this change, {len(before)} earlier analyzed commit"
            f"{'s' if len(before) != 1 else ''} had already edited some of the same files: {earlier}."
        )
    else:
        lines.append(
            "Before this change, no earlier analyzed commit in this window had edited those files."
        )
    lines.append(CAVEAT)

    evidence = [_to_evidence(origin, note="Origin of this butterfly trace")]
    for commit, shared in after[:5]:
        evidence.append(_to_evidence(commit, note=f"After this change · {', '.join(shared[:4])}"))
    for commit, shared in before[:3]:
        evidence.append(_to_evidence(commit, note=f"Before this change · {', '.join(shared[:4])}"))

    related_commits = [origin.short_hash]
    related_commits.extend(commit.short_hash for commit, _shared in after[:5])
    related_commits.extend(commit.short_hash for commit, _shared in before[:3])

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
