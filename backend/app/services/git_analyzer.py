"""Clone a public GitHub repository and extract structured commit evidence via Git CLI."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from app.config import settings
from app.exceptions import (
    CloneTimeoutError,
    EmptyRepositoryError,
    GitNotAvailableError,
    RepositoryUnavailableError,
)
from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo

RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"
CLONE_NAME = "repo"


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = ""
    env["GCM_INTERACTIVE"] = "Never"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["LC_ALL"] = "C"
    return env


def _run_git(
    args: list[str],
    *,
    timeout: int,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            env=_git_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise GitNotAvailableError() from exc
    except subprocess.TimeoutExpired as exc:
        raise CloneTimeoutError() from exc


def _force_rmtree(path: Path) -> None:
    def _unlock(func, item_path, _exc_info) -> None:  # type: ignore[no-untyped-def]
        try:
            os.chmod(item_path, stat.S_IWRITE)
            func(item_path)
        except OSError:
            pass

    if not path.exists():
        return
    kwargs: dict[str, object]
    if sys.version_info >= (3, 12):
        kwargs = {"onexc": lambda func, item_path, _exc: _unlock(func, item_path, None)}
    else:
        kwargs = {"onerror": _unlock}
    shutil.rmtree(path, **kwargs)


def _map_clone_failure(stderr: str) -> None:
    text = (stderr or "").lower()
    if "timed out" in text or "timeout" in text:
        raise CloneTimeoutError()
    if any(
        token in text
        for token in (
            "could not resolve host",
            "failed to connect",
            "network is unreachable",
            "ssl",
            "connection refused",
        )
    ):
        raise RepositoryUnavailableError(
            "Repository could not be cloned because of a network error. Check your connection and try again."
        )
    raise RepositoryUnavailableError()


_RENAME_BRACE_RE = re.compile(r"\{(?P<old>[^{}]*) => (?P<new>[^{}]*)\}")


def _tidy_path(path: str) -> str:
    """Collapse the empty segments Git brace-rename notation can leave behind."""
    while "//" in path:
        path = path.replace("//", "/")
    return path.strip("/") if path.startswith("/") else path


def resolve_rename_path(path: str) -> tuple[str, str | None]:
    """Return (destination, source) for Git rename notation in numstat output.

    Git writes renames either as `old.py => new.py` or with a shared
    prefix/suffix collapsed into braces, e.g. `src/{old => new}/file.py`.
    Only the destination is stored on the FileChange; the source is
    returned so callers can keep it if useful.
    """
    brace = _RENAME_BRACE_RE.search(path)
    if brace is not None:
        prefix, suffix = path[: brace.start()], path[brace.end() :]
        destination = _tidy_path(f"{prefix}{brace.group('new')}{suffix}")
        source = _tidy_path(f"{prefix}{brace.group('old')}{suffix}")
        return destination, (source or None)
    if " => " in path:
        source_raw, destination_raw = path.split(" => ", 1)
        return destination_raw.strip(), (source_raw.strip() or None)
    return path, None


def _parse_numstat_line(line: str) -> FileChange | None:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    added_raw, deleted_raw = parts[0], parts[1]
    rest = parts[2:]
    if len(rest) >= 2 and rest[0] and rest[-1]:
        # `-z`-style rename rows arrive as added, deleted, old, new.
        path = rest[-1]
    else:
        path = "\t".join(rest)
    path, _source = resolve_rename_path(path)
    binary = added_raw == "-" or deleted_raw == "-"
    additions = 0 if binary or not added_raw.isdigit() else int(added_raw)
    deletions = 0 if binary or not deleted_raw.isdigit() else int(deleted_raw)
    change_type = "binary" if binary else None
    return FileChange(
        path=path,
        additions=additions,
        deletions=deletions,
        change_type=change_type,
    )


_STATUS_RE = re.compile(r"^([AMDCRT]|R\d+|C\d+)\t(.+)$")


def _parse_name_status(output: str) -> dict[str, dict[str, str]]:
    """Map commit hash -> {path: change_type}."""
    mapping: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw_line in output.split("\n"):
        line = raw_line.strip("\r")
        if not line:
            continue
        if line.startswith(RECORD_SEP):
            current = line[1:].strip() or None
            if current:
                mapping.setdefault(current, {})
            continue
        if current is None:
            continue
        match = _STATUS_RE.match(line)
        if not match:
            continue
        status, path = match.group(1), match.group(2)
        if "\t" in path:
            path = path.split("\t")[-1]
        path, _source = resolve_rename_path(path)
        letter = status[0]
        readable = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "T": "type-changed",
        }.get(letter, letter)
        mapping[current][path] = readable
    return mapping


def _parse_log(output: str, status_map: dict[str, dict[str, str]]) -> list[CommitEvidence]:
    commits: list[CommitEvidence] = []
    if not output.strip():
        return commits

    records = output.split(RECORD_SEP)
    for record in records:
        record = record.strip()
        if not record:
            continue
        lines = record.split("\n")
        header = lines[0].strip("\r")
        fields = header.split(FIELD_SEP)
        if len(fields) < 6:
            continue
        full_hash, short_hash, author, email, timestamp, subject = fields[:6]
        files: list[FileChange] = []
        for line in lines[1:]:
            line = line.strip("\r")
            if not line.strip():
                continue
            parsed = _parse_numstat_line(line)
            if parsed is None:
                continue
            path_status = status_map.get(full_hash, {})
            if parsed.change_type is None:
                parsed.change_type = path_status.get(parsed.path)
            files.append(parsed)
        additions = sum(item.additions for item in files)
        deletions = sum(item.deletions for item in files)
        commits.append(
            CommitEvidence(
                hash=full_hash,
                short_hash=short_hash,
                author=author,
                author_email=email or None,
                timestamp=timestamp,
                message=subject,
                additions=additions,
                deletions=deletions,
                files=files,
            )
        )
    return commits


def _summarize(commits: list[CommitEvidence]) -> AnalysisSummary:
    authors = {commit.author for commit in commits if commit.author}
    files = {file.path for commit in commits for file in commit.files}
    additions = sum(commit.additions for commit in commits)
    deletions = sum(commit.deletions for commit in commits)
    # `git log` is newest-first, so use that order instead of comparing ISO
    # strings that may carry different timezone offsets.
    last_at = commits[0].timestamp if commits else None
    first_at = commits[-1].timestamp if commits else None
    return AnalysisSummary(
        commits_analyzed=len(commits),
        contributors_found=len(authors),
        files_changed=len(files),
        additions=additions,
        deletions=deletions,
        first_commit_at=first_at,
        last_commit_at=last_at,
        history_window=f"Analyzing the latest {settings.max_commits} commits",
    )


def analyze_repository(owner: str, name: str, canonical_url: str) -> tuple[RepositoryInfo, AnalysisSummary, list[CommitEvidence]]:
    clone_url = f"{canonical_url}.git"
    timeout = settings.clone_timeout_seconds
    cmd_timeout = settings.git_command_timeout_seconds
    max_commits = settings.max_commits

    probe = _run_git(["git", "--version"], timeout=10)
    if probe.returncode != 0:
        raise GitNotAvailableError()

    workspace_root = Path(tempfile.mkdtemp(prefix="ca-workspace-"))
    repo_path = workspace_root / CLONE_NAME
    try:
        clone = _run_git(
            [
                "git",
                "-c",
                "credential.helper=",
                "clone",
                "--depth",
                str(max_commits),
                "--no-tags",
                "--single-branch",
                clone_url,
                str(repo_path),
            ],
            timeout=timeout,
        )
        if clone.returncode != 0:
            _map_clone_failure(clone.stderr)

        pretty = f"%x1e%H%x1f%h%x1f%an%x1f%ae%x1f%aI%x1f%s"
        log = _run_git(
            [
                "git",
                "-C",
                str(repo_path),
                "log",
                f"-n{max_commits}",
                f"--pretty=format:{pretty}",
                "--numstat",
                "-M",
            ],
            timeout=cmd_timeout,
        )
        if log.returncode != 0:
            raise RepositoryUnavailableError(
                "Repository was cloned, but commit history could not be read."
            )

        status = _run_git(
            [
                "git",
                "-C",
                str(repo_path),
                "log",
                f"-n{max_commits}",
                f"--pretty=format:{RECORD_SEP}%H",
                "--name-status",
                "-M",
            ],
            timeout=cmd_timeout,
        )
        status_map = _parse_name_status(status.stdout if status.returncode == 0 else "")
        commits = _parse_log(log.stdout, status_map)
        if not commits:
            raise EmptyRepositoryError()

        repository = RepositoryInfo(owner=owner, name=name, url=canonical_url)
        summary = _summarize(commits)
        return repository, summary, commits
    finally:
        _force_rmtree(workspace_root)
