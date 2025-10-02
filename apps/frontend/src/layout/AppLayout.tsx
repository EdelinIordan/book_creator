import Head from "next/head";
import Link from "next/link";
import { PropsWithChildren, useEffect } from "react";
import { useRouter } from "next/router";
import { useAuth } from "../context/AuthContext";
import { BookStage } from "../types/stage";
import styles from "./AppLayout.module.css";
import { ThemeToggle } from "../components/ThemeToggle";

const STAGE_ORDER: BookStage[] = [
  "IDEA",
  "STRUCTURE",
  "TITLE",
  "RESEARCH",
  "FACT_MAPPING",
  "EMOTIONAL",
  "GUIDELINES",
  "WRITING",
  "COMPLETE",
];

const STAGE_LABELS: Record<BookStage, string> = {
  IDEA: "Idea Intake",
  STRUCTURE: "Structure Lab",
  TITLE: "Title Hub",
  RESEARCH: "Research Dashboard",
  FACT_MAPPING: "Research Fact Map",
  EMOTIONAL: "Story Weave Lab",
  GUIDELINES: "Guideline Studio",
  WRITING: "Writing Studio",
  COMPLETE: "Ready to Publish",
};

export function AppLayout({ title, children }: PropsWithChildren<{ title?: string }>) {
  const { user, loading, error, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      void router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || (!user && typeof window !== "undefined")) {
    return (
      <div className={styles.loadingShell}>
        <p>Checking session…</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className={styles.wrapper}>
      <Head>
        <title>{title ? `${title} • Book Creator` : "Book Creator"}</title>
      </Head>
      <a href="#main-content" className={styles.skipLink}>
        Skip to main content
      </a>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <Link href="/" className={styles.logo}>
            Book Creator
          </Link>
          <div className={styles.themeToggleDesktop}>
            <ThemeToggle />
          </div>
        </div>
        <nav aria-label="Primary">
          <ul>
            {[
              { href: "/", label: "Dashboard" },
              { href: "/categories", label: "Categories" },
              { href: "/agents-and-api", label: "Agents & API" },
            ].map((link) => {
              const isActive = router.pathname === link.href;
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className={`${styles.navLink} ${isActive ? styles.navLinkActive : ""}`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className={styles.pipeline}>
          <h3>Workflow</h3>
          <ol aria-label="Book creation stages">
            {STAGE_ORDER.map((stage) => (
              <li key={stage}>{STAGE_LABELS[stage]}</li>
            ))}
          </ol>
        </div>
        <div className={styles.account}>
          <div>
            <span className={styles.accountLabel}>Signed in as</span>
            <strong>{user.email}</strong>
          </div>
          <button type="button" onClick={() => logout().then(() => router.replace("/login"))}>
            Log out
          </button>
          {error && <p className={styles.accountError}>{error}</p>}
        </div>
      </aside>
      <main className={styles.content} id="main-content">
        <div className={styles.themeToggleMobile}>
          <ThemeToggle />
        </div>
        <div className={styles.contentInner}>{children}</div>
      </main>
    </div>
  );
}
