import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { AppLayout } from "../../../layout/AppLayout";
import { StructureTimeline } from "../../../components/StructureTimeline";
import {
  approveStructure,
  fetchStructure,
  regenerateStructure,
  StructureDetail,
} from "../../../lib/api";
import styles from "./structure.module.css";

export default function StructureLabPage() {
  const router = useRouter();
  const { id } = router.query;
  const [activeTab, setActiveTab] = useState<"structure" | "json">("structure");
  const [detail, setDetail] = useState<StructureDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const structureJson = useMemo(() => {
    return detail ? JSON.stringify(detail.structure, null, 2) : "";
  }, [detail]);

  useEffect(() => {
    if (typeof id !== "string") return;

    let active = true;
    setIsLoading(true);
    setError(null);
    setStatusMessage(null);
    fetchStructure(id)
      .then((data) => {
        if (active) {
          setDetail(data);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load structure");
        }
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

  const handleRegenerate = async () => {
    if (typeof id !== "string") return;
    setIsProcessing(true);
    setStatusMessage("Regenerating structure with current idea summary…");
    try {
      const updated = await regenerateStructure(id);
      setDetail(updated);
      setStatusMessage("Structure regenerated successfully.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to regenerate structure");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApprove = async () => {
    if (typeof id !== "string") return;
    setIsProcessing(true);
    setStatusMessage("Approving structure…");
    try {
      const project = await approveStructure(id);
      setDetail((prev) => (prev ? { ...prev, project } : prev));
      setStatusMessage("Structure approved. Title ideation is unlocked.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to approve structure");
    } finally {
      setIsProcessing(false);
    }
  };

  const ideaSummary = detail?.project.idea_summary ?? "";
  const canApprove = detail?.project.stage === "STRUCTURE";

  return (
    <AppLayout title="Structure Lab">
      <div className={styles.wrapper}>
        <section className={styles.sidebar}>
          <h1>Structure Lab</h1>
          {isLoading ? (
            <p className={styles.status} role="status" aria-live="polite">
              Loading project details…
            </p>
          ) : error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : (
            <p>
              Idea summary: <strong>{ideaSummary}</strong>
            </p>
          )}
          <div className={styles.actions}>
            <button type="button" onClick={handleApprove} disabled={!canApprove || isProcessing || isLoading}>
              {canApprove ? "Approve Structure" : "Structure Approved"}
            </button>
            <button
              type="button"
              className={styles.secondary}
              onClick={handleRegenerate}
              disabled={isProcessing || isLoading}
            >
              Request Regeneration
            </button>
          </div>
          <div className={styles.llmSelector}>
            <h2>LLM Overrides</h2>
            <p className={styles.hint}>Coming soon: configure per-stage models directly from this view.</p>
          </div>
          {statusMessage && (
            <p className={styles.status} role="status" aria-live="polite">
              {statusMessage}
            </p>
          )}
        </section>

        <section className={styles.mainContent}>
          <div className={styles.tabs}>
            <button
              className={activeTab === "structure" ? styles.activeTab : ""}
              onClick={() => setActiveTab("structure")}
              type="button"
              disabled={isLoading || !!error}
            >
              Structure View
            </button>
            <button
              className={activeTab === "json" ? styles.activeTab : ""}
              onClick={() => setActiveTab("json")}
              type="button"
              disabled={isLoading || !!error}
            >
              Raw JSON
            </button>
          </div>

          {isLoading && (
            <p className={styles.status} role="status" aria-live="polite">
              Preparing outline…
            </p>
          )}
          {error && !isLoading && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}

          {!isLoading && !error && detail && (
            <>
              {activeTab === "structure" ? (
                <div className={styles.structureGrid}>
                  {detail.structure.chapters.map((chapter) => (
                    <article key={chapter.id} className={styles.chapterCard}>
                      <header>
                        <h2>
                          {chapter.order}. {chapter.title}
                        </h2>
                        <p>{chapter.summary}</p>
                      </header>
                      <ul>
                        {chapter.subchapters.map((sub) => (
                          <li key={sub.id}>
                            <strong>
                              {chapter.order}.{sub.order} {sub.title}
                            </strong>
                            <p>{sub.summary}</p>
                          </li>
                        ))}
                      </ul>
                    </article>
                  ))}
                </div>
              ) : (
                <pre className={styles.jsonBlock}>{structureJson}</pre>
              )}

              <section>
                <h2>Agent Iterations</h2>
                <StructureTimeline iterations={detail.iterations} />
              </section>
            </>
          )}

          <footer className={styles.footerLinks}>
            <Link href="/">Back to Dashboard</Link>
          </footer>
        </section>
      </div>
    </AppLayout>
  );
}
