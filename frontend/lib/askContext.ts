/**
 * Explicit scope for the main "Ask Code Archaeologist" bar.
 *
 * The main bar is repository-wide by default. UI filter state (selected
 * commit, file filter, sort) is deliberately kept out of AI context so a
 * general question is never silently biased. A scope only exists when the
 * user took an explicit action, and it is always shown as a removable chip.
 */
export type AskContext =
  | { kind: "commit"; hash: string; label: string }
  | { kind: "file"; path: string; label: string };

export function commitContext(shortHash: string, hash: string): AskContext {
  return { kind: "commit", hash, label: `commit ${shortHash}` };
}

export function fileContext(path: string): AskContext {
  return { kind: "file", path, label: path };
}

export function contextHash(context: AskContext | null): string | null {
  return context?.kind === "commit" ? context.hash : null;
}

export function contextFile(context: AskContext | null): string | null {
  return context?.kind === "file" ? context.path : null;
}
