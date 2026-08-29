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
          Code Archaeologist reconstructs recent Git history from a public GitHub repository and
          makes that evidence searchable. It does not invent commits, authors, or intent.
        </p>
        <h2>1. Excavate</h2>
        <p>
          Paste a public GitHub URL and analyze the repository. The backend validates the URL, clones
          a shallow copy into a temporary directory, reads commit metadata with the Git CLI, then
          deletes the clone.
        </p>
        <h2>2. Investigate</h2>
        <p>
          After analysis, ask questions about the current session. Questions run against the stored
          evidence — they do not clone the repository again.
        </p>
        <h2>What you can ask</h2>
        <ul>
          <li>Which files changed the most?</li>
          <li>Who contributed the most in the analyzed history?</li>
          <li>What are the largest commits?</li>
          <li>Show commits involving a file or keyword</li>
          <li>Look up a commit hash from the analyzed window</li>
        </ul>
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
