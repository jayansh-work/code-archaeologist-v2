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
import { analyzeRepository, fetchAiNotes, isCancelled, queryRepository } from "@/lib/api";
import type { AskContext } from "@/lib/askContext";
import { commitContext, contextFile, contextHash, fileContext } from "@/lib/askContext";
import type { InlineAskState } from "@/lib/inlineAsk";
import type { ArchaeologistNote, AnalyzeResponse, CommitEvidence, QueryResponse } from "@/lib/types";
import { validateGithubRepoUrl } from "@/lib/validation";

const EvolutionGraph = dynamic(() => import("@/components/EvolutionGraph"), { ssr: false });

type Status = "idle" | "loading" | "success" | "error";
type QueryStatus = "idle" | "loading" | "success" | "error";

const GENERIC_QUERY_ERROR =
  "The investigation could not be completed. Analyze the repository again if the session expired.";

export default function InvestigationApp() {
  const [repoUrl, setRepoUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [reanalyzeError, setReanalyzeError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [notes, setNotes] = useState<ArchaeologistNote[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [askContext, setAskContext] = useState<AskContext | null>(null);
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
  const lastQuery = useRef<{ question: string; context: AskContext | null }>({
    question: "",
    context: null,
  });

  // Request ownership: every async response must prove it still belongs to the
  // analysis that is on screen before it is allowed to write state.
  const ownerRef = useRef<string | null>(null);
  const scopeRef = useRef<AbortController | null>(null);

  const repoLabel = analysis ? `${analysis.repository.owner}/${analysis.repository.name}` : undefined;

  function owns(analysisId: string): boolean {
    return ownerRef.current === analysisId;
  }

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
    // A running query is the newest thing the user did, so it wins over the
    // already-announced analysis result.
    if (queryStatus === "loading") {
      return "Investigating repository history";
    }
    if (status === "loading") {
      return "Excavating repository history";
    }
    if (queryStatus === "error" && queryError) {
      return queryError;
    }
    if (status === "error" && error) {
      return error;
    }
    if (reanalyzeError) {
      return reanalyzeError;
    }
    if (queryStatus === "success") {
      return "Investigation finding ready";
    }
    if (status === "success") {
      return "Repository analysis complete";
    }
    return "";
  }, [status, error, queryStatus, queryError, reanalyzeError]);

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

  async function runAnalyze() {
    if (analyzeLock.current) {
      return;
    }
    const invalid = validateGithubRepoUrl(repoUrl);
    if (invalid) {
      if (analysis) {
        setReanalyzeError(invalid);
      } else {
        setStatus("error");
        setError(invalid);
      }
      return;
    }
    const hadWorkspace = analysis !== null;
    analyzeLock.current = true;
    // Drop ownership first so anything still in flight for the old analysis
    // cannot write into the new workspace.
    ownerRef.current = null;
    scopeRef.current?.abort();
    scopeRef.current = null;
    setStatus("loading");
    setError(null);
    setReanalyzeError(null);
    setQueryResult(null);
    setQueryError(null);
    setQueryStatus("idle");
    setNotesLoading(false);
    try {
      const result = await analyzeRepository(repoUrl.trim());
      const scope = new AbortController();
      ownerRef.current = result.analysis_id;
      scopeRef.current = scope;
      setAnalysis(result);
      setNotes(result.notes);
      setSelectedHash(null);
      setFileFilter("");
      setAskContext(null);
      setQuestion("");
      setAsks({});
      lastQuery.current = { question: "", context: null };
      setStatus("success");
      setShowAnother(false);
      setNotesLoading(true);
      void fetchAiNotes(result.analysis_id, scope.signal)
        .then((extra) => {
          if (!owns(result.analysis_id) || extra.notes.length === 0) {
            return;
          }
          setNotes((current) => [...current, ...extra.notes]);
        })
        .catch(() => {
          // Deterministic notes are already on screen.
        })
        .finally(() => {
          if (owns(result.analysis_id)) {
            setNotesLoading(false);
          }
        });
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : "Repository could not be analyzed.";
      if (hadWorkspace) {
        // Non-destructive: keep the previous investigation but say plainly
        // that the new repository failed.
        setReanalyzeError(message);
        setStatus("success");
        setShowAnother(true);
        if (analysis) {
          ownerRef.current = analysis.analysis_id;
          const scope = new AbortController();
          scopeRef.current = scope;
        }
      } else {
        setAnalysis(null);
        setError(message);
        setStatus("error");
      }
    } finally {
      analyzeLock.current = false;
    }
  }

  /**
   * Main repository-wide investigation. Scope comes only from `context`,
   * never from the selected commit or the history file filter.
   */
  async function runQuery(raw: string, context: AskContext | null) {
    if (!analysis || queryLock.current) {
      return;
    }
    const nextQuestion = raw.trim();
    if (!nextQuestion) {
      setQueryStatus("error");
      setQueryError("Enter a question about this repository.");
      return;
    }
    const analysisId = analysis.analysis_id;
    const signal = scopeRef.current?.signal;
    queryLock.current = true;
    lastQuery.current = { question: nextQuestion, context };
    setQuestion(nextQuestion);
    setAskContext(context);
    setQueryStatus("loading");
    setQueryError(null);
    try {
      const result = await queryRepository(analysisId, nextQuestion, {
        selectedHash: contextHash(context),
        selectedFile: contextFile(context),
        recordHistory: true,
        signal,
      });
      if (!owns(analysisId)) {
        return;
      }
      setQueryResult(result);
      setQueryStatus("success");
      requestAnimationFrame(() => {
        document.getElementById("finding-heading")?.scrollIntoView({ block: "start" });
      });
    } catch (caught) {
      if (isCancelled(caught) || !owns(analysisId)) {
        return;
      }
      setQueryStatus("error");
      setQueryError(caught instanceof Error ? caught.message : GENERIC_QUERY_ERROR);
    } finally {
      queryLock.current = false;
    }
  }

  /**
   * Inline explanation for one commit, file, or butterfly trace. Always
   * explicitly scoped, and never recorded into the main conversation so
   * follow-up questions in the main bar stay coherent.
   */
  async function runInlineAsk(
    slot: string,
    question: string,
    contextCommit: CommitEvidence | null,
    contextFilePath?: string,
  ) {
    if (!analysis || inlineLocks.current.has(slot)) {
      return;
    }
    const nextQuestion = question.trim();
    if (!nextQuestion) {
      return;
    }
    const analysisId = analysis.analysis_id;
    const signal = scopeRef.current?.signal;
    inlineLocks.current.add(slot);
    setAsks((current) => ({
      ...current,
      [slot]: { status: "loading", result: null, error: null, question: nextQuestion },
    }));
    try {
      const result = await queryRepository(analysisId, nextQuestion, {
        selectedHash: contextCommit?.hash ?? null,
        selectedFile: contextFilePath ?? null,
        recordHistory: false,
        signal,
      });
      if (!owns(analysisId)) {
        return;
      }
      setAsks((current) => ({
        ...current,
        [slot]: { status: "success", result, error: null, question: nextQuestion },
      }));
    } catch (caught) {
      if (isCancelled(caught) || !owns(analysisId)) {
        return;
      }
      setAsks((current) => ({
        ...current,
        [slot]: {
          status: "error",
          result: null,
          error: caught instanceof Error ? caught.message : GENERIC_QUERY_ERROR,
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
          Explore how a codebase evolved through real commits, changed files, authors, timestamps,
          and diff statistics.
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
              <p className="form-hint">
                {analysis.summary.history_window}. These figures are not whole-repository totals.
              </p>
              <button
                className="link-btn"
                type="button"
                onClick={() => setShowAnother((value) => !value)}
              >
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
            {reanalyzeError ? (
              <div className="error-box" role="alert">
                <p>Could not analyze the new repository.</p>
                <p>{reanalyzeError}</p>
                <p>
                  Your previous investigation of {repoLabel} is still available below.
                </p>
                <div className="error-actions">
                  <button className="ghost-btn" type="button" onClick={runAnalyze}>
                    Try again
                  </button>
                  <button
                    className="link-btn"
                    type="button"
                    onClick={() => setReanalyzeError(null)}
                  >
                    Keep current investigation
                  </button>
                </div>
              </div>
            ) : null}
            <RepositorySummary analysis={analysis} />
            <RepositoryQuery
              value={question}
              disabled={queryStatus === "loading"}
              context={askContext}
              onChange={setQuestion}
              onClearContext={() => setAskContext(null)}
              onSubmit={(next) => void runQuery(next, askContext)}
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
                <button
                  className="ghost-btn"
                  type="button"
                  onClick={() =>
                    void runQuery(lastQuery.current.question, lastQuery.current.context)
                  }
                >
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
                onAsk={(next) => void runQuery(next, askContext)}
                onRetry={() =>
                  void runQuery(lastQuery.current.question, lastQuery.current.context)
                }
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
                    onAsk={(slot, inlineQuestion, commit, file) => {
                      selectCommit(commit.hash);
                      void runInlineAsk(slot, inlineQuestion, commit, file);
                    }}
                  />
                  <ButterflyPanel
                    commit={selectedCommit}
                    commits={analysis.commits}
                    asks={asks}
                    onSelectHash={(hash) => selectCommit(hash)}
                    onSelectFile={setFileFilter}
                    onAsk={(slot, inlineQuestion, commit, file) => {
                      selectCommit(commit.hash);
                      void runInlineAsk(slot, inlineQuestion, commit, file);
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
                  commitContext(commit.short_hash, commit.hash),
                );
              }}
              onAskFile={(path) => {
                setFileFilter(path);
                void runQuery(`Summarize the evolution of ${path}.`, fileContext(path));
              }}
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
