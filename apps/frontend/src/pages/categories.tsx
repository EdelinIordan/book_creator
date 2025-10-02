import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppLayout } from "../layout/AppLayout";
import {
  Category,
  CategoryCreatePayload,
  createCategory,
  fetchCategories,
  fetchProjects,
  ProjectSummary,
} from "../lib/api";
import styles from "./categories.module.css";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [categoryLoading, setCategoryLoading] = useState(true);
  const [projectLoading, setProjectLoading] = useState(true);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const [projectError, setProjectError] = useState<string | null>(null);

  const [nameDraft, setNameDraft] = useState("");
  const [colorDraft, setColorDraft] = useState("#2563EB");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    fetchCategories()
      .then((data) => {
        if (!active) {
          return;
        }
        const sorted = [...data].sort((a, b) => a.name.localeCompare(b.name));
        setCategories(sorted);
        if (sorted.length > 0) {
          setSelectedCategoryId((prev) => (prev === null ? sorted[0].id : prev));
        }
      })
      .catch((err) => {
        if (active) {
          setCategoryError(err instanceof Error ? err.message : "Failed to load categories");
        }
      })
      .finally(() => {
        if (active) {
          setCategoryLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    fetchProjects()
      .then((data) => {
        if (active) {
          setProjects(data);
        }
      })
      .catch((err) => {
        if (active) {
          setProjectError(err instanceof Error ? err.message : "Failed to load projects");
        }
      })
      .finally(() => {
        if (active) {
          setProjectLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const completedCounts = useMemo(() => {
    const counts: Record<number, number> = {};
    projects.forEach((project) => {
      const categoryId = project.category?.id;
      if (project.stage === "COMPLETE" && typeof categoryId === "number") {
        counts[categoryId] = (counts[categoryId] ?? 0) + 1;
      }
    });
    return counts;
  }, [projects]);

  const completedProjects = useMemo(() => {
    if (selectedCategoryId === null) {
      return [];
    }
    return projects.filter(
      (project) => project.stage === "COMPLETE" && project.category?.id === selectedCategoryId
    );
  }, [projects, selectedCategoryId]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = nameDraft.trim();
    if (!trimmed) {
      setFormError("Enter a category name");
      return;
    }

    const payload: CategoryCreatePayload = {
      name: trimmed,
      color_hex: colorDraft,
    };

    setFormError(null);
    setSubmitting(true);
    try {
      const created = await createCategory(payload);
      setCategories((prev) => {
        const next = [...prev, created];
        next.sort((a, b) => a.name.localeCompare(b.name));
        return next;
      });
      setNameDraft("");
      setSelectedCategoryId(created.id);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create category");
    } finally {
      setSubmitting(false);
    }
  };

  const statusMessage = categoryError ?? projectError;

  return (
    <AppLayout title="Categories">
      <section className={styles.header}>
        <div>
          <h1>Categories</h1>
          <p>Organise your finished books by theme and add new tracks for upcoming projects.</p>
        </div>
        <form className={styles.form} onSubmit={handleSubmit} aria-label="Create category">
          <div className={styles.formField}>
            <label htmlFor="category-name">Category name</label>
            <input
              id="category-name"
              name="name"
              type="text"
              value={nameDraft}
              onChange={(event) => setNameDraft(event.target.value)}
              placeholder="e.g. Memoir"
              disabled={submitting}
              required
              autoComplete="off"
            />
          </div>
          <div className={styles.formField}>
            <label htmlFor="category-color">Badge colour</label>
            <input
              id="category-color"
              name="color"
              type="color"
              value={colorDraft}
              onChange={(event) => setColorDraft(event.target.value)}
              aria-label="Category colour"
              disabled={submitting}
            />
          </div>
          <button type="submit" className={styles.submitButton} disabled={submitting}>
            {submitting ? "Saving…" : "Add category"}
          </button>
          {formError && (
            <span role="alert" className={styles.formError}>
              {formError}
            </span>
          )}
        </form>
      </section>

      <section className={styles.content}>
        <aside className={styles.categoryPanel}>
          <h2>Available Categories</h2>
          {categoryLoading ? (
            <p className={styles.status}>Loading categories…</p>
          ) : categories.length === 0 ? (
            <p className={styles.status}>No categories yet. Create your first one to get started.</p>
          ) : (
            <ul className={styles.categoryList}>
              {categories.map((category) => {
                const isActive = category.id === selectedCategoryId;
                const completedTotal = completedCounts[category.id] ?? 0;
                return (
                  <li key={category.id}>
                    <button
                      type="button"
                      className={`${styles.categoryButton} ${isActive ? styles.categoryButtonActive : ""}`.trim()}
                      onClick={() => setSelectedCategoryId(category.id)}
                      aria-pressed={isActive}
                    >
                      <span
                        className={styles.categoryColor}
                        style={{ backgroundColor: category.color_hex }}
                        aria-hidden="true"
                      />
                      <span className={styles.categoryLabel}>{category.name}</span>
                      <span className={styles.categoryCount}>
                        {completedTotal === 1 ? "1 completed" : `${completedTotal} completed`}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>
        <div className={styles.detailsPanel}>
          <header className={styles.detailsHeader}>
            <h2>Completed Books</h2>
            {selectedCategoryId !== null && (
              <span className={styles.detailsBadge}>{completedProjects.length}</span>
            )}
          </header>
          {statusMessage && (
            <p className={styles.error} role="alert">
              {statusMessage}
            </p>
          )}
          {projectLoading ? (
            <p className={styles.status}>Loading projects…</p>
          ) : selectedCategoryId === null ? (
            <p className={styles.status}>Select a category to see finished books.</p>
          ) : completedProjects.length === 0 ? (
            <p className={styles.status}>
              No completed books in this category yet. Keep the workflow moving to change that.
            </p>
          ) : (
            <ul className={styles.projectList}>
              {completedProjects.map((project) => (
                <li key={project.id} className={styles.projectCard}>
                  <div>
                    <h3>{project.title ?? "Untitled Project"}</h3>
                    <p className={styles.projectSummary}>{project.idea_summary ?? "No summary available."}</p>
                  </div>
                  <span className={styles.projectMeta}>Last updated {new Date(project.last_updated).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </AppLayout>
  );
}
