const SUGGESTIONS = [
  "Which files changed the most?",
  "Show recent activity",
  "Largest commits",
  "Who contributed the most?",
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
      <h2 id="query-heading">Ask the repository</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(value);
        }}
      >
        <label className="field-label" htmlFor="repo-question">
          Question
        </label>
        <div className="form-row">
          <input
            id="repo-question"
            name="question"
            type="text"
            placeholder="Ask about this repository's history..."
            value={value}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value)}
          />
          <button className="primary-btn" type="submit" disabled={disabled}>
            {disabled ? "Searching…" : "Ask"}
          </button>
        </div>
      </form>
      <div className="suggestions">
        {SUGGESTIONS.map((item) => (
          <button
            key={item}
            type="button"
            disabled={disabled}
            onClick={() => onSubmit(item)}
          >
            {item.replace(/\?$/, "")}
          </button>
        ))}
      </div>
    </section>
  );
}
