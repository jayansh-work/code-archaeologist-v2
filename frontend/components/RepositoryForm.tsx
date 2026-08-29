type RepositoryFormProps = {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export default function RepositoryForm({
  value,
  disabled,
  onChange,
  onSubmit,
}: RepositoryFormProps) {
  return (
    <form
      className="form-block"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label className="field-label" htmlFor="repo-url">
        GitHub repository URL
      </label>
      <div className="form-row">
        <input
          id="repo-url"
          name="repo_url"
          type="text"
          inputMode="url"
          autoComplete="url"
          spellCheck={false}
          placeholder="https://github.com/owner/repository"
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
        <button className="primary-btn" type="submit" disabled={disabled}>
          {disabled ? "Analyzing…" : "Analyze repository"}
        </button>
      </div>
      <p className="form-hint">Public repositories only. Analyzes the latest 30 commits.</p>
    </form>
  );
}
