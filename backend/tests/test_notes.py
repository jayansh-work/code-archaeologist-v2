from app.models import CommitEvidence, FileChange
from app.services.notes import build_deterministic_notes


def test_deterministic_notes_cover_window_and_hotspot() -> None:
    commits = [
        CommitEvidence(
            hash="a" * 40,
            short_hash="aaaaaaa",
            author="Ada",
            author_email=None,
            timestamp="2026-08-29T10:00:00+00:00",
            message="Fix auth",
            additions=40,
            deletions=2,
            files=[FileChange(path="src/auth.py", additions=40, deletions=2, change_type="modified")],
        ),
        CommitEvidence(
            hash="b" * 40,
            short_hash="bbbbbbb",
            author="Sam",
            author_email=None,
            timestamp="2026-08-28T10:00:00+00:00",
            message="Docs",
            additions=1,
            deletions=0,
            files=[FileChange(path="README.md", additions=1, deletions=0, change_type="modified")],
        ),
    ]
    notes = build_deterministic_notes(commits, 30)
    kinds = {note.kind for note in notes}
    assert "activity" in kinds
    assert "hotspot" in kinds
    assert "largest" in kinds
    assert "caveat" in kinds
    assert any("src/auth.py" in note.body for note in notes)
    assert any("aaaaaaa" in note.body for note in notes)
