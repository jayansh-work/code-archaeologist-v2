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


def test_expired_sessions_are_dropped(tmp_path) -> None:
    store = AnalysisStore(ttl_seconds=0, max_sessions=8, persist_dir=tmp_path)
    store.put(_sample())
    assert store.get("session-persist-1") is None


def test_expired_sessions_are_not_reloaded(tmp_path) -> None:
    writer = AnalysisStore(ttl_seconds=3600, max_sessions=8, persist_dir=tmp_path)
    writer.put(_sample())
    assert list(tmp_path.glob("*.json"))

    reader = AnalysisStore(ttl_seconds=0, max_sessions=8, persist_dir=tmp_path)
    assert reader.get("session-persist-1") is None


def test_max_sessions_evicts_oldest(tmp_path) -> None:
    store = AnalysisStore(ttl_seconds=3600, max_sessions=2, persist_dir=tmp_path)
    for index in range(3):
        analysis = _sample()
        analysis.analysis_id = f"session-{index}"
        store.put(analysis)
    assert store.get("session-0") is None
    assert store.get("session-2") is not None


def test_corrupt_session_file_does_not_crash_startup(tmp_path) -> None:
    (tmp_path / "broken.json").write_text("{not json at all", encoding="utf-8")
    (tmp_path / "wrong-shape.json").write_text('{"analysis_id": 12}', encoding="utf-8")
    (tmp_path / "empty.json").write_text("", encoding="utf-8")

    writer = AnalysisStore(ttl_seconds=3600, max_sessions=8, persist_dir=tmp_path)
    writer.put(_sample())

    reloaded = AnalysisStore(ttl_seconds=3600, max_sessions=8, persist_dir=tmp_path)
    assert reloaded.get("session-persist-1") is not None


def test_sessions_never_persist_api_keys(tmp_path) -> None:
    store = AnalysisStore(ttl_seconds=3600, max_sessions=8, persist_dir=tmp_path)
    store.put(_sample())
    for path in tmp_path.glob("*.json"):
        blob = path.read_text(encoding="utf-8").lower()
        assert "api_key" not in blob
        assert "gemini" not in blob


def test_unknown_session_returns_none(tmp_path) -> None:
    store = AnalysisStore(ttl_seconds=3600, max_sessions=8, persist_dir=tmp_path)
    assert store.get("no-such-session") is None
