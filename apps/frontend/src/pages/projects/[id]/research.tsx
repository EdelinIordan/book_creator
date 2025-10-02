import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { AppLayout } from "../../../layout/AppLayout";
import {
  fetchResearch,
  registerResearchUpload,
  regenerateResearch,
  ResearchDetail,
  ResearchPrompt,
  ResearchUpload,
} from "../../../lib/api";
import styles from "./research.module.css";

export default function ResearchDashboardPage() {
  const router = useRouter();
  const { id } = router.query;

  const [detail, setDetail] = useState<ResearchDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [guidelinesDraft, setGuidelinesDraft] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);

  const showStatus = (message: string | null) => {
    setStatusMessage(message);
    if (message) {
      setError(null);
    }
  };

  useEffect(() => {
    if (typeof id !== "string") return;

    let active = true;
    setIsLoading(true);
    setError(null);
    showStatus(null);

    fetchResearch(id)
      .then((data) => {
        if (!active) return;
        setDetail(data);
        setGuidelinesDraft(data.guidelines ?? "");
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load research prompts");
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

  const prompts = detail?.prompts ?? [];
  const uploads = detail?.uploads ?? [];

  const uploadsByPrompt = useMemo(() => {
    const currentUploads = detail?.uploads ?? [];
    return currentUploads.reduce<Record<number, ResearchUpload[]>>((acc, upload) => {
      if (!acc[upload.prompt_index]) {
        acc[upload.prompt_index] = [];
      }
      acc[upload.prompt_index].push(upload);
      return acc;
    }, {});
  }, [detail?.uploads]);

  const handleRegenerate = async (event: FormEvent) => {
    event.preventDefault();
    if (typeof id !== "string") return;
    setIsProcessing(true);
    setError(null);
    showStatus("Regenerating research prompts…");
    try {
      const data = await regenerateResearch(id, guidelinesDraft.trim() || null);
      setDetail(data);
      showStatus("Research prompts refreshed.");
    } catch (err) {
      showStatus(null);
      setError(err instanceof Error ? err.message : "Failed to regenerate prompts");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUpload = async (
    promptIndex: number,
    payload: { filename: string; notes?: string; base64: string }
  ) => {
    if (typeof id !== "string") return;
    setIsProcessing(true);
    setError(null);
    showStatus("Saving upload metadata…");
    try {
      const data = await registerResearchUpload(id, {
        prompt_index: promptIndex,
        filename: payload.filename,
        notes: payload.notes,
        content_base64: payload.base64,
      });
      setDetail(data);
      showStatus("Upload recorded. You can proceed to fact mapping once all prompts are covered.");
    } catch (err) {
      showStatus(null);
      setError(err instanceof Error ? err.message : "Failed to record upload");
    } finally {
      setIsProcessing(false);
    }
  };

  const projectId = typeof id === "string" ? id : "";
  const stage = detail?.project.stage ?? "RESEARCH";
  const readyForNext = detail ? detail.project.stage !== "RESEARCH" : false;
  const nextStageNotice = (() => {
    if (stage === "FACT_MAPPING") {
      return {
        title: "Research Complete",
        message:
          "All prompts have associated uploads. You can run the fact mapping agents to distribute findings across subchapters.",
        href: projectId ? `/projects/${projectId}/facts` : "/",
        cta: "Open Fact Mapping",
      };
    }
    if (stage === "EMOTIONAL") {
      return {
        title: "Fact Mapping Complete",
        message:
          "Mapped facts are ready. Continue to the emotional layer to weave narratives and analogies before drafting guidelines.",
        href: projectId ? `/projects/${projectId}/emotional` : "/",
        cta: "Open Emotional Layer",
      };
    }
    if (stage === "GUIDELINES" || stage === "WRITING") {
      return {
        title: "Emotional Layer Locked",
        message:
          "Persona and story hooks are set. Move into the guideline studio to brief the writing agents.",
        href: projectId ? `/projects/${projectId}/guidelines` : "/",
        cta: "Open Guidelines",
      };
    }
    return null;
  })();

  return (
    <AppLayout title="Research Dashboard">
      <div className={styles.wrapper}>
        <section className={styles.sidebar}>
          <h1>Research Dashboard</h1>
          {isLoading ? (
            <p className={styles.status} role="status" aria-live="polite">
              Loading research prompts…
            </p>
          ) : error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : (
            <>
              <p>
                Project title: <strong>{detail?.project.title ?? "Untitled Project"}</strong>
              </p>
              <form className={styles.guidelinesForm} onSubmit={handleRegenerate}>
                <label>
                  Research Guidelines (optional)
                  <textarea
                    value={guidelinesDraft}
                    onChange={(event) => setGuidelinesDraft(event.target.value)}
                    placeholder="Outline desired angles, required citations, or scope constraints."
                  />
                </label>
                <button type="submit" disabled={isProcessing}>
                  {isProcessing ? "Updating…" : "Regenerate Prompts"}
                </button>
              </form>
            </>
          )}
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
          <div className={styles.links}>
            <Link href={`/projects/${id}/titles`}>Back to Titles</Link>
            <Link href="/">Dashboard</Link>
          </div>
        </section>

        <section className={styles.mainContent}>
          {isLoading && (
            <p className={styles.status} role="status" aria-live="polite">
              Preparing prompts…
            </p>
          )}
          {!isLoading && detail && (
            <>
              <div className={styles.promptGrid}>
                {prompts.map((prompt, index) => (
                  <PromptCard
                    key={prompt.prompt_text}
                    prompt={prompt}
                    index={index}
                    uploads={uploadsByPrompt[index] ?? []}
                    onUpload={(values) => handleUpload(index, values)}
                    disabled={isProcessing || readyForNext}
                    onError={(message) => {
                      showStatus(null);
                      setError(message);
                    }}
                    onNotify={showStatus}
                  />
                ))}
              </div>
              {detail.critique && (
                <div className={styles.critiqueBox}>
                  <h2>Critique Notes</h2>
                  <p>{detail.critique}</p>
                </div>
              )}
              {nextStageNotice && (
                <div className={styles.nextStageNotice}>
                  <h2>{nextStageNotice.title}</h2>
                  <p>{nextStageNotice.message}</p>
                  <Link href={nextStageNotice.href}>{nextStageNotice.cta}</Link>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </AppLayout>
  );
}

async function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read file contents."));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result === "string") {
        const [, base64Payload] = result.split(",");
        resolve(base64Payload ?? result);
        return;
      }
      reject(new Error("Unsupported file format."));
    };
    reader.readAsDataURL(file);
  });
}

function PromptCard({
  prompt,
  index,
  uploads,
  onUpload,
  disabled,
  onError,
  onNotify,
}: {
  prompt: ResearchPrompt;
  index: number;
  uploads: ResearchUpload[];
  onUpload: (payload: { filename: string; notes?: string; base64: string }) => Promise<void>;
  disabled: boolean;
  onError: (message: string) => void;
  onNotify: (message: string) => void;
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || isSubmitting) return;
    const formData = new FormData(event.currentTarget);
    const filename = String(formData.get("filename") || "").trim();
    const notes = String(formData.get("notes") || "").trim();
    const file = formData.get("file");
    if (!filename) {
      onError("Please provide a filename or short label for the uploaded research.");
      return;
    }
    if (!(file instanceof File) || file.size === 0) {
      onError("Attach the research document before recording the upload.");
      return;
    }
    try {
      setIsSubmitting(true);
      const base64 = await readFileAsBase64(file);
      await onUpload({ filename, notes: notes || undefined, base64 });
      event.currentTarget.reset();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to process upload.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyPrompt = async () => {
    const payload = [prompt.focus_summary, prompt.prompt_text]
      .filter(Boolean)
      .join("\n\n");
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(payload);
        setCopyState("copied");
        onNotify(`Prompt ${index + 1} copied to clipboard.`);
      } else {
        throw new Error("Clipboard access unavailable");
      }
    } catch (err) {
      setCopyState("error");
      onError(err instanceof Error ? err.message : "Failed to copy prompt.");
    }
  };

  useEffect(() => {
    if (copyState === "copied") {
      const timer = setTimeout(() => setCopyState("idle"), 2000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [copyState]);

  return (
    <article className={styles.card}>
      <header>
        <h2>Prompt {index + 1}</h2>
        <p>{prompt.focus_summary}</p>
        <button
          type="button"
          onClick={handleCopyPrompt}
          disabled={disabled}
          className={styles.copyButton}
        >
          {copyState === "copied" ? "Copied" : "Copy prompt"}
        </button>
      </header>
      <section className={styles.promptBody}>
        <h3>Prompt Text</h3>
        <p>{prompt.prompt_text}</p>
        {prompt.focus_subchapters.length > 0 && (
          <p className={styles.meta}>Focus: {prompt.focus_subchapters.join(", ")}</p>
        )}
        {prompt.desired_sources.length > 0 && (
          <p className={styles.meta}>Sources: {prompt.desired_sources.join(", ")}</p>
        )}
        {prompt.additional_notes && <p className={styles.meta}>Notes: {prompt.additional_notes}</p>}
      </section>
      <section className={styles.uploadSection}>
        <h3>Uploads</h3>
        {uploads.length === 0 ? (
          <p className={styles.meta}>No uploads recorded yet.</p>
        ) : (
          <ul>
            {uploads.map((upload) => (
              <li key={upload.id}>
                <strong>{upload.filename}</strong>
                <span>{new Date(upload.uploaded_at).toLocaleString()}</span>
                {upload.notes && <p>{upload.notes}</p>}
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={handleSubmit} className={styles.uploadForm}>
          <label>
            File name or reference
            <input
              name="filename"
              type="text"
              placeholder="e.g., logistics-report.docx"
              disabled={disabled || isSubmitting}
            />
          </label>
          <label>
            Notes (optional)
            <textarea
              name="notes"
              rows={2}
              placeholder="Summarise contents or findings."
              disabled={disabled || isSubmitting}
            />
          </label>
          <label>
            Research file
            <input name="file" type="file" accept=".doc,.docx,.txt,.md,.pdf" disabled={disabled || isSubmitting} />
          </label>
          <button type="submit" disabled={disabled || isSubmitting}>
            {isSubmitting ? "Recording…" : "Record Upload"}
          </button>
        </form>
      </section>
    </article>
  );
}
