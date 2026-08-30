import type { QueryResponse } from "@/lib/types";

/**
 * The API always fills `answer` with the deterministic retrieval, even when
 * the AI provider is unavailable. That guarantees the finding is never blank,
 * but it also means the UI must label the fallback so it is never mistaken
 * for an AI answer.
 */
export function isFallbackAnswer(result: QueryResponse): boolean {
  return result.mode === "ai-unavailable" && !result.ai_used;
}

export function unavailableTitle(reason: string | null | undefined): string {
  switch (reason) {
    case "not_configured":
      return "AI investigation is not configured.";
    case "invalid_credentials":
    case "invalid_key":
      return "AI provider rejected the configured credentials.";
    case "insufficient_credits":
      return "AI investigation is temporarily unavailable.";
    case "model_unavailable":
      return "AI investigation is temporarily unavailable.";
    case "provider_timeout":
      return "AI investigation is temporarily unavailable.";
    case "rate_limited":
      return "AI request limit reached";
    default:
      return "AI investigation is temporarily unavailable.";
  }
}

export function unavailableBody(reason: string | null | undefined): string {
  switch (reason) {
    case "not_configured":
      return "Add OPENROUTER_API_KEY to backend/.env, then retry. No restart is required. The retrieved Git evidence below is unaffected.";
    case "invalid_credentials":
    case "invalid_key":
      return "The AI provider rejected the configured credentials. Check backend/.env. The retrieved Git evidence below is unaffected.";
    case "insufficient_credits":
      return "The AI provider reported insufficient credits. The Git evidence below is still available.";
    case "model_unavailable":
      return "The configured AI model is unavailable. The Git evidence below is still available.";
    case "provider_timeout":
      return "The AI request timed out. The Git evidence below is still available.";
    case "rate_limited":
      return "AI request limit reached. The Git evidence below is still available.";
    default:
      return "The repository evidence retrieved for this question is shown below.";
  }
}
