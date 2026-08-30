import { site } from "@/lib/site";
import type { AnalyzeResponse, QueryResponse } from "@/lib/types";

const ANALYZE_TIMEOUT_MS = 90_000;
// Both query paths may call the AI provider, whose whole fallback chain is
// capped at 40s server-side. Staying above that keeps the backend's own calm
// fallback visible instead of a browser timeout.
const QUERY_TIMEOUT_MS = 60_000;

/** Thrown when a caller-supplied signal aborts, e.g. a newer analysis started. */
export class RequestCancelledError extends Error {
  constructor() {
    super("Request cancelled.");
    this.name = "RequestCancelledError";
  }
}

export function isCancelled(error: unknown): boolean {
  return error instanceof RequestCancelledError;
}

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
  externalSignal?: AbortSignal,
): Promise<T> {
  if (externalSignal?.aborted) {
    throw new RequestCancelledError();
  }
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const forwardAbort = () => controller.abort();
  externalSignal?.addEventListener("abort", forwardAbort);
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
      if (timedOut) {
        throw new Error("The request timed out. Try again, or use a smaller public repository.");
      }
      throw new RequestCancelledError();
    }
    if (error instanceof TypeError) {
      throw new Error(
        "Could not reach the analysis service. Confirm the backend is running on port 8000.",
      );
    }
    if (error instanceof Error && error.message) {
      throw error;
    }
    throw new Error(
      "Could not reach the analysis service. Confirm the backend is running on port 8000.",
    );
  } finally {
    clearTimeout(timer);
    externalSignal?.removeEventListener("abort", forwardAbort);
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

export type QueryOptions = {
  /** Explicit commit context. Only set by inline commit/butterfly asks. */
  selectedHash?: string | null;
  /** Explicit file context. Only set by inline file asks. */
  selectedFile?: string | null;
  /** Main ask records conversation history; inline explanations do not. */
  recordHistory?: boolean;
  signal?: AbortSignal;
};

export function queryRepository(
  analysisId: string,
  question: string,
  options: QueryOptions = {},
): Promise<QueryResponse> {
  return request<QueryResponse>(
    "/query",
    {
      method: "POST",
      body: JSON.stringify({
        analysis_id: analysisId,
        question,
        selected_hash: options.selectedHash || undefined,
        selected_file: options.selectedFile || undefined,
        record_history: options.recordHistory ?? true,
      }),
    },
    QUERY_TIMEOUT_MS,
    options.signal,
  );
}
