"""Deterministic Archaeologist Notes derived only from analyzed Git evidence."""

from __future__ import annotations

from collections import Counter, defaultdict

from app.models import ArchaeologistNote, CommitEvidence


def build_deterministic_notes(commits: list[CommitEvidence], commits_window: int) -> list[ArchaeologistNote]:
    notes: list[ArchaeologistNote] = []
    if not commits:
        return [
            ArchaeologistNote(
                kind="caveat",
                title="Caveat",
                body="The analyzed Git history does not contain commits to summarize.",
            )
        ]

    notes.append(
        ArchaeologistNote(
            kind="activity",
            title="Repository activity",
            body=(
                f"{len(commits)} recent commits were analyzed. "
                f"This is a shallow window of the latest {commits_window} commits, not the full repository lifetime."
            ),
        )
    )

    file_counts: dict[str, int] = defaultdict(int)
    file_churn: dict[str, int] = defaultdict(int)
    for commit in commits:
        for item in commit.files:
            file_counts[item.path] += 1
            file_churn[item.path] += item.additions + item.deletions

    if file_counts:
        hotspot, appearances = max(file_counts.items(), key=lambda pair: (pair[1], file_churn[pair[0]]))
        notes.append(
            ArchaeologistNote(
                kind="hotspot",
                title="Historical hotspot",
                body=(
                    f"{hotspot} appears in {appearances} analyzed commit"
                    f"{'s' if appearances != 1 else ''} and is among the most frequently changed files in this window."
                ),
                file_path=hotspot,
            )
        )

    largest = max(commits, key=lambda commit: commit.additions + commit.deletions)
    notes.append(
        ArchaeologistNote(
            kind="largest",
            title="Largest change",
            body=(
                f"Commit {largest.short_hash} produced the largest line change in the analyzed window "
                f"(+{largest.additions} −{largest.deletions}): {largest.message}"
            ),
            commit_hash=largest.hash,
        )
    )

    authors = Counter(commit.author for commit in commits)
    top_n = authors.most_common(3)
    top_count = sum(count for _name, count in top_n)
    if authors:
        names = ", ".join(name for name, _count in top_n)
        notes.append(
            ArchaeologistNote(
                kind="pattern",
                title="Contributor concentration",
                body=(
                    f"{names} account for {top_count} of {len(commits)} analyzed commits. "
                    "This ranking covers only the analyzed history."
                ),
            )
        )

    notes.append(
        ArchaeologistNote(
            kind="caveat",
            title="Caveat",
            body=(
                "Git history shows what changed, when, and who recorded the commit. "
                "It often cannot establish why a developer made a decision unless a commit message states it."
            ),
        )
    )
    return notes
