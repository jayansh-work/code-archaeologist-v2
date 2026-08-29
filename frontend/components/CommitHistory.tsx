"use client";

import { useMemo, useState } from "react";

import CommitRow from "@/components/CommitRow";
import type { CommitEvidence } from "@/lib/types";

type SortMode = "recent" | "largest";

type CommitHistoryProps = {
  commits: CommitEvidence[];
  selectedHash: string | null;
  onSelectHash: (hash: string | null) => void;
};

export default function CommitHistory({
  commits,
  selectedHash,
  onSelectHash,
}: CommitHistoryProps) {
  const [search, setSearch] = useState("");
  const [author, setAuthor] = useState("all");
  const [sort, setSort] = useState<SortMode>("recent");

  const authors = useMemo(
    () => Array.from(new Set(commits.map((commit) => commit.author))).sort(),
    [commits],
  );

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    let next = commits;
    if (author !== "all") {
      next = next.filter((commit) => commit.author === author);
    }
    if (needle) {
      next = next.filter((commit) => {
        const blob = [
          commit.message,
          commit.author,
          commit.hash,
          commit.short_hash,
          ...commit.files.map((file) => file.path),
        ]
          .join(" ")
          .toLowerCase();
        return blob.includes(needle);
      });
    }
    if (sort === "largest") {
      next = [...next].sort(
        (left, right) => right.additions + right.deletions - (left.additions + left.deletions),
      );
    }
    return next;
  }, [commits, search, author, sort]);

  return (
    <section aria-labelledby="history-heading">
      <div className="history-head">
        <h2 id="history-heading">Commit history</h2>
        <div className="history-controls">
          <label className="status-live" htmlFor="history-search">
            Search commit history
          </label>
          <input
            id="history-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search message, file, author, hash"
          />
          <label className="status-live" htmlFor="history-author">
            Author
          </label>
          <select
            id="history-author"
            value={author}
            onChange={(event) => setAuthor(event.target.value)}
          >
            <option value="all">All authors</option>
            {authors.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <label className="status-live" htmlFor="history-sort">
            Sort
          </label>
          <select
            id="history-sort"
            value={sort}
            onChange={(event) => setSort(event.target.value as SortMode)}
          >
            <option value="recent">Recent</option>
            <option value="largest">Largest</option>
          </select>
        </div>
      </div>
      {visible.length === 0 ? (
        <p className="empty">No matching commits found. Try a commit message, file path, author, or hash.</p>
      ) : (
        <ul className="commit-list">
          {visible.map((commit) => (
            <CommitRow
              key={commit.hash}
              commit={commit}
              open={selectedHash === commit.hash}
              onToggle={() => onSelectHash(selectedHash === commit.hash ? null : commit.hash)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
