import type { QueryResponse } from "@/lib/types";

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
