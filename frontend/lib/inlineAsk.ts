import type { QueryResponse } from "@/lib/types";

/**
 * Inline asks are the explicitly scoped counterpart to the main Ask bar.
 *
 * Each one is keyed by a slot so its loading/answer/error state lives with the
 * control that triggered it, and so the same question asked from two places
 * (commit details panel and commit history row) shares one result instead of
 * firing twice.
 */
export type InlineAskState = {
  status: "loading" | "success" | "error";
  result: QueryResponse | null;
  error: string | null;
  question: string;
};

export function displayAnswer(result: QueryResponse): string {
  const answer = result.answer.trim();
  if (answer) {
    return answer;
  }
  return result.retrieval_summary.trim();
}

export function butterflySlot(hash: string): string {
  return `butterfly:${hash}`;
}

export function commitSlot(hash: string): string {
  return `commit:${hash}`;
}

export function fileSlot(hash: string, path: string): string {
  return `file:${hash}:${path}`;
}

// Prompt text lives here so the same slot always carries the same question,
// whichever control the user clicked.
export function commitQuestion(shortHash: string): string {
  return `In plain English, explain what changed in commit ${shortHash} and what the Git history shows about those changes.`;
}

export function fileQuestion(path: string): string {
  return `Explain the file ${path} in plain English. What is it, and how did it change in the analyzed Git history?`;
}

export function butterflyQuestion(shortHash: string): string {
  return `In plain English, explain the butterfly effect of commit ${shortHash}. Which later work reused the same files?`;
}
