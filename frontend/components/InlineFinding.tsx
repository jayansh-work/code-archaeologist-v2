"use client";

import CitedText from "@/components/CitedText";
import { isFallbackAnswer, unavailableTitle } from "@/lib/aiStatus";
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
  const fallback = isFallbackAnswer(ask.result);

  return (
    <div className="inline-finding" aria-live="polite">
      {fallback ? (
        <p className="form-hint">
          {unavailableTitle(ask.result.unavailable_reason)} Showing the retrieved Git history
          explanation instead.
        </p>
      ) : null}
      {text ? (
        <CitedText text={text} onSelectHash={onSelectHash} />
      ) : (
        <p className="empty">No written answer came back. Retry this question.</p>
      )}
      {fallback ? (
        <button className="ghost-btn" type="button" onClick={onRetry}>
          Retry with AI
        </button>
      ) : null}
      {!fallback && ask.result.confidence ? (
        <p className="form-hint">
          Confidence: {ask.result.confidence}
          {ask.result.why ? ` · ${ask.result.why}` : ""}
        </p>
      ) : null}
    </div>
  );
}
