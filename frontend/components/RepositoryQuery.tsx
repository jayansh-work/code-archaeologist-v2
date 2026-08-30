import type { AskContext } from "@/lib/askContext";

const SUGGESTIONS = [
  "Explain recent changes",
  "Find architectural shifts",
  "What files are hotspots?",
  "Which files changed together?",
];

type RepositoryQueryProps = {
  value: string;
  disabled: boolean;
  /** Explicit, user-visible scope. Null means repository-wide. */
  context: AskContext | null;
  onChange: (value: string) => void;
  onSubmit: (question: string) => void;
  onClearContext: () => void;
};

export default function RepositoryQuery({
  value,
  disabled,
  context,
  onChange,
  onSubmit,
  onClearContext,
}: RepositoryQueryProps) {
  return (
    <section className="query-block" aria-labelledby="query-heading">
      <h2 id="query-heading" className="section-title">
        Ask Code Archaeologist
      </h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(value);
        }}
      >
        <label className="status-live" htmlFor="repo-question">
          Ask anything about this repository
        </label>
        <div className="ask-row">
          <input
            id="repo-question"
            name="question"
            type="text"
            placeholder="Ask anything about this repository..."
            value={value}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                onChange("");
              }
            }}
          />
          <button className="ask-btn" type="submit" disabled={disabled} aria-label="Investigate">
            →
          </button>
        </div>
      </form>
      <div className="ask-scope">
        {context ? (
          <>
            <span className="scope-chip">
              Context: {context.label}
              <button
                type="button"
                aria-label={`Remove ${context.label} context and ask across the whole repository`}
                onClick={onClearContext}
              >
                ×
              </button>
            </span>
            <span className="form-hint">This question is scoped to the context above.</span>
          </>
        ) : (
          <span className="form-hint">
            Scope: whole analyzed repository. Selecting a commit or filtering files does not change it.
          </span>
        )}
      </div>
      <p className="form-hint">Suggested investigations</p>
      <div className="suggestions">
        {SUGGESTIONS.map((item) => (
          <button
            key={item}
            className="chip"
            type="button"
            disabled={disabled}
            onClick={() => onSubmit(item)}
          >
            {item}
          </button>
        ))}
      </div>
    </section>
  );
}
