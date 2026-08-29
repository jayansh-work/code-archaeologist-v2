export type FileChange = {
  path: string;
  additions: number;
  deletions: number;
  change_type: string | null;
};

export type CommitEvidence = {
  hash: string;
  short_hash: string;
  author: string;
  author_email: string | null;
  timestamp: string;
  message: string;
  additions: number;
  deletions: number;
  files: FileChange[];
};

export type RepositoryInfo = {
  owner: string;
  name: string;
  url: string;
};

export type AnalysisSummary = {
  commits_analyzed: number;
  contributors_found: number;
  files_changed: number;
  additions: number;
  deletions: number;
  first_commit_at: string | null;
  last_commit_at: string | null;
  history_window: string;
};

export type ArchaeologistNote = {
  kind: string;
  title: string;
  body: string;
  ai_generated: boolean;
  commit_hash: string | null;
  file_path: string | null;
};

export type AnalyzeResponse = {
  analysis_id: string;
  repository: RepositoryInfo;
  summary: AnalysisSummary;
  commits: CommitEvidence[];
  notes: ArchaeologistNote[];
};

export type EvidenceItem = {
  hash: string;
  short_hash: string;
  author: string;
  timestamp: string;
  message: string;
  additions: number;
  deletions: number;
  files: string[];
  note: string | null;
};

export type QueryResponse = {
  mode: string;
  intent: string;
  answer: string;
  evidence: EvidenceItem[];
  ai_used: boolean;
  ai_available: boolean;
  confidence: string | null;
  why: string | null;
  related_commits: string[];
  related_files: string[];
  follow_ups: string[];
  retrieval_summary: string;
  unavailable_reason: string | null;
};

export type NotesResponse = {
  notes: ArchaeologistNote[];
  ai_used: boolean;
};
