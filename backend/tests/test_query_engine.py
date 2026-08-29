from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo
from app.services.analysis_store import StoredAnalysis
from app.services.query_engine import answer_question


def _analysis() -> StoredAnalysis:
    commits = [
        CommitEvidence(
            hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            short_hash="aaaaaaa",
            author="Ada",
            author_email="ada@example.com",
            timestamp="2026-08-29T10:00:00+00:00",
            message="Fix authentication validation",
            additions=20,
            deletions=4,
            files=[
                FileChange(path="src/auth.py", additions=18, deletions=4, change_type="modified"),
                FileChange(path="src/session.py", additions=2, deletions=0, change_type="modified"),
            ],
        ),
        CommitEvidence(
            hash="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            short_hash="bbbbbbb",
            author="Ada",
            author_email="ada@example.com",
            timestamp="2026-08-28T10:00:00+00:00",
            message="Update README",
            additions=5,
            deletions=1,
            files=[FileChange(path="README.md", additions=5, deletions=1, change_type="modified")],
        ),
        CommitEvidence(
            hash="cccccccccccccccccccccccccccccccccccccccc",
            short_hash="ccccccc",
            author="Sam",
            author_email="sam@example.com",
            timestamp="2026-08-27T10:00:00+00:00",
            message="Add login tests",
            additions=40,
            deletions=0,
            files=[FileChange(path="tests/test_auth.py", additions=40, deletions=0, change_type="added")],
        ),
    ]
    return StoredAnalysis(
        analysis_id="test-session",
        repository=RepositoryInfo(
            owner="octocat",
            name="Hello-World",
            url="https://github.com/octocat/Hello-World",
        ),
        summary=AnalysisSummary(
            commits_analyzed=3,
            contributors_found=2,
            files_changed=4,
            additions=65,
            deletions=5,
            first_commit_at="2026-08-27T10:00:00+00:00",
            last_commit_at="2026-08-29T10:00:00+00:00",
            history_window="Analyzing the latest 30 commits",
        ),
        commits=commits,
    )


def test_most_changed_files_ranks_auth() -> None:
    result = answer_question(_analysis(), "Which files changed the most?")
    assert result.intent == "most_changed_files"
    assert "src/auth.py" in result.answer or "tests/test_auth.py" in result.answer
    assert result.evidence


def test_readme_keyword() -> None:
    result = answer_question(_analysis(), "Find commits mentioning README")
    assert result.evidence
    assert any("README" in item.message or "README.md" in item.files for item in result.evidence)


def test_file_history_auth() -> None:
    result = answer_question(_analysis(), "When was src/auth.py modified?")
    assert result.intent == "file_history"
    assert result.evidence[0].short_hash == "aaaaaaa"


def test_hash_lookup() -> None:
    result = answer_question(_analysis(), "Look up commit bbbbbbb")
    assert result.intent == "commit_lookup"
    assert result.evidence[0].short_hash == "bbbbbbb"


def test_hotspots_and_important_changes() -> None:
    hotspots = answer_question(_analysis(), "What files are hotspots?")
    assert hotspots.intent == "most_changed_files"
    assert hotspots.evidence

    important = answer_question(_analysis(), "What are the most important changes in this repository?")
    assert important.intent == "largest_commits"
    assert important.evidence[0].short_hash == "ccccccc"


def test_origin_question_uses_overview() -> None:
    result = answer_question(_analysis(), "how did this come to existence")
    assert result.intent == "overview"
    assert result.evidence
    assert "not the full repository origin" in result.answer


def test_how_repository_works_uses_overview() -> None:
    result = answer_question(_analysis(), "how does this repository work?")
    assert result.intent == "overview"
    assert result.evidence
