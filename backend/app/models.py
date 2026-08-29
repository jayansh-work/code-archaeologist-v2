from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=500)

    @field_validator("repo_url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()


class QueryRequest(BaseModel):
    analysis_id: str = Field(..., min_length=8, max_length=80)
    question: str = Field(..., min_length=1, max_length=500)

    @field_validator("analysis_id", "question")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class RepositoryInfo(BaseModel):
    owner: str
    name: str
    url: str


class FileChange(BaseModel):
    path: str
    additions: int
    deletions: int
    change_type: str | None = None


class CommitEvidence(BaseModel):
    hash: str
    short_hash: str
    author: str
    author_email: str | None = None
    timestamp: str
    message: str
    additions: int
    deletions: int
    files: list[FileChange]


class AnalysisSummary(BaseModel):
    commits_analyzed: int
    contributors_found: int
    files_changed: int
    additions: int
    deletions: int
    first_commit_at: str | None = None
    last_commit_at: str | None = None
    history_window: str


class AnalyzeResponse(BaseModel):
    analysis_id: str
    repository: RepositoryInfo
    summary: AnalysisSummary
    commits: list[CommitEvidence]


class EvidenceItem(BaseModel):
    hash: str
    short_hash: str
    author: str
    timestamp: str
    message: str
    additions: int
    deletions: int
    files: list[str]
    note: str | None = None


class QueryResponse(BaseModel):
    mode: str
    intent: str
    answer: str
    evidence: list[EvidenceItem]
    ai_used: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str


class InfoResponse(BaseModel):
    name: str
    version: str
    capabilities: list[str]
    ai_enabled: bool
    max_commits: int
    session_ttl_minutes: int
