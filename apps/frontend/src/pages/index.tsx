import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { AppLayout } from "../layout/AppLayout";
import { deleteProject, fetchProjects, ProjectSummary, updateProjectBudget } from "../lib/api";
import styles from "./index.module.css";

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingBudget, setEditingBudget] = useState<Record<string, boolean>>({});
  const [budgetDrafts, setBudgetDrafts] = useState<Record<string, string>>({});
  const [budgetErrors, setBudgetErrors] = useState<Record<string, string | null>>({});
  const [budgetSaving, setBudgetSaving] = useState<Record<string, boolean>>({});
  const [pendingDelete, setPendingDelete] = useState<ProjectSummary | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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
          setError(err instanceof Error ? err.message : "Failed to load projects");
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
  }, []);

  const createProjectHref = "/projects/new";

  const destinationForStage = (project: ProjectSummary) => {
    switch (project.stage) {
      case "IDEA":
      case "STRUCTURE":
        return `/projects/${project.id}/structure`;
      case "TITLE":
        return `/projects/${project.id}/titles`;
      case "RESEARCH":
        return `/projects/${project.id}/research`;
      case "FACT_MAPPING":
        return `/projects/${project.id}/facts`;
      case "EMOTIONAL":
        return `/projects/${project.id}/emotional`;
      case "GUIDELINES":
        return `/projects/${project.id}/guidelines`;
      case "WRITING":
        return `/projects/${project.id}/writing`;
      default:
        return `/projects/${project.id}/structure`;
    }
  };

  const startEditingBudget = (project: ProjectSummary) => {
    setEditingBudget((prev) => ({ ...prev, [project.id]: true }));
    setBudgetDrafts((prev) => ({
      ...prev,
      [project.id]: project.spend_limit_usd !== null ? project.spend_limit_usd.toFixed(2) : "",
    }));
    setBudgetErrors((prev) => ({ ...prev, [project.id]: null }));
  };

  const cancelEditingBudget = (projectId: string) => {
    setEditingBudget((prev) => ({ ...prev, [projectId]: false }));
    setBudgetErrors((prev) => ({ ...prev, [projectId]: null }));
    setBudgetSaving((prev) => ({ ...prev, [projectId]: false }));
  };

  const handleBudgetSubmit = async (projectId: string, event?: FormEvent) => {
    if (event) {
      event.preventDefault();
    }

    const draft = (budgetDrafts[projectId] ?? "").trim();
    let nextLimit: number | null;

    if (draft.length === 0) {
      nextLimit = null;
    } else {
      const parsed = Number(draft);
      if (Number.isNaN(parsed) || parsed < 0) {
        setBudgetErrors((prev) => ({
          ...prev,
          [projectId]: "Enter a non-negative amount",
        }));
        return;
      }
      nextLimit = Math.round(parsed * 100) / 100;
    }

    setBudgetErrors((prev) => ({ ...prev, [projectId]: null }));
    setBudgetSaving((prev) => ({ ...prev, [projectId]: true }));

    try {
      const updated = await updateProjectBudget(projectId, nextLimit);
      setProjects((prev) =>
        prev.map((project) => (project.id === projectId ? updated : project))
      );
      setBudgetDrafts((prev) => ({
        ...prev,
        [projectId]: updated.spend_limit_usd !== null ? updated.spend_limit_usd.toFixed(2) : "",
      }));
      setEditingBudget((prev) => ({ ...prev, [projectId]: false }));
    } catch (err) {
      setBudgetErrors((prev) => ({
        ...prev,
        [projectId]: err instanceof Error ? err.message : "Failed to update budget",
      }));
    } finally {
      setBudgetSaving((prev) => ({ ...prev, [projectId]: false }));
    }
  };

  const openDeleteModal = (project: ProjectSummary) => {
    setPendingDelete(project);
    setDeleteError(null);
  };

  const closeDeleteModal = () => {
    if (deleteLoading) {
      return;
    }
    setPendingDelete(null);
    setDeleteError(null);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) {
      return;
    }
    setDeleteLoading(true);
    setDeleteError(null);
    try {
      await deleteProject(pendingDelete.id);
      setProjects((prev) => prev.filter((project) => project.id !== pendingDelete.id));
      setPendingDelete(null);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete project");
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <AppLayout title="Library Dashboard">
      <section className={styles.hero}>
        <h1>Library Dashboard</h1>
        <p>
          Track every manuscript from idea intake through writing, keep provider settings aligned with your agents,
          and understand where Story Weave and guideline prep still need attention.
        </p>
        <div className={styles.actions}>
          <Link href="/provider-settings">Configure Providers</Link>
          <Link href={createProjectHref} className={styles.primaryButton} aria-label="Start a new nonfiction project">
            New Project
          </Link>
        </div>
      </section>
      <section className={styles.projectGrid}>
        {isLoading && (
          <p className={styles.status} role="status" aria-live="polite">
            Loading projects…
          </p>
        )}
        {error && !isLoading && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        {!isLoading && !error && projects.length === 0 && (
          <p className={styles.status} role="status" aria-live="polite">
            Create a new project to start the idea intake workflow.
          </p>
        )}
        {!isLoading && !error &&
          projects.map((project) => {
            const categoryName = project.category?.name ?? "Uncategorised";
            const stageRoute = destinationForStage(project);
            const isEditing = editingBudget[project.id] ?? false;
            const saving = budgetSaving[project.id] ?? false;
            const draftValue = budgetDrafts[project.id] ?? "";
            const budgetStatusLabel =
              project.spend_limit_usd === null
                ? "Unlimited budget"
                : project.budget_status === "warning"
                ? "Budget nearly used"
                : project.budget_status === "exceeded"
                ? "Budget reached"
                : "Within budget";

            return (
              <article key={project.id} className={styles.card}>
                <header>
                  <h2>{project.title ?? "Untitled Project"}</h2>
                  <div className={styles.headerActions}>
                    <button
                      type="button"
                      className={styles.deleteButton}
                      onClick={() => openDeleteModal(project)}
                    >
                      Delete
                    </button>
                    <div className={styles.badgeRow}>
                      <span className={styles.category}>{categoryName}</span>
                      {project.guidelines_ready && (
                        <span className={styles.badge}>Guidelines Ready</span>
                      )}
                      {project.writing_ready && (
                        <span className={styles.badge}>Writing Ready</span>
                      )}
                    </div>
                  </div>
                </header>
                <p>
                  Current Stage: <strong>{project.stage_label}</strong>
                </p>
                <div className={styles.progressBar}>
                  <div style={{ width: `${project.progress}%` }} />
                </div>

                <div className={styles.budgetSection}>
                  <div>
                    <span className={styles.budgetLabel}>Spend</span>
                    <strong>${project.total_cost_usd.toFixed(2)}</strong>
                    {project.spend_limit_usd !== null && (
                      <span className={styles.budgetLimit}>
                        {` / $${project.spend_limit_usd.toFixed(2)} limit`}
                        {project.budget_remaining_usd !== null && (
                          <em>{` (${project.budget_remaining_usd.toFixed(2)} remaining)`}</em>
                        )}
                      </span>
                    )}
                  </div>
                  <span
                    className={`${styles.budgetStatus} ${styles[project.spend_limit_usd === null ? "unlimited" : project.budget_status]}`}
                  >
                    {budgetStatusLabel}
                  </span>
                </div>

                {isEditing ? (
                  <form
                    className={styles.budgetForm}
                    onSubmit={(event) => handleBudgetSubmit(project.id, event)}
                  >
                    <label>
                      Spend limit (USD)
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={draftValue}
                        onChange={(event) =>
                          setBudgetDrafts((prev) => ({ ...prev, [project.id]: event.target.value }))
                        }
                        placeholder="Leave blank for unlimited"
                        disabled={saving}
                      />
                    </label>
                    {budgetErrors[project.id] && (
                      <span className={styles.budgetError} role="alert">
                        {budgetErrors[project.id]}
                      </span>
                    )}
                    <div className={styles.budgetControls}>
                      <button
                        type="button"
                        onClick={() => cancelEditingBudget(project.id)}
                        disabled={saving}
                      >
                        Cancel
                      </button>
                      <button type="submit" disabled={saving}>
                        {saving ? "Saving…" : "Save"}
                      </button>
                    </div>
                    <button
                      type="button"
                      className={styles.clearBudget}
                      onClick={() => setBudgetDrafts((prev) => ({ ...prev, [project.id]: "" }))}
                      disabled={saving}
                    >
                      Clear value
                    </button>
                  </form>
                ) : (
                  <div className={styles.budgetActionsRow}>
                    <button onClick={() => startEditingBudget(project)}>
                      {project.spend_limit_usd === null ? "Set budget" : "Adjust budget"}
                    </button>
                  </div>
                )}

                <footer>
                  <Link
                    href={stageRoute}
                    aria-label={`Continue ${project.title ?? "Untitled Project"} in ${project.stage_label}`}
                  >
                    Continue
                  </Link>
                </footer>
              </article>
            );
          })}
      </section>
      {pendingDelete && (
        <div
          className={styles.modalBackdrop}
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeDeleteModal();
            }
          }}
        >
          <div className={styles.modal}>
            <h2 id="delete-modal-title">Are you sure?</h2>
            <p>
              Delete <strong>{pendingDelete.title ?? "Untitled Project"}</strong> and all of its in-progress
              work.
            </p>
            {deleteError && (
              <p className={styles.modalError} role="alert">
                {deleteError}
              </p>
            )}
            <div className={styles.modalActions}>
              <button type="button" className={styles.secondaryButton} onClick={closeDeleteModal} disabled={deleteLoading}>
                Cancel
              </button>
              <button type="button" className={styles.dangerButton} onClick={confirmDelete} disabled={deleteLoading}>
                {deleteLoading ? "Deleting…" : "Delete project"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
