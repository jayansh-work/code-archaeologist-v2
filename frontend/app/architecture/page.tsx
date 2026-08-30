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
Git Analyzer → temporary clone → Git CLI
    ↓
Structured evidence + session store
    ↓
Evidence retrieval
    ↓
Optional grounded Gemini
    ↓
Evolution graph + butterfly effect + notes + investigation view`}</pre>
        <h2>Evidence first</h2>
        <p>
          Questions run against stored analysis. The repository is not cloned again. Retrieval
          selects relevant commits before any model call.
        </p>
        <h2>Ask scope</h2>
        <p>
          The main Ask bar always searches the whole analyzed window. A commit or file becomes AI
          context only when you click Ask AI about this commit, Explain this file, or Ask AI about
          this butterfly. Those inline answers stay under the control that asked.
        </p>
        <h2>If AI is unavailable</h2>
        <p>
          Git analysis, the evolution graph, and commit evidence remain usable. The investigation bar
          shows that AI is temporarily unavailable and can be retried. The finding is never blank:
          the retrieved Git explanation remains on screen.
        </p>
      </main>
      <Footer />
    </>
  );
}
