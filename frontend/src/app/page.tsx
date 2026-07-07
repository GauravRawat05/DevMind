"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Validate that the value looks like a GitHub repo URL. */
function isValidGitHubUrl(url: string): boolean {
  return /^https?:\/\/(www\.)?github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/.test(
    url.trim()
  );
}

export default function HomePage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    const trimmed = repoUrl.trim();
    if (!trimmed) {
      setError("Please enter a GitHub repository URL.");
      return;
    }
    if (!isValidGitHubUrl(trimmed)) {
      setError("Invalid URL. Use format: https://github.com/owner/repo");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: trimmed }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      router.push(`/dashboard/${data.job_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      setError(msg);
      setLoading(false);
    }
  }

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.hero}>
        <h1 className={styles.logo}>DevMind</h1>
        <p className={styles.tagline}>
          AI-powered multi-agent code intelligence. Connect any GitHub repo and
          get instant documentation, review, Q&amp;A, and analytics.
        </p>

        <div className={styles.card}>
          {/* Feature chips */}
          <div className={styles.features}>
            {[
              "📝 Auto Documentation",
              "🔍 Code Review",
              "💬 RAG Q&A",
              "📊 Complexity Analytics",
            ].map((label) => (
              <span key={label} className={styles.chip}>
                {label}
              </span>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            <div className={styles.formGroup}>
              <input
                id="repo-url-input"
                type="url"
                placeholder="https://github.com/owner/repo"
                value={repoUrl}
                onChange={(e) => {
                  setRepoUrl(e.target.value);
                  if (error) setError("");
                }}
                className={`${styles.input} ${error ? styles.inputError : ""}`}
                disabled={loading}
                autoComplete="url"
                spellCheck={false}
              />
              <button
                id="analyze-submit-btn"
                type="submit"
                className={styles.submitBtn}
                disabled={loading}
              >
                {loading ? <span className={styles.loader} /> : "Analyze"}
              </button>
            </div>

            {error && (
              <p className={styles.errorMsg} role="alert">
                ⚠️ {error}
              </p>
            )}
          </form>

          <p className={styles.hint}>
            Paste any public GitHub repository URL and hit Analyze.
            <br />
            4 AI agents run in parallel to deliver results in real time.
          </p>
        </div>
      </div>
    </div>
  );
}
