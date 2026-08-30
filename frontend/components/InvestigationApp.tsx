"use client";

import dynamic from "next/dynamic";
import { useMemo, useRef, useState } from "react";

import ArchaeologistNotes from "@/components/ArchaeologistNotes";
import ButterflyPanel from "@/components/ButterflyPanel";
import CommitDetailsPanel from "@/components/CommitDetailsPanel";
import CommitHistory from "@/components/CommitHistory";
import EvidencePanel from "@/components/EvidencePanel";
import FocusPoints from "@/components/FocusPoints";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import RepositoryForm from "@/components/RepositoryForm";
import RepositoryQuery from "@/components/RepositoryQuery";
import RepositorySummary from "@/components/RepositorySummary";
import TeamCredits from "@/components/TeamCredits";
import { analyzeRepository, fetchAiNotes, queryRepository } from "@/lib/api";
import type { InlineAskState } from "@/lib/inlineAsk";
import type { ArchaeologistNote, AnalyzeResponse, CommitEvidence, QueryResponse } from "@/lib/types";
import { validateGithubRepoUrl } from "@/lib/validation";

const EvolutionGraph = dynamic(() => import("@/components/EvolutionGraph"), { ssr: false });

type Status = "idle" | "loading" | "success" | "error";
type QueryStatus = "idle" | "loading" | "success" | "error";

export default function InvestigationApp() {
  const [repoUrl, setRepoUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [notes, setNotes] = useState<ArchaeologistNote[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [queryStatus, setQueryStatus] = useState<QueryStatus>("idle");
  const [queryError, setQueryError] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [selectedHash, setSelectedHash] = useState<string | null>(null);
  const [fileFilter, setFileFilter] = useState("");
  const [showAnother, setShowAnother] = useState(false);
  const [asks, setAsks] = useState<Record<string, InlineAskState>>({});
  const analyzeLock = useRef(false);
  const queryLock = useRef(false);
  const inlineLocks = useRef(new Set<string>());
  const lastQuestion = useRef("");

  const repoLabel = analysis ? `${analysis.repository.owner}/${analysis.repository.name}` : undefined;

  function resolveCommitHash(hash: string): string | null {
    if (!analysis) {
      return null;
    }
    const needle = hash.toLowerCase();
    const found = analysis.commits.find(
      (commit) =>
        commit.hash.toLowerCase() === needle ||
        commit.short_hash.toLowerCase() === needle ||
        commit.hash.toLowerCase().startsWith(needle),
    );
    return found?.hash ?? null;
  }

  const selectedCommit = analysis?.commits.find((commit) => commit.hash === selectedHash) ?? null;

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
      return "Investigating repository history";
    }
    return "";
  }, [status, error, queryStatus]);

  function selectCommit(hash: string | null, scrollHistory = false) {
    const resolved = hash ? resolveCommitHash(hash) ?? hash : null;
    setSelectedHash(resolved);
    if (resolved && scrollHistory) {
      requestAnimationFrame(() => {
        document.getElementById(`commit-${resolved}`)?.scrollIntoView({
          block: "nearest",
          behavior: "smooth",
        });
      });
    }
  }

  function askAboutFile(path: string) {
    setFileFilter(path);
    void runQuery(`Summarize the evolution of ${path}.`, null, path);
  }

  async function runAnalyze() {
    if (analyzeLock.current) {
      return;
    }
    const invalid = validateGithubRepoUrl(repoUrl);
    if (invalid) {
      setStatus("error");
      setError(invalid);
      return;
    }
    analyzeLock.current = true;
    setStatus("loading");
    setError(null);
    setQueryResult(null);
    setQueryError(null);
    setQueryStatus("idle");
    setSelectedHash(null);
    setFileFilter("");
    setNotes([]);
    setAsks({});
    try {
      const result = await analyzeRepository(repoUrl.trim());
      setAnalysis(result);
      setNotes(result.notes);
      setStatus("success");
      setShowAnother(false);
      setNotesLoading(true);
      void fetchAiNotes(result.analysis_id)
        .then((extra) => {
          if (extra.notes.length > 0) {
            setNotes((current) => [...current, ...extra.notes]);
          }
        })
        .catch(() => {
          // Deterministic notes already shown.
        })
        .finally(() => setNotesLoading(false));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Repository could not be analyzed.");
      if (!analysis) {
        setAnalysis(null);
        setStatus("error");
      } else {
        setStatus("success");
      }
    } finally {
      analyzeLock.current = false;
    }
  }

  async function runQuery(raw: string, contextCommit?: CommitEvidence | null, contextFile?: string) {
    if (!analysis || queryLock.current) {
      return;
    }
    const nextQuestion = raw.trim();
    if (!nextQuestion) {
      setQueryStatus("error");
      setQueryError("Enter a question about this repository.");
      return;
    }
    queryLock.current = true;
    lastQuestion.current = nextQuestion;
    setQuestion(nextQuestion);
    setQueryStatus("loading");
    setQueryError(null);
    try {
      const result = await queryRepository(
        analysis.analysis_id,
        nextQuestion,
        contextCommit?.hash ?? selectedHash,
        contextFile ?? (fileFilter || undefined),
      );
      setQueryResult(result);
      setQueryStatus("success");
      requestAnimationFrame(() => {
        document.getElementById("finding-heading")?.scrollIntoView({ block: "start" });
      });
    } catch (caught) {
      setQueryStatus("error");
      setQueryError(
        caught instanceof Error
          ? caught.message
          : "The investigation could not be completed. Analyze the repository again if the session expired.",
      );
    } finally {
      queryLock.current = false;
    }
  }

  async function runInlineAsk(
    slot: string,
    question: string,
    contextCommit?: CommitEvidence | null,
    contextFile?: string,
  ) {
    if (!analysis || inlineLocks.current.has(slot)) {
      return;
    }
    const nextQuestion = question.trim();
    if (!nextQuestion) {
      return;
    }
    inlineLocks.current.add(slot);
    setAsks((current) => ({
      ...current,
      [slot]: { status: "loading", result: null, error: null, question: nextQuestion },
    }));
    try {
      const result = await queryRepository(
        analysis.analysis_id,
        nextQuestion,
        contextCommit?.hash ?? selectedHash,
        contextFile,
      );
      setAsks((current) => ({
        ...current,
        [slot]: { status: "success", result, error: null, question: nextQuestion },
      }));
    } catch (caught) {
      setAsks((current) => ({
        ...current,
        [slot]: {
          status: "error",
          result: null,
          error:
            caught instanceof Error
              ? caught.message
              : "The investigation could not be completed. Analyze the repository again if the session expired.",
          question: nextQuestion,
        },
      }));
    } finally {
      inlineLocks.current.delete(slot);
    }
  }

  const workspace = analysis !== null;

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

        <div className="landing-form">
          <RepositoryForm
            value={repoUrl}
            disabled={status === "loading"}
            onChange={setRepoUrl}
            onSubmit={runAnalyze}
          />
        </div>

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
            <div className="workspace-toolbar">
              <p className="form-hint">{analysis.summary.history_window}. These figures are not whole-repository totals.</p>
              <button className="link-btn" type="button" onClick={() => setShowAnother((value) => !value)}>
                Analyze another repository
              </button>
            </div>
            {showAnother ? (
              <RepositoryForm
                value={repoUrl}
                disabled={status === "loading"}
                onChange={setRepoUrl}
                onSubmit={runAnalyze}
              />
            ) : null}
            <RepositorySummary analysis={analysis} />
            <RepositoryQuery
              value={question}
              disabled={queryStatus === "loading"}
              onChange={setQuestion}
              onSubmit={(next) => void runQuery(next)}
            />
            {queryStatus === "loading" ? (
              <div className="status" role="status">
                <p className="loading-copy">Investigating repository history…</p>
                <p className="loading-sub">Tracing relevant evidence…</p>
              </div>
            ) : null}
            {queryStatus === "error" && queryError ? (
              <div className="error-box" role="alert">
                <p>{queryError}</p>
                <button className="ghost-btn" type="button" onClick={() => void runQuery(lastQuestion.current)}>
                  Retry
                </button>
              </div>
            ) : null}
            {queryResult ? (
              <EvidencePanel
                result={queryResult}
                loading={queryStatus === "loading"}
                onSelectHash={(hash) => selectCommit(hash, true)}
                onSelectFile={setFileFilter}
                onAsk={(next) => void runQuery(next)}
                onRetry={() => void runQuery(lastQuestion.current)}
              />
            ) : null}

            <section className="evolution" aria-labelledby="evolution-heading">
              <h2 id="evolution-heading" className="section-title">
                Repository evolution
              </h2>
              <p className="form-hint">
                Older work starts at the top-left. Arrows point toward newer commits. Select a commit
                to see if later work reused the same files.
              </p>
              <div className="evolution-layout">
                <EvolutionGraph
                  commits={analysis.commits}
                  selectedHash={selectedHash}
                  onSelectHash={(hash) => selectCommit(hash)}
                />
                <div className="evolution-below">
                  <CommitDetailsPanel
                    commit={selectedCommit}
                    asks={asks}
                    onSelectHash={(hash) => selectCommit(hash)}
                    onSelectFile={setFileFilter}
                    onAsk={(slot, question, commit, file) => {
                      selectCommit(commit.hash);
                      void runInlineAsk(slot, question, commit, file);
                    }}
                  />
                  <ButterflyPanel
                    commit={selectedCommit}
                    commits={analysis.commits}
                    asks={asks}
                    onSelectHash={(hash) => selectCommit(hash)}
                    onSelectFile={setFileFilter}
                    onAsk={(slot, question, commit, file) => {
                      selectCommit(commit.hash);
                      void runInlineAsk(slot, question, commit, file);
                    }}
                  />
                </div>
              </div>
            </section>

            <ArchaeologistNotes
              notes={notes}
              loadingAi={notesLoading}
              onSelectHash={(hash) => selectCommit(hash, true)}
              onSelectFile={setFileFilter}
            />

            <CommitHistory
              commits={analysis.commits}
              selectedHash={selectedHash}
              fileFilter={fileFilter}
              onFileFilterChange={setFileFilter}
              onSelectHash={(hash) => selectCommit(hash)}
              onAsk={(commit) => {
                selectCommit(commit.hash);
                void runQuery(
                  `Explain this commit ${commit.short_hash} to someone new to the codebase.`,
                  commit,
                );
              }}
              onAskFile={askAboutFile}
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
