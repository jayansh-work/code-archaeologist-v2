"use client";

type CitedTextProps = {
  text: string;
  onSelectHash: (hash: string) => void;
};

const HASH_REF = /\[([0-9a-f]{7,40})\]/gi;

export default function CitedText({ text, onSelectHash }: CitedTextProps) {
  const parts: Array<{ value: string; hash?: string }> = [];
  let last = 0;
  const matches = text.matchAll(HASH_REF);
  for (const match of matches) {
    const index = match.index ?? 0;
    if (index > last) {
      parts.push({ value: text.slice(last, index) });
    }
    parts.push({ value: match[0], hash: match[1] });
    last = index + match[0].length;
  }
  if (last < text.length) {
    parts.push({ value: text.slice(last) });
  }

  return (
    <p className="finding-body">
      {parts.map((part, index) =>
        part.hash ? (
          <button
            key={`${part.hash}-${index}`}
            className="cite"
            type="button"
            onClick={() => onSelectHash(part.hash ?? "")}
          >
            {part.value}
          </button>
        ) : (
          <span key={`t-${index}`}>{part.value}</span>
        ),
      )}
    </p>
  );
}
