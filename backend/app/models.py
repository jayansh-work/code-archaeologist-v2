from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=500)

    @field_validator("repo_url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()


class QueryRequest(BaseModel):
    analysis_id: str = Field(..., min_length=8, max_length=80)
    question: str = Field(..., min_length=1, max_length=800)
    selected_hash: str | None = Field(default=None, max_length=80)
    selected_file: str | None = Field(default=None, max_length=400)
    # Inline commit/file/butterfly explanations set this to false so they do
    # not overwrite the main repository conversation used for follow-ups.
    record_history: bool = True

    @field_validator("analysis_id", "question")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("selected_hash", "selected_file")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class NotesRequest(BaseModel):
    analysis_id: str = Field(..., min_length=8, max_length=80)

    @field_validator("analysis_id")
    @classmethod
    def strip_id(cls, value: str) -> str:
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


class ArchaeologistNote(BaseModel):
    kind: str
    title: str
    body: str
    ai_generated: bool = False
    commit_hash: str | None = None
    file_path: str | None = None


class AnalyzeResponse(BaseModel):
    analysis_id: str
    repository: RepositoryInfo
    summary: AnalysisSummary
    commits: list[CommitEvidence]
    notes: list[ArchaeologistNote]


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
    ai_available: bool = False
    confidence: str | None = None
    why: str | None = None
    related_commits: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    retrieval_summary: str = ""
    unavailable_reason: str | None = None


class NotesResponse(BaseModel):
    notes: list[ArchaeologistNote]
    ai_used: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    # Surfaced so scripts/doctor.ps1 can confirm AI readiness before a demo
    # without ever touching the key itself.
    ai_available: bool


class InfoResponse(BaseModel):
    name: str
    version: str
    capabilities: list[str]
    ai_enabled: bool
    ai_provider: str = "openrouter"
    max_commits: int
    session_ttl_minutes: int
