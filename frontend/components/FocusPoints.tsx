export default function FocusPoints() {
  return (
    <dl className="focus-list">
      <div className="focus-item">
        <dt>01</dt>
        <dd>
          <strong>What changed?</strong>
          <span>Reconstruct modifications across commits and files.</span>
        </dd>
      </div>
      <div className="focus-item">
        <dt>02</dt>
        <dd>
          <strong>When, and why?</strong>
          <span>Trace changes through authors, timestamps and available commit context.</span>
        </dd>
      </div>
      <div className="focus-item">
        <dt>03</dt>
        <dd>
          <strong>Show the evidence.</strong>
          <span>Keep findings connected to actual Git history.</span>
        </dd>
      </div>
    </dl>
  );
}
