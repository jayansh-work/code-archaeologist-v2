import type { CommitEvidence } from "@/lib/types";

export type ButterflyLink = {
  commit: CommitEvidence;
  shared: string[];
};

export type ButterflyTrace = {
  origin: CommitEvidence;
  files: string[];
  upstream: ButterflyLink[];
  downstream: ButterflyLink[];
};

function sharedPaths(left: CommitEvidence, right: CommitEvidence): string[] {
  const leftPaths = new Set(left.files.map((item) => item.path));
  const shared: string[] = [];
  const seen = new Set<string>();
  for (const item of right.files) {
    if (leftPaths.has(item.path) && !seen.has(item.path)) {
      seen.add(item.path);
      shared.push(item.path);
    }
  }
  return shared;
}

export function computeButterfly(commits: CommitEvidence[], origin: CommitEvidence): ButterflyTrace {
  const upstream: ButterflyLink[] = [];
  const downstream: ButterflyLink[] = [];
  for (const commit of commits) {
    if (commit.hash === origin.hash) {
      continue;
    }
    const shared = sharedPaths(origin, commit);
    if (shared.length === 0) {
      continue;
    }
    if (commit.timestamp < origin.timestamp) {
      upstream.push({ commit, shared });
    } else {
      downstream.push({ commit, shared });
    }
  }
  upstream.sort((left, right) => right.commit.timestamp.localeCompare(left.commit.timestamp));
  downstream.sort((left, right) => left.commit.timestamp.localeCompare(right.commit.timestamp));
  return {
    origin,
    files: origin.files.map((item) => item.path),
    upstream: upstream.slice(0, 8),
    downstream: downstream.slice(0, 8),
  };
}

export function butterflyRelatedHashes(trace: ButterflyTrace | null): string[] {
  if (!trace) {
    return [];
  }
  return [trace.origin.hash, ...trace.upstream.map((item) => item.commit.hash), ...trace.downstream.map((item) => item.commit.hash)];
}
