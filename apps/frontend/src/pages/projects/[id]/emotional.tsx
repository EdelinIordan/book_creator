import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { AppLayout } from "../../../layout/AppLayout";
import {
  EmotionalEntry,
  EmotionalLayerDetail,
  fetchEmotionalLayer,
  fetchStructure,
  regenerateEmotionalLayer,
} from "../../../lib/api";
import styles from "./emotional.module.css";

interface SubchapterLookup {
  [subchapterId: string]: {
    chapterTitle: string;
    subchapterTitle: string;
    orderLabel: string;
  };
}

export default function EmotionalLayerPage() {
  const router = useRouter();
  const { id } = router.query;

  const [detail, setDetail] = useState<EmotionalLayerDetail | null>(null);
  const [structureLookup, setStructureLookup] = useState<SubchapterLookup>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [personaDraft, setPersonaDraft] = useState<string>("");

  useEffect(() => {
    if (typeof id !== "string") return;
    let active = true;
    setIsLoading(true);
    setError(null);
    setStatusMessage(null);

    fetchEmotionalLayer(id)
      .then((data) => {
        if (!active) return;
        setDetail(data);
        setPersonaDraft("");
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load emotional layer");
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
        structure.structure.chapters.forEach((chapter) => {
          chapter.subchapters.forEach((sub) => {
            const orderLabel = `${chapter.order}.${sub.order}`;
            lookup[sub.id] = {
              chapterTitle: chapter.title,
              subchapterTitle: sub.title,
              orderLabel,
            };
          });
        });
        setStructureLookup(lookup);
      })
      .catch(() => {
        // Non-critical; leave lookup empty if structure fetch fails.
        setStructureLookup({});
      });
  }, [id, detail]);

  const entries = useMemo(() => detail?.entries ?? [], [detail?.entries]);

  const handleRegenerate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (typeof id !== "string") return;
    setIsProcessing(true);
    setError(null);
    setStatusMessage("Refreshing emotional layer…");
    try {
      const data = await regenerateEmotionalLayer(id, personaDraft.trim() || null);
      setDetail(data);
      setStatusMessage("Emotional layer updated.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to regenerate emotional layer");
    } finally {
      setIsProcessing(false);
    }
  };

  const stage = detail?.project.stage ?? "EMOTIONAL";
  const persona = detail?.persona;
  const critique = detail?.critique;

  return (
    <AppLayout title="Story Weave Lab">
      <div className={styles.wrapper}>
        <section className={styles.sidebar}>
          <h1>Story Weave Lab</h1>
          {isLoading ? (
            <p className={styles.status} role="status" aria-live="polite">
              Gathering persona context…
            </p>
          ) : error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : persona ? (
            <article className={styles.personaCard}>
              <h2>{persona.name}</h2>
              <p className={styles.meta}>{persona.voice}</p>
              <p>{persona.background}</p>
              {persona.signature_themes.length > 0 && (
                <div>
                  <h3>Signature Themes</h3>
                  <ul className={styles.badgeList}>
                    {persona.signature_themes.map((theme) => (
                      <li key={theme}>{theme}</li>
                    ))}
                  </ul>
                </div>
              )}
              {persona.guiding_principles.length > 0 && (
                <div>
                  <h3>Guiding Principles</h3>
                  <ul className={styles.badgeList}>
                    {persona.guiding_principles.map((principle) => (
                      <li key={principle}>{principle}</li>
                    ))}
                  </ul>
                </div>
              )}
            </article>
          ) : (
            <p className={styles.status} role="status" aria-live="polite">
              No persona data available.
            </p>
          )}

          <form className={styles.guidanceForm} onSubmit={handleRegenerate}>
            <label>
              Persona Preferences (optional)
              <textarea
                value={personaDraft}
                onChange={(event) => setPersonaDraft(event.target.value)}
                placeholder="Share tone adjustments, continuity reminders, or thematic cues for regeneration."
                disabled={isProcessing || isLoading}
              />
            </label>
            <button type="submit" disabled={isProcessing || isLoading}>
              {isProcessing ? "Updating…" : "Regenerate Emotional Layer"}
            </button>
          </form>

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

          {(stage === "GUIDELINES" || stage === "WRITING") && (
            <div className={styles.stageBanner} role="status" aria-live="polite">
              Emotional layer locked in — {" "}
              <Link href={`/projects/${id}/guidelines`}>open the guideline studio</Link> to brief the writing crew.
            </div>
          )}

          <div className={styles.links}>
            <Link href={`/projects/${id}/research`}>Back to Research</Link>
            <Link href="/">Dashboard</Link>
          </div>
        </section>

        <section className={styles.mainContent}>
          {isLoading && (
            <p className={styles.status} role="status" aria-live="polite">
              Formatting emotional entries…
            </p>
          )}
          {!isLoading && detail && (
            <>
              {critique && (
                <div className={styles.critiqueBox}>
                  <h2>Critique Notes</h2>
                  <p>{critique}</p>
                </div>
              )}
              <div className={styles.entriesGrid}>
                {entries.map((entry) => (
                  <EmotionalEntryCard
                    key={entry.id}
                    entry={entry}
                    lookup={structureLookup}
                  />
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </AppLayout>
  );
}

function EmotionalEntryCard({
  entry,
  lookup,
}: {
  entry: EmotionalEntry;
  lookup: SubchapterLookup;
}) {
  const metadata = lookup[entry.subchapter_id];
  const header = metadata
    ? `${metadata.orderLabel} ${metadata.subchapterTitle}`
    : `Subchapter ${entry.subchapter_id}`;
  const chapterTitle = metadata?.chapterTitle;
  const formatRole = (value: string) =>
    value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");

  return (
    <article className={styles.entryCard}>
      <header className={styles.entryHeader}>
        <h3>{header}</h3>
        {chapterTitle && <span className={styles.meta}>Chapter: {chapterTitle}</span>}
        <span className={styles.meta}>
          Authored by {formatRole(entry.created_by)}
        </span>
      </header>
      <p>{entry.story_hook}</p>
      {entry.persona_note && <p className={styles.meta}>Persona Note: {entry.persona_note}</p>}
      {entry.analogy && <p className={styles.meta}>Analogy: {entry.analogy}</p>}
      {entry.emotional_goal && <p className={styles.meta}>Emotional Goal: {entry.emotional_goal}</p>}
    </article>
  );
}
