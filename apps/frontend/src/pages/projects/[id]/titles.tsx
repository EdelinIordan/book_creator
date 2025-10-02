import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { AppLayout } from "../../../layout/AppLayout";
import {
  fetchTitles,
  regenerateTitles,
  selectTitle,
  TitleDetail,
  updateTitleShortlist,
} from "../../../lib/api";
import styles from "./titles.module.css";

export default function TitleIdeationPage() {
  const router = useRouter();
  const { id } = router.query;
  const [detail, setDetail] = useState<TitleDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [titleDraft, setTitleDraft] = useState<string>("");

  const shortlist = useMemo(() => detail?.shortlist ?? [], [detail?.shortlist]);
  const options = detail?.options ?? [];

  useEffect(() => {
    if (typeof id !== "string") return;

    let active = true;
    setIsLoading(true);
    setError(null);
    setStatusMessage(null);

    fetchTitles(id)
      .then((data) => {
        if (active) {
          setDetail(data);
          const baseTitle = data.selected_title ?? data.shortlist[0] ?? null;
          setSelected(baseTitle);
          setTitleDraft(baseTitle ?? "");
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load titles");
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
    setError(null);
    setStatusMessage("Regenerating title options…");
    try {
      const data = await regenerateTitles(id);
      setDetail(data);
      const baseTitle = data.selected_title ?? data.shortlist[0] ?? null;
      setSelected(baseTitle);
      setTitleDraft(baseTitle ?? "");
      setStatusMessage("New titles generated.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to regenerate titles");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleToggleShortlist = async (title: string) => {
    if (typeof id !== "string" || isProcessing) return;
    setIsProcessing(true);
    setError(null);
    const nextShortlist = shortlist.includes(title)
      ? shortlist.filter((item) => item !== title)
      : [...shortlist, title];
    try {
      const data = await updateTitleShortlist(id, nextShortlist);
      setDetail(data);
      if (!data.selected_title) {
        const nextSelected = selected && data.shortlist.includes(selected)
          ? selected
          : data.shortlist[0] ?? null;
        setSelected(nextSelected);
        setTitleDraft(nextSelected ?? "");
      } else {
        setSelected(data.selected_title);
        setTitleDraft(data.selected_title ?? "");
      }
      setStatusMessage("Shortlist updated.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to update shortlist");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSelect = (title: string) => {
    setSelected(title);
    setTitleDraft(title);
  };

  const handleConfirm = async () => {
    const trimmedTitle = titleDraft.trim();
    if (typeof id !== "string" || !trimmedTitle) return;
    setIsProcessing(true);
    setError(null);
    setStatusMessage("Confirming final title…");
    try {
      const data = await selectTitle(id, trimmedTitle);
      setDetail(data);
      const confirmed = data.selected_title ?? trimmedTitle;
      setSelected(confirmed);
      setTitleDraft(confirmed);
      setStatusMessage("Title confirmed. Research prompts are next.");
    } catch (err) {
      setStatusMessage(null);
      setError(err instanceof Error ? err.message : "Failed to confirm title");
    } finally {
      setIsProcessing(false);
    }
  };

  const projectStage = detail?.project.stage ?? "TITLE";
  const isConfirmed = projectStage !== "TITLE";
  const canConfirm = Boolean(titleDraft.trim()) && !isConfirmed;
  const finalTitle = detail?.selected_title ?? titleDraft || selected;

  return (
    <AppLayout title="Title Ideation">
      <div className={styles.wrapper}>
        <section className={styles.infoPane}>
          <h1>Title Ideation</h1>
          <p>Review AI-generated titles, shortlist your favourites, and confirm the one that fits best.</p>

          <div className={styles.actions}>
            <button
              type="button"
              onClick={handleRegenerate}
              disabled={isProcessing || isLoading || isConfirmed}
            >
              Regenerate Titles
            </button>
            <button
              type="button"
              disabled={!canConfirm || isProcessing || isLoading}
              className={styles.primary}
              onClick={handleConfirm}
            >
              {isConfirmed ? "Title Confirmed" : "Confirm Final Title"}
            </button>
          </div>

          <div className={styles.selectedBox}>
            <h2>Final Selection</h2>
            {finalTitle ? <p>{finalTitle}</p> : <p>No title selected yet.</p>}
          </div>

          {!isConfirmed && (
            <div className={styles.editorBox}>
              <h2>Edit Title Before Confirming</h2>
              <label>
                <span>Title text</span>
                <input
                  type="text"
                  value={titleDraft}
                  onChange={(event) => setTitleDraft(event.target.value)}
                  placeholder="Refine or customise the selected title"
                  disabled={isProcessing || isLoading}
                />
              </label>
              <p className={styles.helperText}>
                Adjust wording to taste; the confirmed value will feed every downstream stage.
              </p>
            </div>
          )}

          <div className={styles.shortlistBox}>
            <h2>Shortlist</h2>
            {shortlist.length === 0 ? (
              <p>No titles shortlisted.</p>
            ) : (
              <ul>
                {shortlist.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>

          {detail?.critique && (
            <div className={styles.critiqueBox}>
              <h2>Critique Notes</h2>
              <p>{detail.critique}</p>
            </div>
          )}

          {statusMessage && (
            <p className={styles.status} role="status" aria-live="polite">
              {statusMessage}
            </p>
          )}
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
        </section>

        <section className={styles.grid}>
          {isLoading && (
            <p className={styles.status} role="status" aria-live="polite">
              Loading title options…
            </p>
          )}
          {error && !isLoading && detail === null && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
          {!isLoading && detail && (
            options.map((option) => {
              const isShortlisted = shortlist.includes(option.title);
              const isSelected = selected === option.title || detail.selected_title === option.title;
              return (
                <article key={option.title} className={styles.card}>
                  <header>
                    <h2>{option.title}</h2>
                  </header>
                  <p>{option.rationale}</p>
                  <div className={styles.cardActions}>
                    <button type="button" onClick={() => handleSelect(option.title)} disabled={isConfirmed}>
                      {isSelected ? "Selected" : "Select"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleToggleShortlist(option.title)}
                      className={isShortlisted ? styles.shortlisted : ""}
                      disabled={isConfirmed}
                    >
                      {isShortlisted ? "Remove from shortlist" : "Add to shortlist"}
                    </button>
                  </div>
                </article>
              );
            })
          )}
        </section>

        <footer className={styles.footerLinks}>
          <Link href={`/projects/${id}/structure`}>Back to Structure</Link>
          <Link href="/">Dashboard</Link>
        </footer>
      </div>
    </AppLayout>
  );
}
