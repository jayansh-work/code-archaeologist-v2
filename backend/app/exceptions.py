class ArchaeologistError(Exception):
    """User-facing application error with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidRepoUrlError(ArchaeologistError):
    def __init__(self, message: str = "A valid public GitHub repository URL is required.") -> None:
        super().__init__(message, status_code=400)


class GitNotAvailableError(ArchaeologistError):
    def __init__(self) -> None:
        super().__init__(
            "Git is not available on this machine. Install Git and restart the API.",
            status_code=500,
        )


class RepositoryUnavailableError(ArchaeologistError):
    def __init__(
        self,
        message: str = (
            "Repository could not be analyzed. "
            "It may be private, unavailable, invalid, or larger than the current analysis limits."
        ),
    ) -> None:
        super().__init__(message, status_code=404)


class CloneTimeoutError(ArchaeologistError):
    def __init__(self) -> None:
        super().__init__(
            "Repository analysis timed out. Try a smaller public repository.",
            status_code=408,
        )


class EmptyRepositoryError(ArchaeologistError):
    def __init__(self) -> None:
        super().__init__(
            "The repository was cloned, but it has no commits to analyze.",
            status_code=422,
        )


class AnalysisNotFoundError(ArchaeologistError):
    def __init__(self) -> None:
        super().__init__(
            "That analysis session is no longer available. Analyze the repository again.",
            status_code=404,
        )


class QueryError(ArchaeologistError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)
