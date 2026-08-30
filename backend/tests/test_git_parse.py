import pytest

from app.models import AnalysisSummary, CommitEvidence, FileChange
from app.services.git_analyzer import (
    _parse_log,
    _parse_name_status,
    _parse_numstat_line,
    _summarize,
    resolve_rename_path,
)


def test_parse_numstat_binary() -> None:
    parsed = _parse_numstat_line("-\t-\tassets/logo.png")
    assert parsed is not None
    assert parsed.path == "assets/logo.png"
    assert parsed.additions == 0
    assert parsed.deletions == 0
    assert parsed.change_type == "binary"


def test_parse_numstat_rename() -> None:
    parsed = _parse_numstat_line("3\t1\told.py => new.py")
    assert parsed is not None
    assert parsed.path == "new.py"
    assert parsed.additions == 3
    assert parsed.deletions == 1


@pytest.mark.parametrize(
    ("raw", "destination", "source"),
    [
        ("old.py => new.py", "new.py", "old.py"),
        ("src/{old => new}/file.py", "src/new/file.py", "src/old/file.py"),
        ("src/{ => nested}/file.py", "src/nested/file.py", "src/file.py"),
        ("src/{nested => }/file.py", "src/file.py", "src/nested/file.py"),
        ("{a => b}", "b", "a"),
        ("frontend/lib/{api.ts => http/api.ts}", "frontend/lib/http/api.ts", "frontend/lib/api.ts"),
        ("plain/path.py", "plain/path.py", None),
        ("weird {name} file.py", "weird {name} file.py", None),
    ],
)
def test_resolve_rename_path(raw: str, destination: str, source: str | None) -> None:
    assert resolve_rename_path(raw) == (destination, source)


@pytest.mark.parametrize(
    ("line", "path"),
    [
        ("3\t1\told.py => new.py", "new.py"),
        ("3\t1\tsrc/{old => new}/file.py", "src/new/file.py"),
        ("3\t1\tsrc/{ => api}/client.ts", "src/api/client.ts"),
        ("-\t-\tsrc/{old => new}/logo.png", "src/new/logo.png"),
    ],
)
def test_parse_numstat_rename_variants(line: str, path: str) -> None:
    parsed = _parse_numstat_line(line)
    assert parsed is not None
    assert parsed.path == path


def test_parse_numstat_keeps_spaces_in_filenames() -> None:
    parsed = _parse_numstat_line("2\t0\tdocs/release notes.md")
    assert parsed is not None
    assert parsed.path == "docs/release notes.md"


def test_parse_numstat_ignores_malformed_rows() -> None:
    assert _parse_numstat_line("") is None
    assert _parse_numstat_line("garbage") is None
    assert _parse_numstat_line("3\tsrc/auth.py") is None


def test_parse_name_status_rename_uses_destination() -> None:
    status = _parse_name_status(
        "\x1e" + "a" * 40 + "\nR094\tsrc/old_auth.py\tsrc/auth.py\nM\tREADME.md\n"
    )
    entries = status["a" * 40]
    assert entries["src/auth.py"] == "renamed"
    assert entries["README.md"] == "modified"


def test_parse_name_status_brace_rename_uses_destination() -> None:
    status = _parse_name_status("\x1e" + "b" * 40 + "\nR100\tsrc/{old => new}/file.py\n")
    assert status["b" * 40] == {"src/new/file.py": "renamed"}


def test_merge_commit_without_files_is_kept() -> None:
    output = (
        "\x1e" + "m" * 40 + "\x1fmmmmmmm\x1fAda\x1fada@example.com"
        "\x1f2026-08-29T10:00:00+00:00\x1fMerge branch 'main'\n"
    )
    commits = _parse_log(output, {})
    assert len(commits) == 1
    assert commits[0].files == []
    assert commits[0].additions == 0


def test_missing_author_email_does_not_break_parsing() -> None:
    output = (
        "\x1e" + "a" * 40 + "\x1faaaaaaa\x1fAda\x1f"
        "\x1f2026-08-29T10:00:00+00:00\x1fFix auth\n"
        "1\t0\tsrc/auth.py\n"
    )
    commits = _parse_log(output, {})
    assert commits[0].author == "Ada"
    assert commits[0].author_email is None


def test_summary_dates_follow_git_order_not_string_order() -> None:
    """Offsets make these ISO strings sort the wrong way lexically."""

    def commit(short: str, timestamp: str) -> CommitEvidence:
        return CommitEvidence(
            hash=short * 5,
            short_hash=short,
            author="Ada",
            author_email="ada@example.com",
            timestamp=timestamp,
            message=short,
            additions=1,
            deletions=0,
            files=[FileChange(path="a.py", additions=1, deletions=0)],
        )

    commits = [
        commit("newest", "2026-08-20T01:00:00+05:30"),
        commit("middle", "2026-08-19T18:00:00+00:00"),
        commit("oldest", "2026-08-19T23:00:00+09:00"),
    ]
    summary: AnalysisSummary = _summarize(commits)
    assert summary.last_commit_at == "2026-08-20T01:00:00+05:30"
    assert summary.first_commit_at == "2026-08-19T23:00:00+09:00"


def test_summary_of_empty_history() -> None:
    summary = _summarize([])
    assert summary.first_commit_at is None
    assert summary.last_commit_at is None
    assert summary.commits_analyzed == 0


def test_parse_log_roundtrip() -> None:
    output = (
        "\x1eaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\x1faaaaaaa\x1fAda\x1fada@example.com"
        "\x1f2026-08-29T10:00:00+00:00\x1fFix auth\n"
        "10\t2\tsrc/auth.py\n"
    )
    status = _parse_name_status("\x1eaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nM\tsrc/auth.py\n")
    commits = _parse_log(output, status)
    assert len(commits) == 1
    assert commits[0].message == "Fix auth"
    assert commits[0].files[0].path == "src/auth.py"
    assert commits[0].files[0].additions == 10
    assert commits[0].files[0].change_type == "modified"
    assert commits[0].additions == 10
    assert commits[0].deletions == 2
