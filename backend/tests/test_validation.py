from app.exceptions import InvalidRepoUrlError
from app.services.github_url import parse_github_repo_url


def test_accepts_standard_github_url() -> None:
    owner, name, url = parse_github_repo_url("https://github.com/octocat/Hello-World")
    assert owner == "octocat"
    assert name == "Hello-World"
    assert url == "https://github.com/octocat/Hello-World"


def test_accepts_git_suffix_and_trailing_slash() -> None:
    owner, name, url = parse_github_repo_url("https://github.com/octocat/Hello-World.git")
    assert owner == "octocat"
    assert name == "Hello-World"
    assert url == "https://github.com/octocat/Hello-World"


def test_rejects_empty() -> None:
    try:
        parse_github_repo_url("   ")
        assert False
    except InvalidRepoUrlError as exc:
        assert exc.status_code == 400


def test_rejects_non_https() -> None:
    try:
        parse_github_repo_url("http://github.com/octocat/Hello-World")
        assert False
    except InvalidRepoUrlError:
        pass


def test_rejects_non_github_host() -> None:
    try:
        parse_github_repo_url("https://gitlab.com/octocat/Hello-World")
        assert False
    except InvalidRepoUrlError:
        pass


def test_rejects_file_protocol() -> None:
    try:
        parse_github_repo_url("file:///tmp/repo")
        assert False
    except InvalidRepoUrlError:
        pass


def test_rejects_ssh() -> None:
    try:
        parse_github_repo_url("git@github.com:octocat/Hello-World.git")
        assert False
    except InvalidRepoUrlError:
        pass


def test_rejects_extra_path() -> None:
    try:
        parse_github_repo_url("https://github.com/octocat/Hello-World/issues")
        assert False
    except InvalidRepoUrlError:
        pass


def test_rejects_credentials_in_url() -> None:
    try:
        parse_github_repo_url("https://user:token@github.com/octocat/Hello-World")
        assert False
    except InvalidRepoUrlError:
        pass
