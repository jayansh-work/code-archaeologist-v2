from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo
from app.services.analysis_store import StoredAnalysis
from app.services.butterfly import MAX_LINKS, butterfly_response, compute_butterfly
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
    assert "ripple" in result.answer.lower() or "same file" in result.answer.lower()
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


def test_newest_commit_has_no_later_continuation() -> None:
    commits = _commits()
    before, after = compute_butterfly(commits, commits[0])
    assert after == []
    assert [commit.short_hash for commit, _shared in before] == ["bbbbbbb", "aaaaaaa"]
    answer = butterfly_response(commits, commits[0]).answer
    assert "no later analyzed commit" in answer.lower()


def test_oldest_commit_has_no_earlier_context() -> None:
    commits = _commits()
    before, after = compute_butterfly(commits, commits[-1])
    assert before == []
    assert after == []


def test_oldest_shared_file_commit_reports_all_later_work() -> None:
    commits = _commits()
    # `aaaaaaa` is the oldest commit touching src/auth.py.
    before, after = compute_butterfly(commits, commits[2])
    assert before == []
    assert [commit.short_hash for commit, _shared in after] == ["bbbbbbb", "ccccccc"]


def test_identical_timestamps_still_ordered_by_history_position() -> None:
    """Ties in commit time must not collapse the before/after split."""
    tie = "2026-08-20T10:00:00+00:00"
    commits = [
        _commit("c", tie, "newest", [FileChange(path="a.py", additions=1, deletions=0)], 1),
        _commit("b", tie, "middle", [FileChange(path="a.py", additions=1, deletions=0)], 1),
        _commit("a", tie, "oldest", [FileChange(path="a.py", additions=1, deletions=0)], 1),
    ]
    before, after = compute_butterfly(commits, commits[1])
    assert [commit.short_hash for commit, _shared in after] == ["ccccccc"]
    assert [commit.short_hash for commit, _shared in before] == ["aaaaaaa"]


def test_timezone_offsets_do_not_flip_chronology() -> None:
    """These ISO strings sort the wrong way lexically; Git order must win."""
    commits = [
        # Real order: newest is 2026-08-20T01:00:00+05:30 (19:30 UTC on the 19th).
        _commit("c", "2026-08-20T01:00:00+05:30", "newest", [FileChange(path="a.py", additions=1, deletions=0)], 1),
        _commit("b", "2026-08-19T18:00:00+00:00", "middle", [FileChange(path="a.py", additions=1, deletions=0)], 1),
        _commit("a", "2026-08-19T23:00:00+09:00", "oldest", [FileChange(path="a.py", additions=1, deletions=0)], 1),
    ]
    before, after = compute_butterfly(commits, commits[1])
    assert [commit.short_hash for commit, _shared in after] == ["ccccccc"]
    assert [commit.short_hash for commit, _shared in before] == ["aaaaaaa"]


def test_unrelated_files_produce_no_relationships() -> None:
    commits = _commits()
    docs = commits[3]
    before, after = compute_butterfly(commits, docs)
    assert before == []
    assert after == []


def test_deleted_file_still_counts_as_shared_history() -> None:
    commits = [
        _commit(
            "b",
            "2026-08-20T10:00:00+00:00",
            "Drop legacy auth",
            [FileChange(path="src/auth.py", additions=0, deletions=40, change_type="deleted")],
            0,
            40,
        ),
        _commit(
            "a",
            "2026-08-10T10:00:00+00:00",
            "Add auth",
            [FileChange(path="src/auth.py", additions=40, deletions=0, change_type="added")],
            40,
        ),
    ]
    _before, after = compute_butterfly(commits, commits[1])
    assert [commit.short_hash for commit, _shared in after] == ["bbbbbbb"]


def test_binary_file_counts_as_shared_history() -> None:
    binary = FileChange(path="assets/logo.png", additions=0, deletions=0, binary=True)
    commits = [
        _commit("b", "2026-08-20T10:00:00+00:00", "Swap logo", [binary], 0),
        _commit("a", "2026-08-10T10:00:00+00:00", "Add logo", [binary], 0),
    ]
    _before, after = compute_butterfly(commits, commits[1])
    assert [commit.short_hash for commit, _shared in after] == ["bbbbbbb"]


def test_merge_commit_with_no_files_is_reported_clearly() -> None:
    commits = [
        _commit("m", "2026-08-21T10:00:00+00:00", "Merge branch 'main'", [], 0),
        _commit("a", "2026-08-10T10:00:00+00:00", "Add auth", [FileChange(path="a.py", additions=1, deletions=0)], 1),
    ]
    result = butterfly_response(commits, commits[0])
    assert result.intent == "butterfly"
    assert "did not record any changed files" in result.answer
    assert len(result.evidence) == 1


def test_relationships_are_capped() -> None:
    shared = [FileChange(path="a.py", additions=1, deletions=0)]
    commits = [
        CommitEvidence(
            hash=f"{index:040d}",
            short_hash=f"{index:07d}",
            author="Ada",
            author_email="ada@example.com",
            timestamp="2026-08-20T10:00:00+00:00",
            message=f"change {index}",
            additions=1,
            deletions=0,
            files=shared,
        )
        for index in range(24)
    ]
    before, after = compute_butterfly(commits, commits[12])
    assert len(after) == MAX_LINKS
    assert len(before) == MAX_LINKS


def test_origin_not_in_window_returns_nothing() -> None:
    commits = _commits()
    stranger = _commit("z", "2026-08-25T10:00:00+00:00", "Elsewhere", [FileChange(path="src/auth.py", additions=1, deletions=0)], 1)
    before, after = compute_butterfly(commits, stranger)
    assert before == []
    assert after == []


def test_response_never_claims_causation() -> None:
    result = butterfly_response(_commits(), _commits()[1])
    assert "does not prove one change caused another" in result.answer
    lowered = result.answer.lower()
    assert "caused by" not in lowered
    assert "because of" not in lowered
