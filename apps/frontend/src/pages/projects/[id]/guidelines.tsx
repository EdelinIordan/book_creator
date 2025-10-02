import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { AppLayout } from "../../../layout/AppLayout";
import {
  fetchGuidelines,
  fetchStructure,
  GuidelineDetail,
  GuidelinePacket,
  regenerateGuidelines,
} from "../../../lib/api";
import styles from "./guidelines.module.css";

type SubchapterLookup = {
  [subchapterId: string]: {
    chapterId: string;
    chapterTitle: string;
    subchapterTitle: string;
    orderLabel: string;
    chapterOrder: number;
    subOrder: number;
  };
};

type ChapterOption = {
  id: string;
  title: string;
  order: number;
};

export default function GuidelinesPage() {
  const router = useRouter();
  const { id } = router.query;

  const [detail, setDetail] = useState<GuidelineDetail | null>(null);
  const [structureLookup, setStructureLookup] = useState<SubchapterLookup>({});
  const [chapterOptions, setChapterOptions] = useState<ChapterOption[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<string>("all");
  const [preferencesDraft, setPreferencesDraft] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (typeof id !== "string") return;
    let active = true;
    setIsLoading(true);
    setError(null);
    setStatusMessage(null);

    fetchGuidelines(id)
      .then((data) => {
        if (!active) return;
        setDetail(data);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load guidelines");
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

  useEffect(() => {
    if (typeof id !== "string" || !detail) return;

    fetchStructure(id)
      .then((structure) => {
        const lookup: SubchapterLookup = {};
        const chapters: ChapterOption[] = [];

        structure.structure.chapters.forEach((chapter) => {
          chapters.push({ id: chapter.id, title: chapter.title, order: chapter.order });
          chapter.subchapters.forEach((sub) => {
            lookup[sub.id] = {
              chapterId: chapter.id,
              chapterTitle: chapter.title,
              subchapterTitle: sub.title,
              orderLabel: `${chapter.order}.${sub.order}`,
              chapterOrder: chapter.order,
              subOrder: sub.order,
            };
          });
        });

        chapters.sort((a, b) => a.order - b.order);
        setStructureLookup(lookup);
        setChapterOptions(chapters);
      })
      .catch(() => {
        setStructureLookup({});
        setChapterOptions([]);
      });
  }, [id, detail]);

  const guidelines = useMemo(() => {
    const packets = detail?.guidelines ?? [];
    const sorted = [...packets].sort((a, b) => {
      const metaA = structureLookup[a.subchapter_id];
      const metaB = structureLookup[b.subchapter_id];
      if (!metaA || !metaB) {
        return a.subchapter_id.localeCompare(b.subchapter_id);
      }
      if (metaA.chapterOrder !== metaB.chapterOrder) {
        return metaA.chapterOrder - metaB.chapterOrder;
      }
      return metaA.subOrder - metaB.subOrder;
    });

    if (selectedChapter === "all") {
      return sorted;
    }
    return sorted.filter((packet) => structureLookup[packet.subchapter_id]?.chapterId === selectedChapter);
  }, [detail?.guidelines, structureLookup, selectedChapter]);

  const handleRegenerate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (typeof id !== "string") return;
    setIsProcessing(true);
    setError(null);
    setStatusMessage("Refreshing creative guidelines…");
    try {
      const data = await regenerateGuidelines(id, preferencesDraft.trim() || null);
      setDetail(data);
      setStatusMessage("Guidelines updated.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to regenerate guidelines");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExportGuidelines = () => {
    if (!detail) return;
    try {
      const payload = {
        project: {
          id: detail.project.id,
          title: detail.project.title,
          stage: detail.project.stage_label,
          updated_at: detail.updated_at,
        },
        guidelines: detail.guidelines,
        summary: detail.summary,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const filename = detail.project.title
        ? detail.project.title.replace(/[^a-z0-9-_]+/gi, "-").toLowerCase()
        : `project-${detail.project.id}`;
      link.download = `${filename}-guidelines.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setStatusMessage("Guidelines exported as JSON.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to export guidelines");
    }
  };

  const stage = detail?.project.stage ?? "GUIDELINES";
  const readiness = detail?.readiness ?? "draft";
  const version = detail?.version ?? detail?.project.guideline_version ?? 1;

  const readinessLabel = readiness === "ready" ? "Ready for Writing" : "In Progress";

  return (
    <AppLayout title="Guideline Studio">
      <div className={styles.wrapper}>
        <section className={styles.sidebar}>
          <h1>Guideline Studio</h1>
          {detail ? (
            <article className={styles.summaryCard}>
              <header>
                <h2>{detail.project.title ?? "Untitled Project"}</h2>
                <span className={styles.readinessBadge} data-status={readiness}>
                  {readinessLabel}
                </span>
              </header>
              <p className={styles.meta}>Version {version}</p>
              <p className={styles.meta}>
                Updated {detail ? new Date(detail.updated_at).toLocaleString() : "–"}
              </p>
              {detail.summary && <p className={styles.summaryText}>{detail.summary}</p>}
            </article>
          ) : isLoading ? (
            <p className={styles.status} role="status" aria-live="polite">
              Loading guidelines…
            </p>
          ) : error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}

          <form className={styles.guidanceForm} onSubmit={handleRegenerate}>
            <label>
              Preference Notes (optional)
              <textarea
                value={preferencesDraft}
                onChange={(event) => setPreferencesDraft(event.target.value)}
                placeholder="Share tone tweaks, structural priorities, or success criteria for regeneration."
                disabled={isProcessing || isLoading}
              />
            </label>
            <button type="submit" disabled={isProcessing || isLoading}>
              {isProcessing ? "Updating…" : "Regenerate Guidelines"}
            </button>
          </form>

          <button
            type="button"
            className={styles.secondaryButton}
            onClick={handleExportGuidelines}
            disabled={isLoading || !detail}
          >
            Export guidelines (JSON)
          </button>

          {statusMessage && (
            <p className={styles.status} role="status" aria-live="polite">
              {statusMessage}
            </p>
          )}
          {error && !isLoading && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}

          {detail?.critique && (
            <div className={styles.critiqueBox}>
              <h3>Critic Highlights</h3>
              <p>{detail.critique}</p>
            </div>
          )}

          {stage === "WRITING" && (
            <div className={styles.stageBanner} role="status" aria-live="polite">
              Guidelines locked. All set to open the Writing Studio once ready.
            </div>
          )}

          <div className={styles.links}>
            <Link href={`/projects/${id}/emotional`}>Back to Emotional Layer</Link>
            <Link href="/">Dashboard</Link>
          </div>
        </section>

        <section className={styles.mainContent}>
          {isLoading && (
            <p className={styles.status} role="status" aria-live="polite">
              Preparing creative directives…
            </p>
          )}
          {!isLoading && detail && (
            <>
              <div className={styles.controls}>
                <label>
                  Chapter Filter
                  <select
                    value={selectedChapter}
                    onChange={(event) => setSelectedChapter(event.target.value)}
                  >
                    <option value="all">All chapters</option>
                    {chapterOptions.map((chapter) => (
                      <option key={chapter.id} value={chapter.id}>
                        {chapter.order}. {chapter.title}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className={styles.guidelineList}>
                {guidelines.map((packet) => (
                  <GuidelineCard
                    key={packet.id}
                    packet={packet}
                    metadata={structureLookup[packet.subchapter_id]}
                  />
                ))}
                {guidelines.length === 0 && (
                  <p className={styles.status} role="status" aria-live="polite">
                    No guideline packets match the current filter.
                  </p>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </AppLayout>
  );
}

function GuidelineCard({
  packet,
  metadata,
}: {
  packet: GuidelinePacket;
  metadata?: SubchapterLookup[string];
}) {
  const header = metadata
    ? `${metadata.orderLabel} ${metadata.subchapterTitle}`
    : `Subchapter ${packet.subchapter_id}`;
  const chapterTitle = metadata?.chapterTitle;

  const formatRole = (value: string) =>
    value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");

  return (
    <article className={styles.guidelineCard}>
      <header className={styles.cardHeader}>
        <div>
          <h3>{header}</h3>
          {chapterTitle && <p className={styles.meta}>{chapterTitle}</p>}
        </div>
        <div className={styles.badges}>
          <span className={styles.statusBadge}>{packet.status.toUpperCase()}</span>
          <span className={styles.meta}>v{packet.version}</span>
        </div>
      </header>

      <section className={styles.cardSection}>
        <h4>Objectives</h4>
        <ul>
          {packet.objectives.map((objective) => (
            <li key={objective}>{objective}</li>
          ))}
        </ul>
      </section>

      {packet.must_include_facts.length > 0 && (
        <section className={styles.cardSection}>
          <h4>Must-Include Facts</h4>
          <ul className={styles.factList}>
            {packet.must_include_facts.map((fact) => (
              <li key={fact.fact_id}>
                <strong>{fact.summary}</strong>
                <div className={styles.meta}>{formatCitation(fact.citation)}</div>
                {fact.rationale && <p className={styles.meta}>{fact.rationale}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {packet.emotional_beats.length > 0 && (
        <section className={styles.cardSection}>
          <h4>Emotional Beats</h4>
          <ul>
            {packet.emotional_beats.map((beat) => (
              <li key={beat}>{beat}</li>
            ))}
          </ul>
        </section>
      )}

      {packet.structural_reminders.length > 0 && (
        <section className={styles.cardSection}>
          <h4>Structural Reminders</h4>
          <ul>
            {packet.structural_reminders.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      )}

      {packet.success_metrics.length > 0 && (
        <section className={styles.cardSection}>
          <h4>Success Metrics</h4>
          <ul>
            {packet.success_metrics.map((metric) => (
              <li key={metric}>{metric}</li>
            ))}
          </ul>
        </section>
      )}

      {packet.risks.length > 0 && (
        <section className={styles.cardSection}>
          <h4>Risks to Watch</h4>
          <ul>
            {packet.risks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
        </section>
      )}

      <footer className={styles.cardFooter}>
        <span className={styles.meta}>{formatRole(packet.created_by)}</span>
        <span className={styles.meta}>
          Updated {new Date(packet.updated_at).toLocaleString()}
        </span>
      </footer>
    </article>
  );
}

function formatCitation(citation: {
  source_title: string;
  author: string | null;
  publication_date: string | null;
  url: string | null;
  page: string | null;
  source_type: string | null;
}): string {
  const parts: string[] = [];
  if (citation.source_title) parts.push(citation.source_title);
  if (citation.author) parts.push(citation.author);
  if (citation.publication_date) parts.push(citation.publication_date);
  if (citation.page) parts.push(`p. ${citation.page}`);
  if (citation.source_type) parts.push(citation.source_type.replace(/_/g, " "));
  return parts.join(" • ");
}
