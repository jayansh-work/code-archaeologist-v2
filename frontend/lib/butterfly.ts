import type { CommitEvidence } from "@/lib/types";

/**
 * Butterfly chronology mirrors `backend/app/services/butterfly.py`.
 *
 * The analyzed commit list is newest-first (`git log` order), so index 0
 * is the newest analyzed commit. Timestamp strings are not used for
 * ordering because they can carry different timezone offsets, be
 * rewritten, or tie.
 *
 * after  = indices lower than the origin index (newer commits)
 * before = indices higher than the origin index (older commits)
 */
export const MAX_LINKS = 8;

export const BUTTERFLY_CAVEAT =
  "This shows shared file history. It does not prove one change caused another.";

export type ButterflyLink = {
  commit: CommitEvidence;
  shared: string[];
};

export type ButterflyTrace = {
  origin: CommitEvidence;
  files: string[];
  /** Older analyzed commits that already edited the same files. */
  before: ButterflyLink[];
  /** Newer analyzed commits that edited the same files again. */
  after: ButterflyLink[];
};

function sharedPaths(origin: CommitEvidence, other: CommitEvidence): string[] {
  const originPaths = new Set(origin.files.map((item) => item.path));
  const shared: string[] = [];
  const seen = new Set<string>();
  for (const item of other.files) {
    if (originPaths.has(item.path) && !seen.has(item.path)) {
      seen.add(item.path);
      shared.push(item.path);
    }
  }
  return shared;
}

export function computeButterfly(commits: CommitEvidence[], origin: CommitEvidence): ButterflyTrace {
  const files = origin.files.map((item) => item.path);
  const index = commits.findIndex((commit) => commit.hash === origin.hash);
  if (index < 0) {
    return { origin, files, before: [], after: [] };
  }

  const after: ButterflyLink[] = [];
  for (let i = index - 1; i >= 0; i -= 1) {
    const commit = commits[i];
    const shared = sharedPaths(origin, commit);
    if (shared.length > 0) {
      after.push({ commit, shared });
    }
  }

  const before: ButterflyLink[] = [];
  for (let i = index + 1; i < commits.length; i += 1) {
    const commit = commits[i];
    const shared = sharedPaths(origin, commit);
    if (shared.length > 0) {
      before.push({ commit, shared });
    }
  }

  return {
    origin,
    files,
    before: before.slice(0, MAX_LINKS),
    after: after.slice(0, MAX_LINKS),
  };
}

export function butterflyRelatedHashes(trace: ButterflyTrace | null): string[] {
  if (!trace) {
    return [];
  }
  return [
    trace.origin.hash,
    ...trace.after.map((item) => item.commit.hash),
    ...trace.before.map((item) => item.commit.hash),
  ];
}
