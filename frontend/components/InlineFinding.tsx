"use client";

import CitedText from "@/components/CitedText";
import { displayAnswer, type InlineAskState } from "@/lib/inlineAsk";

type InlineFindingProps = {
  ask: InlineAskState | null | undefined;
  onSelectHash: (hash: string) => void;
  onRetry: () => void;
};

export default function InlineFinding({ ask, onSelectHash, onRetry }: InlineFindingProps) {
  if (!ask) {
    return null;
  }

  if (ask.status === "loading") {
    return (
      <div className="inline-finding" role="status">
        <p className="loading-copy">Investigating…</p>
        <p className="form-hint">Reading the analyzed Git history for this question.</p>
      </div>
    );
  }

  if (ask.status === "error") {
    return (
      <div className="inline-finding" role="alert">
        <p>{ask.error ?? "The investigation could not be completed."}</p>
        <button className="ghost-btn" type="button" onClick={onRetry}>
          Retry
        </button>
      </div>
    );
  }

  if (!ask.result) {
    return null;
  }

  const text = displayAnswer(ask.result);
  const reason = ask.result.unavailable_reason;
  const showKeyHint =
    ask.result.mode === "ai-unavailable" &&
    !ask.result.ai_used &&
    (reason === "not_configured" || reason === "invalid_key");

  return (
    <div className="inline-finding" aria-live="polite">
      {showKeyHint ? (
        <p className="form-hint">
          {reason === "invalid_key"
            ? "Gemini rejected the API key. The Git history explanation is shown instead."
            : "Add GEMINI_API_KEY in backend/.env to let AI rewrite this. The Git history explanation is shown below."}
        </p>
      ) : null}
      {text ? (
        <CitedText text={text} onSelectHash={onSelectHash} />
      ) : (
        <p className="empty">No written answer came back. Retry this question.</p>
      )}
      {ask.result.confidence ? (
        <p className="form-hint">
          Confidence: {ask.result.confidence}
          {ask.result.why ? ` · ${ask.result.why}` : ""}
        </p>
      ) : null}
    </div>
  );
}
