"use client";

import { useState, type FormEvent } from "react";
import { marked } from "marked";
import styles from "./AgentPanel.module.css";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ReviewIssue {
  file: string;
  line: number | null;
  severity: "critical" | "warning" | "info";
  message: string;
  suggestion: string;
}

interface AnalyticsData {
  file_metrics?: Record<string, unknown>[];
  summary?: {
    total_files?: number;
    total_python_files?: number;
    total_loc?: number;
    avg_complexity?: number;
    complexity_distribution?: Record<string, number>;
  };
  top_complex_files?: Record<string, unknown>[];
  tech_debt_score?: number;
}

interface QAPair {
  question: string;
  answer: string;
}

/* ------------------------------------------------------------------ */
/*  Shared props                                                       */
/* ------------------------------------------------------------------ */

interface AgentPanelProps {
  variant: "doc" | "review" | "qa" | "analytics";
  status: "pending" | "running" | "completed" | "error";
  data: string | ReviewIssue[] | AnalyticsData | null;
  /** Only for Q&A panel — the job ID for interactive queries */
  jobId?: string;
  /** Analytics charts component injected from outside */
  chartsSlot?: React.ReactNode;
}

const PANEL_META: Record<
  AgentPanelProps["variant"],
  { icon: string; label: string; iconClass: string }
> = {
  doc:       { icon: "📝", label: "Doc Agent",       iconClass: styles.iconDoc },
  review:    { icon: "🔍", label: "Review Agent",    iconClass: styles.iconReview },
  qa:        { icon: "💬", label: "Q&A Agent",       iconClass: styles.iconQA },
  analytics: { icon: "📊", label: "Analytics Agent", iconClass: styles.iconAnalytics },
};

const STATUS_CLASS: Record<string, string> = {
  pending:   styles.statusPending,
  running:   styles.statusRunning,
  completed: styles.statusCompleted,
  error:     styles.statusError,
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AgentPanel({
  variant,
  status,
  data,
  jobId,
  chartsSlot,
}: AgentPanelProps) {
  const meta = PANEL_META[variant];

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <span className={`${styles.icon} ${meta.iconClass}`}>{meta.icon}</span>
        <span className={styles.title}>{meta.label}</span>
        {variant === "doc" && status === "completed" && jobId && (
          <a
            href={`${API_BASE}/api/download/${jobId}/doc`}
            download
            className={styles.downloadBtn}
            title="Download README.md"
          >
            📥 Download
          </a>
        )}
        <span className={`${styles.status} ${STATUS_CLASS[status] ?? ""}`}>
          {status}
        </span>
      </div>

      {/* Body */}
      <div className={styles.body}>
        {status === "pending" && <EmptyState text="Waiting for data…" />}
        {status === "running" && <EmptyState text="Agent is working…" icon="⏳" />}
        {status === "error" && <EmptyState text="Agent encountered an error." icon="❌" />}

        {status === "completed" && variant === "doc" && (
          <DocBody markdown={data as string} />
        )}
        {status === "completed" && variant === "review" && (
          <ReviewBody issues={data as ReviewIssue[]} />
        )}
        {status === "completed" && variant === "qa" && (
          <QABody
            initialAnswer={data as string}
            jobId={jobId ?? ""}
          />
        )}
        {status === "completed" && variant === "analytics" && (
          <AnalyticsBody
            analytics={data as AnalyticsData}
            chartsSlot={chartsSlot}
          />
        )}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Sub-components                                                     */
/* ================================================================== */

function EmptyState({ text, icon = "🔄" }: { text: string; icon?: string }) {
  return (
    <div className={styles.empty}>
      <span className={styles.emptyIcon}>{icon}</span>
      <span>{text}</span>
    </div>
  );
}

/* ---- Doc Agent --------------------------------------------------- */

function DocBody({ markdown }: { markdown: string }) {
  const html = marked.parse(markdown || "", { async: false }) as string;
  return (
    <div
      className="markdown-body"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/* ---- Review Agent ------------------------------------------------ */

function ReviewBody({ issues }: { issues: ReviewIssue[] }) {
  if (!issues || issues.length === 0) {
    return <EmptyState text="No issues found — great code!" icon="✅" />;
  }

  const severityClass: Record<string, string> = {
    critical: styles.issueCritical,
    warning:  styles.issueWarning,
    info:     styles.issueInfo,
  };

  return (
    <ul className={styles.issuesList}>
      {issues.map((issue, idx) => (
        <li
          key={idx}
          className={`${styles.issueItem} ${severityClass[issue.severity] ?? ""}`}
        >
          <div className={styles.issueMeta}>
            <span
              className={`badge ${
                issue.severity === "critical"
                  ? "badge-critical"
                  : issue.severity === "warning"
                  ? "badge-warning"
                  : "badge-info"
              }`}
            >
              {issue.severity}
            </span>
            <span className={styles.issueFile}>
              {issue.file}
              {issue.line != null ? `:${issue.line}` : ""}
            </span>
          </div>
          <p className={styles.issueMessage}>{issue.message}</p>
          {issue.suggestion && (
            <p className={styles.issueSuggestion}>💡 {issue.suggestion}</p>
          )}
        </li>
      ))}
    </ul>
  );
}

/* ---- Q&A Agent --------------------------------------------------- */

function QABody({
  initialAnswer,
  jobId,
}: {
  initialAnswer: string;
  jobId: string;
}) {
  const [pairs, setPairs] = useState<QAPair[]>([
    {
      question: "What is the main purpose of this project?",
      answer: initialAnswer || "No answer available.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || !jobId) return;

    setLoading(true);
    setInput("");

    try {
      const res = await fetch(`${API_BASE}/api/results/${jobId}/qa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();
      setPairs((prev) => [
        ...prev,
        { question: q, answer: data.answer ?? "No answer." },
      ]);
    } catch {
      setPairs((prev) => [
        ...prev,
        { question: q, answer: "Failed to get answer. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className={styles.qaThread}>
        {pairs.map((p, i) => (
          <div key={i} className={styles.qaPair}>
            <p className={styles.qaQuestion}>Q: {p.question}</p>
            <div
              className={`${styles.qaAnswer} markdown-body`}
              dangerouslySetInnerHTML={{
                __html: marked.parse(p.answer, { async: false }) as string,
              }}
            />
          </div>
        ))}
      </div>

      <form className={styles.qaForm} onSubmit={handleAsk}>
        <input
          id="qa-input"
          className={styles.qaInput}
          type="text"
          placeholder="Ask about the codebase…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          id="qa-submit-btn"
          type="submit"
          className={styles.qaSubmitBtn}
          disabled={loading || !input.trim()}
        >
          {loading ? "…" : "Ask"}
        </button>
      </form>
    </>
  );
}

/* ---- Analytics Agent --------------------------------------------- */

function AnalyticsBody({
  analytics,
  chartsSlot,
}: {
  analytics: AnalyticsData;
  chartsSlot?: React.ReactNode;
}) {
  const summary = analytics?.summary;
  if (!summary) {
    return <EmptyState text="No analytics data available." icon="📊" />;
  }

  return (
    <>
      {/* Summary cards */}
      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <div className={styles.summaryValue}>{summary.total_files ?? 0}</div>
          <div className={styles.summaryLabel}>Total Files</div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryValue}>
            {summary.total_python_files ?? 0}
          </div>
          <div className={styles.summaryLabel}>Python Files</div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryValue}>{summary.total_loc ?? 0}</div>
          <div className={styles.summaryLabel}>Lines of Code</div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryValue}>
            {summary.avg_complexity ?? 0}
          </div>
          <div className={styles.summaryLabel}>Avg Complexity</div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryValue}>
            {analytics.tech_debt_score ?? 0}
          </div>
          <div className={styles.summaryLabel}>Debt Score</div>
        </div>
      </div>

      {/* Charts injected via slot */}
      {chartsSlot}
    </>
  );
}
