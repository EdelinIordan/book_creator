import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { AppLayout } from "../../../layout/AppLayout";
import {
  DraftFeedback,
  DraftIterationDetail,
  SubchapterDraftState,
  WritingDetail,
  fetchWriting,
  runWriting,
} from "../../../lib/api";
import styles from "./writing.module.css";

function statusLabel(status: SubchapterDraftState["status"]): string {
  switch (status) {
    case "ready":
      return "Ready";
    case "in_review":
      return "In Review";
    default:
      return "Draft";
  }
}

function roleLabel(role: string): string {
  return role
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function FeedbackList({ feedback }: { feedback: DraftFeedback[] }) {
  if (!feedback || feedback.length === 0) {
    return null;
  }

  return (
    <div className={styles.feedbackChips}>
      {feedback.map((item) => (
        <div
          key={item.id}
          className={styles.feedbackChip}
          data-severity={item.severity}
          data-addressed={item.addressed ? "true" : "false"}
        >
          <header>
            <span>{item.severity.toUpperCase()}</span>
            {item.addressed && <small>Resolved</small>}
          </header>
          <p>{item.message}</p>
          {item.rationale && <small>{item.rationale}</small>}
          {item.category && <small>Focus: {roleLabel(item.category)}</small>}
        </div>
      ))}
    </div>
  );
}

function IterationPanel({ iteration }: { iteration: DraftIterationDetail }) {
  const hasFeedback = iteration.feedback && iteration.feedback.length > 0;

  return (
    <div className={styles.iteration}>
      <div className={styles.iterationHeader}>
        <span className={styles.iterationRole}>{roleLabel(iteration.role)}</span>
        <span className={styles.iterationMeta}>{formatDate(iteration.created_at)}</span>
      </div>
      {iteration.summary && <p>{iteration.summary}</p>}
      <details>
        <summary>View draft</summary>
        <pre>{iteration.content}</pre>
      </details>
      {hasFeedback && <FeedbackList feedback={iteration.feedback} />}
    </div>
  );
}

function SubchapterCard({ draft }: { draft: SubchapterDraftState }) {
  const latestIteration = draft.iterations[draft.iterations.length - 1];

  return (
    <article className={styles.subchapterCard} data-status={draft.status}>
      <div className={styles.subchapterHeader}>
        <div>
          <h2>{draft.title}</h2>
          <div className={styles.labelRow}>
            {draft.order_label && <span>#{draft.order_label}</span>}
            {draft.chapter_title && <span>{draft.chapter_title}</span>}
          </div>
        </div>
        <span className={styles.badge} data-status={draft.status}>
          {statusLabel(draft.status)}
        </span>
      </div>

      <div className={styles.finalDraft}>
        <header>
          <strong>Latest Draft</strong>
        </header>
        <div className={styles.labelRow}>
          {typeof draft.final_word_count === "number" && <span>{draft.final_word_count} words</span>}
          <span>Cycle {draft.current_cycle}</span>
          <span>Updated {formatDate(draft.last_updated)}</span>
        </div>
        {latestIteration && <pre>{latestIteration.content}</pre>}
      </div>

      {draft.outstanding_feedback.length > 0 && (
        <div>
          <strong>Outstanding Feedback</strong>
          <ul className={styles.outstandingList}>
            {draft.outstanding_feedback.map((item) => (
              <li key={item.id}>{item.message}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <strong>Iteration Timeline</strong>
        <div className={styles.iterationList}>
          {draft.iterations.map((iteration) => (
            <IterationPanel key={iteration.id} iteration={iteration} />
          ))}
        </div>
      </div>
    </article>
  );
}

export default function WritingPage() {
  const router = useRouter();
  const { id } = router.query;

  const [detail, setDetail] = useState<WritingDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [notesDraft, setNotesDraft] = useState("");

  useEffect(() => {
    if (typeof id !== "string") return;
    let active = true;
    setIsLoading(true);
    setError(null);
    setStatusMessage(null);

    fetchWriting(id)
      .then((data) => {
        if (!active) return;
        setDetail(data);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load writing detail");
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [id]);

  const subchapters = useMemo(() => {
    if (!detail) return [] as SubchapterDraftState[];
    const list = detail.batch.subchapters ?? [];
    return [...list].sort((a, b) => {
      const labelA = a.order_label ?? "";
      const labelB = b.order_label ?? "";
      return labelA.localeCompare(labelB, undefined, { numeric: true });
    });
  }, [detail]);

  const handleRun = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (typeof id !== "string") return;
    setIsProcessing(true);
    setError(null);
    setStatusMessage("Running writing loop…");
    try {
      const data = await runWriting(id, notesDraft.trim() || null);
      setDetail(data);
      setStatusMessage("Writing loop completed.");
      setNotesDraft("");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to run writing loop");
    } finally {
      setIsProcessing(false);
    }
  };

  const readiness = detail?.batch.readiness ?? "draft";
  const totalWordCount = detail?.batch.total_word_count;

  return (
    <AppLayout title="Writing Studio">
      <div className={styles.wrapper}>
        <section className={styles.sidebar}>
          <h1>Writing Studio</h1>
          {isLoading ? (
            <p className={styles.status} role="status" aria-live="polite">
              Preparing drafts…
            </p>
          ) : error && !detail ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : detail ? (
            <article className={styles.summaryCard}>
              <header>
                <h2>{detail.project.title ?? "Untitled Project"}</h2>
                <span className={styles.badge} data-status={readiness}>
                  {readiness === "ready" ? "Ready" : "In Progress"}
                </span>
              </header>
              <p className={styles.meta}>Cycle count: {detail.batch.cycle_count}</p>
              {typeof totalWordCount === "number" && (
                <p className={styles.meta}>Total words: {totalWordCount}</p>
              )}
              <p className={styles.meta}>
                Updated {formatDate(detail.batch.updated_at)}
              </p>
              {detail.batch.summary && <p>{detail.batch.summary}</p>}
            </article>
          ) : null}

          <form className={styles.actionForm} onSubmit={handleRun}>
            <label>
              Run Notes (optional)
              <textarea
                value={notesDraft}
                onChange={(event) => setNotesDraft(event.target.value)}
                placeholder="Add guidance for the next writing cycle—tone adjustments, focus areas, or risks."
                disabled={isProcessing || isLoading}
              />
            </label>
            <button type="submit" disabled={isProcessing || isLoading}>
              {isProcessing ? "Running…" : "Run Writing Loop"}
            </button>
          </form>

          {statusMessage && (
            <p className={styles.status} role="status" aria-live="polite">
              {statusMessage}
            </p>
          )}
          {error && detail && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}

          <div className={styles.links}>
            <Link href={`/projects/${id}/guidelines`}>Back to Guidelines</Link>
            <Link href="/">Dashboard</Link>
          </div>
        </section>

        <section className={styles.mainContent}>
          {isLoading && (
            <p className={styles.status} role="status" aria-live="polite">
              Orchestrating drafts…
            </p>
          )}
          {!isLoading && detail && (
            <>
              {detail.batch.summary && (
                <div className={styles.summaryBox}>
                  <h2>Run Summary</h2>
                  <p>{detail.batch.summary}</p>
                </div>
              )}
              {detail.critique && (
                <div className={styles.critiqueBox}>
                  <h2>Critique Highlights</h2>
                  <p>{detail.critique}</p>
                </div>
              )}
              <div className={styles.subchapterGrid}>
                {subchapters.map((draft) => (
                  <SubchapterCard key={draft.subchapter_id} draft={draft} />
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
