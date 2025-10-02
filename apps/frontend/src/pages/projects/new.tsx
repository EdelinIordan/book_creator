import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useForm } from "react-hook-form";
import { AppLayout } from "../../layout/AppLayout";
import {
  Category,
  createProject,
  fetchCategories,
  IdeaIntakePayload,
  IdeaIntakeResult,
} from "../../lib/api";
import styles from "./new.module.css";

const MAX_WORDS = 100;
const MAX_GUIDELINES_WORDS = 500;

type IdeaFormValues = {
  category_id: string;
  working_title: string;
  description: string;
  research_guidelines: string;
};

export default function NewProjectPage() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<IdeaFormValues>({
    defaultValues: {
      category_id: "",
      working_title: "",
      description: "",
      research_guidelines: "",
    },
  });

  const [categories, setCategories] = useState<Category[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const description = watch("description");
  const guidelines = watch("research_guidelines");
  const wordCount = useMemo(() => {
    return description
      .trim()
      .split(/\s+/)
      .filter(Boolean).length;
  }, [description]);

  const guidelineWordCount = useMemo(() => {
    return guidelines
      .trim()
      .split(/\s+/)
      .filter(Boolean).length;
  }, [guidelines]);

  useEffect(() => {
    let active = true;
    fetchCategories()
      .then((data) => {
        if (active) {
          setCategories(data);
        }
      })
      .catch(() => {
        if (active) {
          setCategories([]);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const onSubmit = async (values: IdeaFormValues) => {
    setIsSubmitting(true);
    setSubmitStatus(null);
    setSubmitError(null);

    const payload: IdeaIntakePayload = {
      category_id: values.category_id ? Number(values.category_id) : null,
      working_title: values.working_title.trim() || undefined,
      description: values.description.trim(),
      research_guidelines: values.research_guidelines.trim() || undefined,
    };

    try {
      const result: IdeaIntakeResult = await createProject(payload);
      setSubmitStatus("Structure generated! Redirecting to Structure Lab…");
      await router.push(`/projects/${result.projectId}/structure`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppLayout title="Idea Intake">
      <div className={styles.wrapper}>
        <header className={styles.header}>
          <h1>Idea Intake</h1>
          <p>
            Share up to 100 words describing your idea. The orchestrator will generate a structured outline that you can
            refine before moving to title ideation and research stages.
          </p>
        </header>
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)}>
          <label className={styles.field}>
            Working Title <span className={styles.optional}>(optional)</span>
            <input type="text" placeholder="Untitled Project" {...register("working_title", { maxLength: 150 })} />
            {errors.working_title && <span className={styles.error}>Title must be under 150 characters.</span>}
          </label>

          <label className={styles.field}>
            Category
            <select {...register("category_id")}>
              <option value="">Select a category</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            Idea Description
            <textarea
              rows={6}
              placeholder="Describe the concept, goals, and audience in up to 100 words."
              {...register("description", { required: true })}
            />
            <div className={wordCount <= MAX_WORDS ? styles.wordCount : styles.wordCountExceeded}>
              {wordCount} / {MAX_WORDS} words
            </div>
            {errors.description && <span className={styles.error}>Idea description is required.</span>}
          </label>

          <label className={styles.field}>
            Research Guidelines <span className={styles.optional}>(optional, up to 500 words)</span>
            <textarea
              rows={6}
              placeholder="Describe the depth of research you expect, preferred sources, or analysis expectations."
              {...register("research_guidelines")}
            />
            <div className={
              guidelineWordCount <= MAX_GUIDELINES_WORDS
                ? styles.wordCount
                : styles.wordCountExceeded
            }>
              {guidelineWordCount} / {MAX_GUIDELINES_WORDS} words
            </div>
          </label>

          {submitError && (
            <p className={styles.errorBanner} role="alert">
              {submitError}
            </p>
          )}
          {submitStatus && (
            <p className={styles.statusBanner} role="status" aria-live="polite">
              {submitStatus}
            </p>
          )}

          <div className={styles.actions}>
            <Link href="/" className={styles.secondaryButton}>
              Cancel
            </Link>
            <button
              type="submit"
              disabled={
                isSubmitting ||
                wordCount === 0 ||
                wordCount > MAX_WORDS ||
                guidelineWordCount > MAX_GUIDELINES_WORDS
              }
            >
              {isSubmitting ? "Generating structure…" : "Generate Structure"}
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  );
}
