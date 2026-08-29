const SUGGESTIONS = [
  "Explain recent changes",
  "Find architectural shifts",
  "What files are hotspots?",
  "Why did this area change?",
];

type RepositoryQueryProps = {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: (question: string) => void;
};

export default function RepositoryQuery({
  value,
  disabled,
  onChange,
  onSubmit,
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
