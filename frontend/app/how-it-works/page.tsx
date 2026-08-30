import Footer from "@/components/Footer";
import Header from "@/components/Header";

export default function HowItWorksPage() {
  return (
    <>
      <Header current="how" />
      <main className="page prose">
        <p className="kicker">Software forensics</p>
        <h1>How it works</h1>
        <p>
          Code Archaeologist is a repository investigation environment. It reconstructs recent Git history,
          visualizes how the repository evolved, then lets you ask evidence-grounded questions.
        </p>
        <h2>1. Excavate</h2>
        <p>
          Paste a public GitHub URL. The backend validates it, clones a shallow copy, reads commit
          metadata with the Git CLI, then deletes the clone.
        </p>
        <h2>2. Visualize</h2>
        <p>
          The investigation workspace shows a repository evolution flowchart of the analyzed commits.
          Arrows run left-to-right and wrap downward so the graph stays on the page. Selecting a
          node reveals commit details and a butterfly effect: if later commits edited the same files,
          the original change rippled forward. Ask AI under those panels to explain the ripple or a
          file in plain English.
        </p>
        <h2>3. Investigate</h2>
        <p>
          Ask Code Archaeologist in natural language. The API retrieves relevant commits first, then
          Gemini explains only that evidence when an API key is configured. Findings stay linked to
          real hashes.
        </p>
        <h2>Limits</h2>
        <p>
          Analysis covers the latest 30 commits. Git history can show what changed, when, and who
          recorded the commit. It often cannot prove why a developer made a decision.
        </p>
      </main>
      <Footer />
    </>
  );
}
