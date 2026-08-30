import type { QueryResponse } from "@/lib/types";

/**
 * The API always fills `answer` with the deterministic retrieval, even when
 * Gemini is unavailable. That guarantees the finding is never blank, but it
 * also means the UI must label the fallback so it is never mistaken for an
 * AI answer.
 */
export function isFallbackAnswer(result: QueryResponse): boolean {
  return result.mode === "ai-unavailable" && !result.ai_used;
}

export function unavailableTitle(reason: string | null | undefined): string {
  switch (reason) {
    case "not_configured":
      return "AI investigation is not configured.";
    case "invalid_key":
      return "Gemini rejected the API key.";
    case "rate_limited":
      return "AI temporarily at capacity";
    default:
      return "AI investigation is temporarily unavailable.";
  }
}

export function unavailableBody(reason: string | null | undefined): string {
  switch (reason) {
    case "not_configured":
      return "Add GEMINI_API_KEY to backend/.env, then retry. No restart is required. The retrieved Git evidence below is unaffected.";
    case "invalid_key":
      return "Check GEMINI_API_KEY in backend/.env. The retrieved Git evidence below is unaffected.";
    case "rate_limited":
      return "Gemini has temporarily reached its request limit. The Git evidence below is still available.";
    default:
      return "The retrieved Git evidence below is unaffected.";
  }
}
