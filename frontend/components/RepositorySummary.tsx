import { formatCount } from "@/lib/format";
import type { AnalyzeResponse } from "@/lib/types";

export default function RepositorySummary({ analysis }: { analysis: AnalyzeResponse }) {
  const { repository, summary } = analysis;
  return (
    <section aria-labelledby="repo-heading">
      <div className="repo-head">
        <h2 id="repo-heading">
          {repository.owner}/{repository.name}
        </h2>
        <a href={repository.url} target="_blank" rel="noreferrer">
          {repository.url.replace("https://", "")}
        </a>
      </div>
      <dl className="stats">
        <div>
          <dt>Commits</dt>
          <dd>{formatCount(summary.commits_analyzed)}</dd>
        </div>
        <div>
          <dt>Contributors</dt>
          <dd>{formatCount(summary.contributors_found)}</dd>
        </div>
        <div>
          <dt>Files</dt>
          <dd>{formatCount(summary.files_changed)}</dd>
        </div>
        <div>
          <dt>Changes</dt>
          <dd className="churn">
            <span className="add">+{formatCount(summary.additions)}</span>{" "}
            <span className="del">-{formatCount(summary.deletions)}</span>
          </dd>
        </div>
      </dl>
      <p className="form-hint">{summary.history_window}</p>
    </section>
  );
}
