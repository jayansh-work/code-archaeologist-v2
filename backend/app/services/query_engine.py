"""Deterministic evidence query engine. Works without any AI provider."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable

from app.models import CommitEvidence, EvidenceItem, FileChange, QueryResponse
from app.services.analysis_store import StoredAnalysis
from app.services.butterfly import butterfly_response

STOPWORDS = {
    "a",
    "an",
    "and",
    "about",
    "any",
    "are",
    "at",
    "be",
    "by",
    "can",
    "code",
    "commit",
    "commits",
    "did",
    "does",
    "find",
    "for",
    "from",
    "happened",
    "history",
    "how",
    "in",
    "involving",
    "is",
    "it",
    "its",
    "list",
    "me",
    "mentioning",
    "mentions",
    "of",
    "on",
    "or",
    "please",
    "related",
    "repo",
    "repository",
    "show",
    "tell",
    "the",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "work",
    "working",
    "works",
    "you",
}

HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
PATHISH_RE = re.compile(
    r"\b[\w./-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|cs|php|md|json|yml|yaml|toml|css|html|sh|sql)\b",
    re.IGNORECASE,
)


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


def _commit_churn(commit: CommitEvidence) -> int:
    return commit.additions + commit.deletions


def _file_churn(item: FileChange) -> int:
    return item.additions + item.deletions


def _keywords(question: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_./-]+", question.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def _score_commit(commit: CommitEvidence, terms: Iterable[str]) -> int:
    blob = " ".join(
        [
            commit.message,
            commit.author,
            commit.hash,
            commit.short_hash,
            " ".join(item.path for item in commit.files),
        ]
    ).lower()
    score = 0
    for term in terms:
        needle = term.lower()
        if needle in blob:
            score += 3
        if needle in commit.message.lower():
            score += 2
        for item in commit.files:
            if needle in item.path.lower():
                score += 4
        if needle in commit.author.lower():
            score += 2
        if commit.hash.lower().startswith(needle) or commit.short_hash.lower().startswith(needle):
            score += 8
    return score


def _intent(question: str) -> str:
    q = question.lower()
    if any(
        phrase in q
        for phrase in (
            "butterfly",
            "blast radius",
            "ripple",
            "what did this affect",
            "what did that affect",
            "cascade",
            "later commits that",
        )
    ):
        return "butterfly"
    if HASH_RE.search(q) and any(word in q for word in ("before", "prior", "earlier than")):
        return "before_commit"
    if HASH_RE.search(q) and any(
        word in q for word in ("commit", "look up", "lookup", "show", "find", "hash")
    ):
        return "commit_lookup"
    if HASH_RE.search(q) and len(question.strip()) <= 48:
        return "commit_lookup"
    if any(
        phrase in q
        for phrase in (
            "changed together",
            "often changed together",
            "files that change together",
            "coupled",
            "co-changed",
            "cochanged",
        )
    ):
        return "cochanged_files"
    if any(
        phrase in q
        for phrase in (
            "most changed file",
            "files changed the most",
            "largest files",
            "busiest files",
            "which files changed",
            "files with the most",
            "hotspot",
            "hotspots",
            "most frequently changed",
            "most active",
        )
    ):
        return "most_changed_files"
    if any(
        phrase in q
        for phrase in (
            "largest commit",
            "biggest commit",
            "most additions",
            "highest churn",
            "largest changes",
            "most important",
            "important change",
            "architectural",
            "refactor",
        )
    ):
        return "largest_commits"
    if any(
        phrase in q
        for phrase in (
            "who contributed",
            "top contributor",
            "top authors",
            "most commits",
            "contributors",
            "who worked",
        )
    ):
        return "top_contributors"
    if any(
        phrase in q
        for phrase in (
            "recent",
            "latest",
            "what happened recently",
            "recent activity",
            "latest commits",
        )
    ):
        return "recent_activity"
    if any(
        phrase in q
        for phrase in (
            "come to existence",
            "come into existence",
            "how did this start",
            "how did this begin",
            "how was this created",
            "how did this repo",
            "how did this repository",
            "how did this project",
            "how did this come",
            "where did this come",
            "origin of this",
            "explain this repository",
            "explain the repository",
            "what is this repository",
            "repository overview",
            "how did this evolve",
            "explain the evolution",
            "how this began",
            "how does this repository work",
            "how does this repo work",
            "how does this work",
        )
    ):
        return "overview"
    if PATHISH_RE.search(question) or any(
        phrase in q for phrase in ("history for", "history of", "when was", "modified", "this file")
    ):
        return "file_history"
    if any(phrase in q for phrase in ("commits by", "author", "written by", "committed by")):
        return "author_search"
    return "keyword_search"


def _most_changed_files(analysis: StoredAnalysis) -> QueryResponse:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    file_commits: dict[str, list[CommitEvidence]] = defaultdict(list)
    for commit in analysis.commits:
        for item in commit.files:
            totals[item.path][0] += item.additions
            totals[item.path][1] += item.deletions
            file_commits[item.path].append(commit)

    ranked = sorted(
        totals.items(),
        key=lambda pair: pair[1][0] + pair[1][1],
        reverse=True,
    )[:8]
    if not ranked:
        return QueryResponse(
            mode="repository-search",
            intent="most_changed_files",
            answer="No file changes were recorded in the analyzed history.",
            evidence=[],
        )

    lines = []
    evidence: list[EvidenceItem] = []
    seen_hashes: set[str] = set()
    for path, (added, deleted) in ranked:
        lines.append(f"{path}  +{added} -{deleted}")
        for commit in file_commits[path]:
            if commit.hash in seen_hashes:
                continue
            seen_hashes.add(commit.hash)
            evidence.append(_to_evidence(commit, note=path))
            if len(evidence) >= 8:
                break

    answer = (
        "In the analyzed history, these files have the most combined additions and deletions:\n"
        + "\n".join(lines)
        + "\n\nThese totals cover only the analyzed commits, not the entire repository."
    )
    return QueryResponse(
        mode="repository-search",
        intent="most_changed_files",
        answer=answer,
        evidence=evidence[:8],
    )


def _largest_commits(analysis: StoredAnalysis) -> QueryResponse:
    ranked = sorted(analysis.commits, key=_commit_churn, reverse=True)[:8]
    if not ranked:
        return QueryResponse(
            mode="repository-search",
            intent="largest_commits",
            answer="No commits were available to rank.",
            evidence=[],
        )
    lines = [
        f"{commit.short_hash}  {commit.message}  +{commit.additions} -{commit.deletions}"
        for commit in ranked
    ]
    answer = (
        "Largest commits in the analyzed history, ranked by additions plus deletions:\n"
        + "\n".join(lines)
    )
    return QueryResponse(
        mode="repository-search",
        intent="largest_commits",
        answer=answer,
        evidence=[_to_evidence(commit) for commit in ranked],
    )


def _top_contributors(analysis: StoredAnalysis) -> QueryResponse:
    counts = Counter(commit.author for commit in analysis.commits)
    if not counts:
        return QueryResponse(
            mode="repository-search",
            intent="top_contributors",
            answer="No contributors were found in the analyzed history.",
            evidence=[],
        )
    ranked = counts.most_common(8)
    lines = [f"{author}  {count} commit{'s' if count != 1 else ''}" for author, count in ranked]
    answer = (
        "Contributors ranked by number of commits in the analyzed history "
        f"({analysis.summary.commits_analyzed} commits):\n"
        + "\n".join(lines)
        + "\n\nThis is not a ranking of the entire repository lifetime."
    )
    evidence = []
    for author, _count in ranked:
        sample = next(commit for commit in analysis.commits if commit.author == author)
        evidence.append(_to_evidence(sample, note=f"{_count} commits in analyzed history"))
    return QueryResponse(
        mode="repository-search",
        intent="top_contributors",
        answer=answer,
        evidence=evidence,
    )


def _recent_activity(analysis: StoredAnalysis) -> QueryResponse:
    recent = analysis.commits[:8]
    if not recent:
        return QueryResponse(
            mode="repository-search",
            intent="recent_activity",
            answer="No recent commits are available in the analyzed history.",
            evidence=[],
        )
    first = recent[-1].timestamp
    last = recent[0].timestamp
    answer = (
        f"Most recent commits in the analyzed window, from {last} back toward {first}:"
    )
    return QueryResponse(
        mode="repository-search",
        intent="recent_activity",
        answer=answer,
        evidence=[_to_evidence(commit) for commit in recent],
    )


def _overview(analysis: StoredAnalysis) -> QueryResponse:
    commits = analysis.commits
    if not commits:
        return QueryResponse(
            mode="repository-search",
            intent="overview",
            answer="No analyzed commits are available to describe this repository.",
            evidence=[],
        )
    newest = commits[0]
    oldest = commits[-1]
    largest = max(commits, key=_commit_churn)
    picked: list[CommitEvidence] = []
    seen: set[str] = set()
    for commit in (oldest, newest, largest, *commits[:6]):
        if commit.hash in seen:
            continue
        seen.add(commit.hash)
        picked.append(commit)
        if len(picked) >= 10:
            break
    answer = (
        f"The analyzed window covers the latest {analysis.summary.commits_analyzed} commits "
        f"of {analysis.repository.owner}/{analysis.repository.name}, not the full repository origin. "
        f"Oldest analyzed commit: {oldest.short_hash} ({oldest.timestamp}) — {oldest.message}. "
        f"Newest analyzed commit: {newest.short_hash} ({newest.timestamp}) — {newest.message}. "
        f"Largest line change in this window: {largest.short_hash} "
        f"(+{largest.additions} −{largest.deletions}). "
        "Git history in this window can show what changed recently, not why the project was originally created."
    )
    return QueryResponse(
        mode="repository-search",
        intent="overview",
        answer=answer,
        evidence=[_to_evidence(commit) for commit in picked],
    )


def _find_commit(analysis: StoredAnalysis, token: str) -> CommitEvidence | None:
    needle = token.lower()
    for commit in analysis.commits:
        if commit.hash.lower().startswith(needle) or commit.short_hash.lower() == needle:
            return commit
    return None


def _commit_lookup(analysis: StoredAnalysis, question: str) -> QueryResponse:
    match = HASH_RE.search(question)
    if match is None:
        return QueryResponse(
            mode="repository-search",
            intent="commit_lookup",
            answer="No commit hash was found in the question.",
            evidence=[],
        )
    commit = _find_commit(analysis, match.group(0))
    if commit is None:
        return QueryResponse(
            mode="repository-search",
            intent="commit_lookup",
            answer=(
                f"No analyzed commit matches `{match.group(0)}`. "
                "The hash may be older than the analyzed window, or it may not exist in this repository."
            ),
            evidence=[],
        )
    files = ", ".join(item.path for item in commit.files) or "no recorded file changes"
    answer = (
        f"Commit {commit.short_hash} by {commit.author} at {commit.timestamp}: "
        f"{commit.message}. Files: {files}. +{commit.additions} -{commit.deletions}."
    )
    return QueryResponse(
        mode="repository-search",
        intent="commit_lookup",
        answer=answer,
        evidence=[_to_evidence(commit)],
    )


def _before_commit(analysis: StoredAnalysis, question: str) -> QueryResponse:
    match = HASH_RE.search(question)
    if match is None:
        return QueryResponse(
            mode="repository-search",
            intent="before_commit",
            answer="No commit hash was found in the question.",
            evidence=[],
        )
    target = _find_commit(analysis, match.group(0))
    if target is None:
        return QueryResponse(
            mode="repository-search",
            intent="before_commit",
            answer=(
                f"No analyzed commit matches `{match.group(0)}`, so earlier history cannot be listed from this session."
            ),
            evidence=[],
        )
    older = [commit for commit in analysis.commits if commit.timestamp < target.timestamp]
    if not older:
        return QueryResponse(
            mode="repository-search",
            intent="before_commit",
            answer=(
                f"Within the analyzed window, no commits are older than {target.short_hash}. "
                "Earlier history may exist outside the latest-commit limit."
            ),
            evidence=[],
        )
    sample = older[:8]
    answer = (
        f"Analyzed commits older than {target.short_hash} ({target.timestamp}). "
        "This is only the shallow analysis window, not the full repository."
    )
    return QueryResponse(
        mode="repository-search",
        intent="before_commit",
        answer=answer,
        evidence=[_to_evidence(commit) for commit in sample],
    )


def _cochanged(analysis: StoredAnalysis) -> QueryResponse:
    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_commits: dict[tuple[str, str], list[CommitEvidence]] = defaultdict(list)
    for commit in analysis.commits:
        paths = sorted({item.path for item in commit.files})
        if len(paths) < 2:
            continue
        for i, left in enumerate(paths):
            for right in paths[i + 1 :]:
                key = (left, right)
                pair_counts[key] += 1
                if len(pair_commits[key]) < 3:
                    pair_commits[key].append(commit)
    if not pair_counts:
        return QueryResponse(
            mode="repository-search",
            intent="cochanged_files",
            answer="No commits in the analyzed history changed more than one file together.",
            evidence=[],
        )
    top = pair_counts.most_common(6)
    lines = [f"{left}  +  {right}  ({count} shared commits)" for (left, right), count in top]
    answer = (
        "Files that most often changed in the same analyzed commit:\n"
        + "\n".join(lines)
        + "\n\nCo-change counts only reflect the analyzed window."
    )
    evidence: list[EvidenceItem] = []
    seen: set[str] = set()
    for pair, _count in top:
        for commit in pair_commits[pair]:
            if commit.hash in seen:
                continue
            seen.add(commit.hash)
            evidence.append(_to_evidence(commit, note=f"{pair[0]} and {pair[1]}"))
            if len(evidence) >= 8:
                break
        if len(evidence) >= 8:
            break
    return QueryResponse(
        mode="repository-search",
        intent="cochanged_files",
        answer=answer,
        evidence=evidence,
    )


def _file_history(analysis: StoredAnalysis, question: str) -> QueryResponse:
    path_match = PATHISH_RE.search(question)
    candidates: list[str] = []
    if path_match:
        candidates.append(path_match.group(0))
    terms = _keywords(question)
    all_paths = {item.path for commit in analysis.commits for item in commit.files}
    for term in terms:
        for path in all_paths:
            if term.lower() in path.lower() and path not in candidates:
                candidates.append(path)
    if not candidates:
        return _keyword_search(analysis, question)

    target = candidates[0]
    matching = [
        commit
        for commit in analysis.commits
        if any(target.lower() in item.path.lower() or item.path.lower().endswith(target.lower()) for item in commit.files)
    ]
    if not matching:
        return QueryResponse(
            mode="repository-search",
            intent="file_history",
            answer=(
                f"No analyzed commit modified a file matching `{target}`. "
                "The file may be unchanged in the latest-commit window, or the name may not match."
            ),
            evidence=[],
        )
    answer = (
        f"{len(matching)} analyzed commit{'s' if len(matching) != 1 else ''} involve `{target}`."
    )
    return QueryResponse(
        mode="repository-search",
        intent="file_history",
        answer=answer,
        evidence=[_to_evidence(commit) for commit in matching[:10]],
    )


def _author_search(analysis: StoredAnalysis, question: str) -> QueryResponse:
    authors = sorted({commit.author for commit in analysis.commits}, key=len, reverse=True)
    q = question.lower()
    matched_author = next((author for author in authors if author.lower() in q), None)
    if matched_author is None:
        terms = _keywords(question)
        for author in authors:
            if any(term in author.lower() for term in terms):
                matched_author = author
                break
    if matched_author is None:
        return _keyword_search(analysis, question)
    matching = [commit for commit in analysis.commits if commit.author == matched_author]
    answer = (
        f"{matched_author} authored {len(matching)} of the {analysis.summary.commits_analyzed} analyzed commits."
    )
    return QueryResponse(
        mode="repository-search",
        intent="author_search",
        answer=answer,
        evidence=[_to_evidence(commit) for commit in matching[:10]],
    )


def _keyword_search(analysis: StoredAnalysis, question: str) -> QueryResponse:
    terms = _keywords(question)
    if not terms:
        return QueryResponse(
            mode="repository-search",
            intent="keyword_search",
            answer="Ask about files, authors, commits, or a specific hash from the analyzed history.",
            evidence=[],
        )
    scored = []
    for commit in analysis.commits:
        score = _score_commit(commit, terms)
        if score > 0:
            scored.append((score, commit))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored:
        return QueryResponse(
            mode="repository-search",
            intent="keyword_search",
            answer=(
                "No matching commits found in the analyzed history. "
                "Try a commit message, file path, author, or hash."
            ),
            evidence=[],
        )
    matches = [commit for _score, commit in scored[:10]]
    answer = (
        f"Found {len(scored)} matching commit{'s' if len(scored) != 1 else ''} "
        f"for `{', '.join(terms)}` in the analyzed history."
    )
    return QueryResponse(
        mode="repository-search",
        intent="keyword_search",
        answer=answer,
        evidence=[_to_evidence(commit) for commit in matches],
    )


def _butterfly(analysis: StoredAnalysis, question: str, focus_hashes: list[str] | None) -> QueryResponse:
    origin = None
    if focus_hashes:
        origin = _find_commit(analysis, focus_hashes[0])
    if origin is None:
        match = HASH_RE.search(question)
        if match:
            origin = _find_commit(analysis, match.group(0))
    if origin is None:
        origin = max(analysis.commits, key=_commit_churn, default=None)
    if origin is None:
        return QueryResponse(
            mode="repository-search",
            intent="butterfly",
            answer="No analyzed commit is available to trace a butterfly effect.",
            evidence=[],
        )
    return butterfly_response(analysis.commits, origin)


_HANDLERS = {
    "most_changed_files": lambda analysis, _question: _most_changed_files(analysis),
    "largest_commits": lambda analysis, _question: _largest_commits(analysis),
    "top_contributors": lambda analysis, _question: _top_contributors(analysis),
    "recent_activity": lambda analysis, _question: _recent_activity(analysis),
    "overview": lambda analysis, _question: _overview(analysis),
    "cochanged_files": lambda analysis, _question: _cochanged(analysis),
    "commit_lookup": _commit_lookup,
    "before_commit": _before_commit,
    "file_history": _file_history,
    "author_search": _author_search,
    "keyword_search": _keyword_search,
}


def _merge_focus(
    analysis: StoredAnalysis,
    result: QueryResponse,
    focus_hashes: list[str] | None,
    focus_file: str | None,
) -> QueryResponse:
    extra: list[EvidenceItem] = []
    seen = {item.hash for item in result.evidence}
    needles = [token.lower() for token in (focus_hashes or []) if token]
    if needles:
        for commit in analysis.commits:
            if commit.hash in seen:
                continue
            hay = commit.hash.lower()
            if any(hay.startswith(token) or commit.short_hash.lower() == token for token in needles):
                extra.append(_to_evidence(commit, note="Selected in the investigation"))
                seen.add(commit.hash)
    if focus_file:
        needle = focus_file.lower()
        for commit in analysis.commits:
            if commit.hash in seen:
                continue
            if any(needle in item.path.lower() for item in commit.files):
                extra.append(_to_evidence(commit, note=focus_file))
                seen.add(commit.hash)
            if len(extra) >= 8:
                break
    merged = extra + result.evidence
    related_files: list[str] = []
    for item in merged:
        for path in item.files:
            if path not in related_files:
                related_files.append(path)
    return result.model_copy(
        update={
            "evidence": merged[:12],
            "retrieval_summary": result.answer,
            "related_commits": [item.short_hash for item in merged[:8]],
            "related_files": related_files[:12],
        }
    )


def answer_question(
    analysis: StoredAnalysis,
    question: str,
    focus_hashes: list[str] | None = None,
    focus_file: str | None = None,
) -> QueryResponse:
    intent = _intent(question)
    if intent == "butterfly":
        result = _butterfly(analysis, question, focus_hashes)
    else:
        handler = _HANDLERS.get(intent, _keyword_search)
        result = handler(analysis, question)
    return _merge_focus(analysis, result, focus_hashes, focus_file)
