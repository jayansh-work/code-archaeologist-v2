"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import CommitHistory from "@/components/CommitHistory";
import EvidencePanel from "@/components/EvidencePanel";
import FocusPoints from "@/components/FocusPoints";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import RepositoryForm from "@/components/RepositoryForm";
import RepositoryQuery from "@/components/RepositoryQuery";
import RepositorySummary from "@/components/RepositorySummary";
import TeamCredits from "@/components/TeamCredits";
import { analyzeRepository, queryRepository } from "@/lib/api";
import type { AnalyzeResponse, QueryResponse } from "@/lib/types";
import { validateGithubRepoUrl } from "@/lib/validation";

type Status = "idle" | "loading" | "success" | "error";
type QueryStatus = "idle" | "loading" | "success" | "error";

export default function InvestigationApp() {
  const [repoUrl, setRepoUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [question, setQuestion] = useState("");
  const [queryStatus, setQueryStatus] = useState<QueryStatus>("idle");
  const [queryError, setQueryError] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [selectedHash, setSelectedHash] = useState<string | null>(null);
  const inFlight = useRef(false);

  const repoLabel = analysis ? `${analysis.repository.owner}/${analysis.repository.name}` : undefined;

  const liveMessage = useMemo(() => {
    if (status === "loading") {
      return "Excavating repository history";
    }
    if (status === "error" && error) {
      return error;
    }
    if (status === "success") {
      return "Repository analysis complete";
    }
    if (queryStatus === "loading") {
      return "Searching analyzed history";
    }
    return "";
  }, [status, error, queryStatus]);

  useEffect(() => {
    if (!selectedHash) {
      return;
    }
    const node = document.getElementById(`commit-${selectedHash}`);
    node?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [selectedHash]);

  async function runAnalyze() {
    if (inFlight.current) {
      return;
    }
    const invalid = validateGithubRepoUrl(repoUrl);
    if (invalid) {
      setStatus("error");
      setError(invalid);
      return;
    }
    inFlight.current = true;
    setStatus("loading");
    setError(null);
    setQueryResult(null);
    setQueryError(null);
    setQueryStatus("idle");
    setSelectedHash(null);
    try {
      const result = await analyzeRepository(repoUrl.trim());
      setAnalysis(result);
      setStatus("success");
    } catch (caught) {
      setAnalysis(null);
      setStatus("error");
      setError(caught instanceof Error ? caught.message : "Repository could not be analyzed.");
    } finally {
      inFlight.current = false;
    }
  }

  async function runQuery(raw: string) {
    if (!analysis || inFlight.current) {
      return;
    }
    const nextQuestion = raw.trim();
    if (!nextQuestion) {
      setQueryStatus("error");
      setQueryError("Enter a question about this repository's history.");
      return;
    }
    inFlight.current = true;
    setQuestion(nextQuestion);
    setQueryStatus("loading");
    setQueryError(null);
    try {
      const result = await queryRepository(analysis.analysis_id, nextQuestion);
      setQueryResult(result);
      setQueryStatus("success");
    } catch (caught) {
      setQueryStatus("error");
      setQueryError(
        caught instanceof Error
          ? caught.message
          : "The question could not be answered. Analyze the repository again if the session expired.",
      );
    } finally {
      inFlight.current = false;
    }
  }

  const workspace = status === "success" && analysis;

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Header repoLabel={repoLabel} />
      <main id="main" className={workspace ? "page workspace" : "page"}>
        <p className="kicker">Software forensics</p>
        <h1 className="hero-title">
          Software has a history.
          <br />
          Make it searchable.
        </h1>
        <p className="hero-copy">
          Explore how a codebase evolved through real commits, changed files, authors, timestamps, and diffs.
        </p>

        <RepositoryForm
          value={repoUrl}
          disabled={status === "loading"}
          onChange={setRepoUrl}
          onSubmit={runAnalyze}
        />

        <div className="status-live" aria-live="polite">
          {liveMessage}
        </div>

        {status === "loading" ? (
          <div className="status" role="status">
            <p className="loading-copy">Excavating repository history…</p>
            <p className="loading-sub">This may take a few seconds depending on repository size.</p>
          </div>
        ) : null}

        {status === "error" && error ? (
          <div className="error-box" role="alert">
            <p>Repository could not be analyzed.</p>
            <p>{error}</p>
            <button className="ghost-btn" type="button" onClick={runAnalyze}>
              Try again
            </button>
          </div>
        ) : null}

        {workspace ? (
          <>
            <RepositorySummary analysis={analysis} />
            <RepositoryQuery
              value={question}
              disabled={queryStatus === "loading"}
              onChange={setQuestion}
              onSubmit={runQuery}
            />
            {queryStatus === "loading" ? (
              <div className="status" role="status">
                <p className="loading-copy">Searching analyzed history…</p>
              </div>
            ) : null}
            {queryStatus === "error" && queryError ? (
              <div className="error-box" role="alert">
                <p>{queryError}</p>
              </div>
            ) : null}
            {queryResult ? (
              <EvidencePanel
                result={queryResult}
                onSelectHash={(hash) => setSelectedHash(hash)}
              />
            ) : null}
            <CommitHistory
              commits={analysis.commits}
              selectedHash={selectedHash}
              onSelectHash={setSelectedHash}
            />
          </>
        ) : (
          <>
            <FocusPoints />
            <TeamCredits />
          </>
        )}
      </main>
      <Footer />
    </>
  );
}
