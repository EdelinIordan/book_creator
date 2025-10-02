import Head from "next/head";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/router";
import { useAuth } from "../context/AuthContext";
import styles from "./login.module.css";
import { ThemeToggle } from "../components/ThemeToggle";

export default function LoginPage() {
  const router = useRouter();
  const { user, loading, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  if (!loading && user) {
    void router.replace("/");
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim().toLowerCase(), password);
      await router.replace("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to log in";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <Head>
        <title>Sign in • Book Creator</title>
      </Head>
      <div className={styles.themeToggle}>
        <ThemeToggle />
      </div>
      <section className={styles.card}>
        <h1>Welcome back</h1>
        <p>Sign in to continue orchestrating your book projects.</p>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              disabled={submitting}
            />
          </label>
          <label>
            Password
            <div className={styles.passwordInput}>
              <input
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                disabled={submitting}
              />
              <button
                type="button"
                className={styles.passwordToggle}
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          {error && <p className={styles.error}>{error}</p>}
          <button type="submit" disabled={submitting || email.trim() === "" || password.trim() === ""}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className={styles.helpText}>
          Need help? Check the <Link href="/">project dashboard</Link> documentation for credential setup.
        </p>
      </section>
    </div>
  );
}
