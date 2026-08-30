from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo
from app.services.analysis_store import StoredAnalysis
from app.services.butterfly import butterfly_response, compute_butterfly
from app.services.query_engine import answer_question


def _commit(
    letter: str,
    timestamp: str,
    message: str,
    files: list[FileChange],
    additions: int,
    deletions: int = 0,
) -> CommitEvidence:
    return CommitEvidence(
        hash=letter * 40,
        short_hash=letter * 7,
        author="Ada",
        author_email="ada@example.com",
        timestamp=timestamp,
        message=message,
        additions=additions,
        deletions=deletions,
        files=files,
    )


def _commits() -> list[CommitEvidence]:
    return [
        _commit(
            "c",
            "2026-08-29T10:00:00+00:00",
            "Harden login",
            [FileChange(path="src/auth.py", additions=8, deletions=1, change_type="modified")],
            additions=8,
            deletions=1,
        ),
        _commit(
            "b",
            "2026-08-20T10:00:00+00:00",
            "Rewrite session",
            [
                FileChange(path="src/auth.py", additions=20, deletions=4, change_type="modified"),
                FileChange(path="src/session.py", additions=12, deletions=0, change_type="added"),
            ],
            additions=32,
            deletions=4,
        ),
        _commit(
            "a",
            "2026-08-10T10:00:00+00:00",
            "Add login",
            [FileChange(path="src/auth.py", additions=40, deletions=0, change_type="added")],
            additions=40,
        ),
        _commit(
            "d",
            "2026-08-05T10:00:00+00:00",
            "Docs",
            [FileChange(path="README.md", additions=3, deletions=0, change_type="modified")],
            additions=3,
        ),
    ]


def _analysis() -> StoredAnalysis:
    commits = _commits()
    return StoredAnalysis(
        analysis_id="butterfly-session",
        repository=RepositoryInfo(
            owner="octocat",
            name="Hello-World",
            url="https://github.com/octocat/Hello-World",
        ),
        summary=AnalysisSummary(
            commits_analyzed=len(commits),
            contributors_found=1,
            files_changed=3,
            additions=83,
            deletions=5,
            first_commit_at="2026-08-05T10:00:00+00:00",
            last_commit_at="2026-08-29T10:00:00+00:00",
            history_window="Analyzing the latest 30 commits",
        ),
        commits=commits,
    )


def test_compute_butterfly_splits_upstream_and_downstream() -> None:
    commits = _commits()
    origin = commits[1]
    upstream, downstream = compute_butterfly(commits, origin)
    assert [commit.short_hash for commit, _shared in upstream] == ["aaaaaaa"]
    assert [commit.short_hash for commit, _shared in downstream] == ["ccccccc"]
    assert upstream[0][1] == ["src/auth.py"]
    assert downstream[0][1] == ["src/auth.py"]


def test_butterfly_response_mentions_later_reuse() -> None:
    commits = _commits()
    result = butterfly_response(commits, commits[1])
    assert result.intent == "butterfly"
    assert "bbbbbbb" in result.answer
    assert "ccccccc" in result.answer
    assert "src/auth.py" in result.related_files
    assert result.evidence[0].note == "Origin of this butterfly trace"


def test_query_butterfly_uses_selected_commit() -> None:
    result = answer_question(
        _analysis(),
        "What is the butterfly effect of commit bbbbbbb? What later work reused the same files?",
        focus_hashes=["b" * 40],
    )
    assert result.intent == "butterfly"
    assert result.evidence[0].short_hash == "bbbbbbb"
    assert any(item.short_hash == "ccccccc" for item in result.evidence)


def test_query_butterfly_phrase_without_selection_uses_largest() -> None:
    result = answer_question(_analysis(), "Show the butterfly effect")
    assert result.intent == "butterfly"
    assert result.evidence[0].short_hash == "aaaaaaa"
