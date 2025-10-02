import { useEffect, useState } from "react";
import { useTheme } from "../context/ThemeContext";
import styles from "./ThemeToggle.module.css";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  const isDark = theme === "dark";
  const label = `Switch to ${isDark ? "light" : "dark"} mode`;
  const statusLabel = ready ? (isDark ? "Dark mode" : "Light mode") : "Theme";

  return (
    <button
      type="button"
      className={`${styles.toggle} ${isDark ? styles.dark : styles.light}`}
      onClick={toggleTheme}
      aria-label={label}
      aria-pressed={isDark}
    >
      <span className={styles.icon} aria-hidden>
        {isDark ? <MoonIcon /> : <SunIcon />}
      </span>
      <span className={styles.label}>{statusLabel}</span>
      <span className={styles.indicator} aria-hidden />
    </button>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" role="presentation" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" />
      <g>
        <line x1="12" y1="2" x2="12" y2="5" />
        <line x1="12" y1="19" x2="12" y2="22" />
        <line x1="4.22" y1="4.22" x2="6.34" y2="6.34" />
        <line x1="17.66" y1="17.66" x2="19.78" y2="19.78" />
        <line x1="2" y1="12" x2="5" y2="12" />
        <line x1="19" y1="12" x2="22" y2="12" />
        <line x1="4.22" y1="19.78" x2="6.34" y2="17.66" />
        <line x1="17.66" y1="6.34" x2="19.78" y2="4.22" />
      </g>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" role="presentation">
      <path d="M21 12.79A9 9 0 0111.21 3 7 7 0 1019 14.79 9 9 0 0121 12.79z" />
    </svg>
  );
}
