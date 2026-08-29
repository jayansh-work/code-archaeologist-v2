from pathlib import Path


def test_git_calls_do_not_use_shell() -> None:
    source = Path("app/services/git_analyzer.py").read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "shell=False" in source
    assert "subprocess.run" in source
