import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { AppLayout } from "../../../layout/AppLayout";
import {
  fetchFactMapping,
  fetchStructure,
  FactMappingDetail,
  MappedFact,
  FactCoverage,
} from "../../../lib/api";
import styles from "./facts.module.css";

type SubchapterMeta = {
  chapterTitle: string;
  chapterOrder: number;
  subchapterTitle: string;
  subOrder: number;
  orderLabel: string;
};

type CoverageWithMeta = FactCoverage & { meta?: SubchapterMeta };

export default function FactMappingPage() {
  const router = useRouter();
  const { id } = router.query;

  const [detail, setDetail] = useState<FactMappingDetail | null>(null);
  const [structureLookup, setStructureLookup] = useState<Record<string, SubchapterMeta>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSubchapter, setSelectedSubchapter] = useState<string>("all");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (typeof id !== "string") return;
    let active = true;
    setIsLoading(true);
    setError(null);
    setStatusMessage("Loading fact mapping…");

    fetchFactMapping(id)
      .then((data) => {
        if (!active) return;
        setDetail(data);
        setStatusMessage(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load fact mapping");
        setStatusMessage(null);
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
        const lookup: Record<string, SubchapterMeta> = {};
        structure.structure.chapters.forEach((chapter) => {
          chapter.subchapters.forEach((sub) => {
            lookup[sub.id] = {
              chapterTitle: chapter.title,
              chapterOrder: chapter.order,
              subchapterTitle: sub.title,
              subOrder: sub.order,
              orderLabel: `${chapter.order}.${sub.order}`,
            };
          });
        });
        setStructureLookup(lookup);
      })
      .catch(() => {
        setStructureLookup({});
      });
  }, [id, detail]);

  const coverage = useMemo<CoverageWithMeta[]>(() => {
    if (!detail) return [];
    return detail.coverage
      .map((item) => ({
        ...item,
        meta: structureLookup[item.subchapter_id],
      }))
      .sort((a, b) => {
        const metaA = a.meta;
        const metaB = b.meta;
        if (metaA && metaB) {
          if (metaA.chapterOrder !== metaB.chapterOrder) {
            return metaA.chapterOrder - metaB.chapterOrder;
          }
          return metaA.subOrder - metaB.subOrder;
        }
        return a.subchapter_id.localeCompare(b.subchapter_id);
      });
  }, [detail, structureLookup]);

  const totalFacts = detail?.facts?.length ?? 0;

  const uncovered = useMemo(() => coverage.filter((item) => item.fact_count === 0), [coverage]);

  const filteredFacts = useMemo(() => {
    const list = detail?.facts ?? [];
    if (selectedSubchapter === "all") {
      return list;
    }
    return list.filter((fact) => fact.subchapter_id === selectedSubchapter);
  }, [detail, selectedSubchapter]);

  const projectStage = detail?.project.stage ?? "FACT_MAPPING";
  const stageUnlocked = projectStage !== "FACT_MAPPING";

  const nextStageLink = useMemo(() => {
    if (!detail) return null;
    if (projectStage === "GUIDELINES" || projectStage === "WRITING" || projectStage === "COMPLETE") {
      return {
        href: `/projects/${detail.project.id}/guidelines`,
        label: "Open Guidelines",
      };
    }
    if (projectStage === "EMOTIONAL") {
      return {
        href: `/projects/${detail.project.id}/emotional`,
        label: "Open Emotional Layer",
      };
    }
    return null;
  }, [detail, projectStage]);

  return (
    <AppLayout title="Research Fact Map">
      <div className={styles.wrapper}>
        <section className={styles.sidebar}>
          <h1>Research Fact Map</h1>
          {isLoading ? (
            <p className={styles.status} role="status" aria-live="polite">
              Gathering mapped facts…
            </p>
          ) : error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : detail ? (
            <>
              <p>
                Project title: <strong>{detail.project.title ?? "Untitled Project"}</strong>
              </p>
              <p className={styles.meta}>Updated {new Date(detail.updated_at).toLocaleString()}</p>
              <p className={styles.meta}>
                Stage: <strong>{detail.project.stage_label}</strong>
              </p>
              {stageUnlocked && (
                <div className={styles.stageBanner} role="status" aria-live="polite">
                  Fact mapping complete — emotional layer is unlocked.
                </div>
              )}
              {detail.critique && (
                <div className={styles.critiqueBox}>
                  <h2>Critique Notes</h2>
                  <p>{detail.critique}</p>
                </div>
              )}
              <label className={styles.filterField}>
                Filter by subchapter
                <select
                  value={selectedSubchapter}
                  onChange={(event) => setSelectedSubchapter(event.target.value)}
                >
                  <option value="all">All subchapters</option>
                  {coverage.map((item) => {
                    const meta = item.meta;
                    const label = meta ? `${meta.orderLabel} ${meta.subchapterTitle}` : item.subchapter_id;
                    return (
                      <option key={item.subchapter_id} value={item.subchapter_id}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </label>
              <div className={styles.coverageList}>
                <h2>Coverage Overview</h2>
                <ul>
                  {coverage.map((item) => {
                    const meta = item.meta;
                    const label = meta ? `${meta.orderLabel} ${meta.subchapterTitle}` : item.subchapter_id;
                    return (
                      <li key={item.subchapter_id} data-empty={item.fact_count === 0 ? "true" : "false"}>
                        <span>{label}</span>
                        <span>{item.fact_count} facts</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
              {uncovered.length > 0 && (
                <div className={styles.alertBox}>
                  <h3>Needs mapping attention</h3>
                  <p>
                    {uncovered.length === 1
                      ? "1 subchapter still needs mapped facts."
                      : `${uncovered.length} subchapters still need mapped facts.`}
                  </p>
                  <ul>
                    {uncovered.map((item) => {
                      const meta = item.meta;
                      const label = meta ? `${meta.orderLabel} ${meta.subchapterTitle}` : item.subchapter_id;
                      return <li key={item.subchapter_id}>{label}</li>;
                    })}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className={styles.status} role="status" aria-live="polite">
              No fact mapping data found.
            </p>
          )}

          {statusMessage && (
            <p className={styles.status} role="status" aria-live="polite">
              {statusMessage}
            </p>
          )}

          <div className={styles.links}>
            <Link href={`/projects/${id}/research`}>Back to Research</Link>
            {nextStageLink && <Link href={nextStageLink.href}>{nextStageLink.label}</Link>}
            <Link href="/">Dashboard</Link>
          </div>
        </section>

        <section className={styles.mainContent}>
          {isLoading && (
            <p className={styles.status} role="status" aria-live="polite">
              Preparing fact list…
            </p>
          )}
          {!isLoading && !error && detail && (
            <>
              <h2 className={styles.sectionHeading}>
                {selectedSubchapter === "all"
                  ? `Mapped Facts (${totalFacts})`
                  : `Mapped Facts for ${structureLookup[selectedSubchapter]?.orderLabel ?? "Selected"}`}
              </h2>
              {filteredFacts.length === 0 ? (
                <p className={styles.status} role="status" aria-live="polite">
                  No facts mapped yet for this selection.
                </p>
              ) : (
                <div className={styles.factGrid}>
                  {filteredFacts.map((fact) => (
                    <FactCard key={fact.id} fact={fact} meta={structureLookup[fact.subchapter_id]} />
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </AppLayout>
  );
}

function FactCard({ fact, meta }: { fact: MappedFact; meta?: SubchapterMeta }) {
  const header = meta ? `${meta.orderLabel} ${meta.subchapterTitle}` : fact.subchapter_id;
  const chapterTitle = meta?.chapterTitle;
  return (
    <article className={styles.factCard}>
      <header className={styles.factHeader}>
        <h3>{header}</h3>
        {chapterTitle && <span className={styles.meta}>Chapter: {chapterTitle}</span>}
        <span className={styles.meta}>Recorded {new Date(fact.created_at).toLocaleString()}</span>
      </header>
      <p className={styles.factSummary}>{fact.summary}</p>
      <details>
        <summary>Source detail</summary>
        <p>{fact.detail}</p>
      </details>
      <footer className={styles.factFooter}>
        <span>{formatCitation(fact.citation)}</span>
        {typeof fact.prompt_index === "number" && (
          <span>Prompt #{fact.prompt_index + 1}</span>
        )}
      </footer>
    </article>
  );
}

function formatCitation(citation: MappedFact["citation"]): string {
  const parts: string[] = [];
  if (citation.source_title) parts.push(citation.source_title);
  if (citation.author) parts.push(citation.author);
  if (citation.publication_date) parts.push(citation.publication_date);
  if (citation.page) parts.push(`p. ${citation.page}`);
  if (citation.source_type) parts.push(citation.source_type.replace(/_/g, " "));
  return parts.join(" • ");
}
