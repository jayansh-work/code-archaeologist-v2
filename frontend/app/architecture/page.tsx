import Footer from "@/components/Footer";
import Header from "@/components/Header";

export default function ArchitecturePage() {
  return (
    <>
      <Header current="architecture" />
      <main className="page prose">
        <p className="kicker">Internals</p>
        <h1>Architecture</h1>
        <pre className="flow">{`Browser
    ↓
Next.js
    ↓
FastAPI
    ↓
Git Analyzer
    ↓
Temporary Clone
    ↓
Git CLI
    ↓
Structured Evidence
    ↓
Analysis Session Store
    ↓
Repository Query Engine
    ↓
Optional Grounded AI
    ↓
Investigation view`}</pre>
        <h2>Why Git CLI</h2>
        <p>
          Git is the source of truth for history. Calling Git with argument arrays avoids shell
          injection and keeps extraction aligned with what developers already trust.
        </p>
        <h2>Temporary clones</h2>
        <p>
          Clones live in a temporary directory and are removed after analysis, including failures.
          Query requests reuse structured evidence in memory instead of keeping repositories on disk.
        </p>
        <h2>Optional AI</h2>
        <p>
          If a Gemini API key is configured, answers may be written from retrieved evidence. Without a
          key, deterministic repository search remains available.
        </p>
      </main>
      <Footer />
    </>
  );
}
