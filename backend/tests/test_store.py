from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo
from app.services.analysis_store import AnalysisStore, ConversationTurn, StoredAnalysis


def _sample() -> StoredAnalysis:
    return StoredAnalysis(
        analysis_id="session-persist-1",
        repository=RepositoryInfo(
            owner="octocat",
            name="Hello-World",
            url="https://github.com/octocat/Hello-World",
        ),
        summary=AnalysisSummary(
            commits_analyzed=1,
            contributors_found=1,
            files_changed=1,
            additions=1,
            deletions=0,
            first_commit_at="2011-01-26T19:06:08+00:00",
            last_commit_at="2011-01-26T19:06:08+00:00",
            history_window="Analyzing the latest 30 commits",
        ),
        commits=[
            CommitEvidence(
                hash="a" * 40,
                short_hash="aaaaaaa",
                author="The Octocat",
                author_email=None,
                timestamp="2011-01-26T19:06:08+00:00",
                message="first commit",
                additions=1,
                deletions=0,
                files=[FileChange(path="README", additions=1, deletions=0, change_type="added")],
            )
        ],
    )


def test_store_survives_reload(tmp_path) -> None:
    first = AnalysisStore(ttl_seconds=3600, max_sessions=8, persist_dir=tmp_path)
    analysis = _sample()
    first.put(analysis)
    first.append_turn(
        analysis.analysis_id,
        ConversationTurn(question="What changed?", answer="README was added.", evidence_hashes=["a" * 40]),
    )

    reloaded = AnalysisStore(ttl_seconds=3600, max_sessions=8, persist_dir=tmp_path)
    restored = reloaded.get("session-persist-1")
    assert restored is not None
    assert restored.repository.name == "Hello-World"
    assert restored.commits[0].short_hash == "aaaaaaa"
    assert restored.turns[0].question == "What changed?"
