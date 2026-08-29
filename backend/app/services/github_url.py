import re
from urllib.parse import urlparse

from app.exceptions import InvalidRepoUrlError

OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def parse_github_repo_url(raw: str) -> tuple[str, str, str]:
    """Return (owner, name, canonical_https_url) or raise InvalidRepoUrlError."""
    if raw is None or not str(raw).strip():
        raise InvalidRepoUrlError("A GitHub repository URL is required.")

    text = raw.strip()
    parsed = urlparse(text)

    if parsed.scheme != "https":
        raise InvalidRepoUrlError("Only HTTPS GitHub repository URLs are supported.")

    host = (parsed.hostname or "").lower()
    if host != "github.com":
        raise InvalidRepoUrlError("Only public GitHub repositories are supported.")

    if parsed.username or parsed.password:
        raise InvalidRepoUrlError("Repository URLs must not include credentials.")

    if parsed.query or parsed.fragment:
        raise InvalidRepoUrlError(
            "Repository URL must not include query parameters or fragments."
        )

    if parsed.port not in (None, 443):
        raise InvalidRepoUrlError("Only standard HTTPS GitHub URLs are supported.")

    parts = [segment for segment in parsed.path.split("/") if segment]
    if len(parts) != 2:
        raise InvalidRepoUrlError(
            "URL must look like https://github.com/owner/repository"
        )

    owner, name = parts[0], parts[1]
    if name.lower().endswith(".git"):
        name = name[:-4]

    if not OWNER_RE.fullmatch(owner) or not REPO_RE.fullmatch(name):
        raise InvalidRepoUrlError("Owner or repository name is invalid.")

    if name in {".", ".."} or ".." in name:
        raise InvalidRepoUrlError("Owner or repository name is invalid.")

    canonical = f"https://github.com/{owner}/{name}"
    return owner, name, canonical
