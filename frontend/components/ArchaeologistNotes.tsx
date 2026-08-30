import type { ArchaeologistNote } from "@/lib/types";

type ArchaeologistNotesProps = {
  notes: ArchaeologistNote[];
  onSelectHash: (hash: string) => void;
  onSelectFile: (path: string) => void;
};

export default function ArchaeologistNotes({
  notes,
  onSelectHash,
  onSelectFile,
}: ArchaeologistNotesProps) {
  return (
    <section className="notes" aria-labelledby="notes-heading">
      <h2 id="notes-heading" className="section-title">
        Archaeologist notes
      </h2>
      <ul className="notes-list">
        {notes.map((note) => (
          <li key={`${note.kind}-${note.title}-${note.commit_hash ?? note.file_path ?? ""}`}>
            <h3>
              {note.title}
              {note.ai_generated ? <span className="ai-note">AI</span> : null}
            </h3>
            <p>{note.body}</p>
            <div className="inline-actions">
              {note.commit_hash ? (
                <button className="link-btn" type="button" onClick={() => onSelectHash(note.commit_hash ?? "")}>
                  Open related commit
                </button>
              ) : null}
              {note.file_path ? (
                <button className="link-btn" type="button" onClick={() => onSelectFile(note.file_path ?? "")}>
                  Filter to {note.file_path}
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
