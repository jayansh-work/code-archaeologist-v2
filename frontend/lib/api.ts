import { site } from "@/lib/site";
import type { AnalyzeResponse, NotesResponse, QueryResponse } from "@/lib/types";

const ANALYZE_TIMEOUT_MS = 90_000;
const QUERY_TIMEOUT_MS = 35_000;
const NOTES_TIMEOUT_MS = 35_000;

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }
  } catch {
    // Fall through to status text.
  }
  if (response.status === 404) {
    return "Repository could not be analyzed. It may be private, unavailable, or invalid.";
  }
  if (response.status === 408) {
    return "Repository analysis timed out. Try a smaller public repository.";
  }
  return "The analysis service returned an unexpected error.";
}

async function request<T>(
  path: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${site.apiBaseUrl}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The request timed out. Try again, or use a smaller public repository.");
    }
    if (error instanceof Error && error.message) {
      throw error;
    }
    throw new Error(
      "Could not reach the analysis service. Confirm the backend is running on port 8000.",
    );
  } finally {
    clearTimeout(timer);
  }
}

export function analyzeRepository(repoUrl: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>(
    "/analyze",
    {
      method: "POST",
      body: JSON.stringify({ repo_url: repoUrl }),
    },
    ANALYZE_TIMEOUT_MS,
  );
}

export function queryRepository(
  analysisId: string,
  question: string,
  selectedHash?: string | null,
  selectedFile?: string | null,
): Promise<QueryResponse> {
  return request<QueryResponse>(
    "/query",
    {
      method: "POST",
      body: JSON.stringify({
        analysis_id: analysisId,
        question,
        selected_hash: selectedHash || undefined,
        selected_file: selectedFile || undefined,
      }),
    },
    QUERY_TIMEOUT_MS,
  );
}

export function fetchAiNotes(analysisId: string): Promise<NotesResponse> {
  return request<NotesResponse>(
    "/notes",
    {
      method: "POST",
      body: JSON.stringify({ analysis_id: analysisId }),
    },
    NOTES_TIMEOUT_MS,
  );
}
