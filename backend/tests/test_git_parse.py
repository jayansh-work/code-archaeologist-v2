from app.services.git_analyzer import _parse_log, _parse_name_status, _parse_numstat_line


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
