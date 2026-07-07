"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
/* eslint-disable @typescript-eslint/no-explicit-any */
import AgentPanel from "@/app/components/AgentPanel";
import MetricsChart from "@/app/components/MetricsChart";
import styles from "./page.module.css";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ||
  API_BASE.replace(/^http/, "ws");

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface LogEntry {
  time: string;
  stage: string;
  message: string;
  status: string;
}

interface JobResults {
  doc: string | null;
  review: any[] | null;
  analytics: Record<string, any> | null;
}

type OverallStatus = "connecting" | "running" | "completed" | "failed" | "loading";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const { id: jobId } = useParams<{ id: string }>();
  const router = useRouter();

  const [overallStatus, setOverallStatus] = useState<OverallStatus>("connecting");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [repoUrl, setRepoUrl] = useState("");
  const [results, setResults] = useState<JobResults>({
    doc: null,
    review: null,
    analytics: null,
  });
  const [qaInitialAnswer, setQaInitialAnswer] = useState<string>("");

  const logEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  /* -- helpers -------------------------------------------------------- */

  const addLog = useCallback((entry: LogEntry) => {
    setLogs((prev) => [...prev, entry]);
  }, []);

  const fetchResults = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/results/${jobId}`);
      if (!res.ok) return;
      const data = await res.json();
      setRepoUrl(data.repo_url || "");
      setResults({
        doc: data.results?.doc ?? null,
        review: data.results?.review ?? null,
        analytics: data.results?.analytics ?? null,
      });

      // fetch QA history
      try {
        const qaRes = await fetch(`${API_BASE}/api/results/${jobId}/qa`);
        if (qaRes.ok) {
          const qaData = await qaRes.json();
          if (qaData.length > 0) {
            setQaInitialAnswer(qaData[0].answer);
          }
        }
      } catch {
        /* ignore */
      }
    } catch {
      /* ignore */
    }
  }, [jobId]);

  /* -- WebSocket lifecycle ------------------------------------------- */

  useEffect(() => {
    if (!jobId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setOverallStatus("running");
      addLog({
        time: new Date().toLocaleTimeString(),
        stage: "ws",
        message: "WebSocket connected. Listening for progress…",
        status: "connected",
      });
    };

    ws.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        const time = payload.timestamp
          ? new Date(payload.timestamp).toLocaleTimeString()
          : new Date().toLocaleTimeString();

        addLog({
          time,
          stage: payload.stage || "info",
          message: payload.message || JSON.stringify(payload),
          status: payload.status || "in_progress",
        });

        if (payload.status === "completed") {
          setOverallStatus("completed");
          fetchResults();
          ws.close();
        } else if (payload.status === "failed") {
          setOverallStatus("failed");
          ws.close();
        }
      } catch {
        /* ignore malformed JSON */
      }
    };

    ws.onerror = () => {
      addLog({
        time: new Date().toLocaleTimeString(),
        stage: "error",
        message: "WebSocket error. Falling back to REST polling…",
        status: "error",
      });
      /* Fall back: try to load results via REST */
      setOverallStatus("loading");
      fetchResults().then(() => {
        setOverallStatus((prev) => (prev === "loading" ? "completed" : prev));
      });
    };

    ws.onclose = () => {
      /* If we never got a terminal status, fall back to REST */
      setOverallStatus((prev) => {
        if (prev === "running" || prev === "connecting") {
          fetchResults();
          return "completed";
        }
        return prev;
      });
    };

    return () => {
      ws.close();
    };
  }, [jobId, addLog, fetchResults]);

  /* auto-scroll logs */
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  /* -- agent panel status -------------------------------------------- */

  function agentStatus(
    data: unknown
  ): "pending" | "running" | "completed" | "error" {
    if (overallStatus === "failed") return "error";
    if (data != null) return "completed";
    if (overallStatus === "running") return "running";
    return "pending";
  }

  /* -- stage class ---------------------------------------------------- */

  function stageClass(status: string) {
    if (status === "completed") return styles.logStageCompleted;
    if (status === "failed") return styles.logStageFailed;
    return "";
  }

  /* ------------------------------------------------------------------ */
  /*  Render                                                             */
  /* ------------------------------------------------------------------ */

  return (
    <div className={styles.page}>
      {/* Top bar */}
      <div className={styles.topBar}>
        <button className={styles.backLink} onClick={() => router.push("/")}>
          ← Back
        </button>
        <h1 className={styles.pageTitle}>
          <span className="gradient-text">Analysis Dashboard</span>
        </h1>
        {repoUrl && <span className={styles.repoChip}>🔗 {repoUrl}</span>}
      </div>

      {/* Progress log */}
      <div className={styles.progressSection}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "var(--space-md)",
          }}
        >
          <span className={styles.progressTitle}>Pipeline Progress</span>
          <span
            className={`${styles.overallStatus} ${
              overallStatus === "completed"
                ? styles.statusCompleted
                : overallStatus === "failed"
                ? styles.statusFailed
                : overallStatus === "running"
                ? styles.statusRunning
                : styles.statusPending
            }`}
          >
            {overallStatus === "running" && (
              <span className={styles.spinnerSmall} />
            )}
            {overallStatus.toUpperCase()}
          </span>
        </div>

        <div className={styles.progressLog}>
          {logs.map((log, i) => (
            <div key={i} className={styles.logEntry}>
              <span className={styles.logTime}>{log.time}</span>
              <span
                className={`${styles.logStage} ${stageClass(log.status)}`}
              >
                {log.stage}
              </span>
              <span className={styles.logMessage}>{log.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>

      {/* Agent panels grid */}
      <div className={styles.agentGrid}>
        <AgentPanel
          variant="doc"
          status={agentStatus(results.doc)}
          data={results.doc}
          jobId={jobId}
        />
        <AgentPanel
          variant="review"
          status={agentStatus(results.review)}
          data={results.review as any}
        />
        <AgentPanel
          variant="qa"
          status={agentStatus(
            qaInitialAnswer || (overallStatus === "completed" ? "" : null)
          )}
          data={
            qaInitialAnswer ||
            (overallStatus === "completed"
              ? "Analysis complete. Ask me anything about this codebase!"
              : null)
          }
          jobId={jobId}
        />
        <AgentPanel
          variant="analytics"
          status={agentStatus(results.analytics)}
          data={results.analytics as any}
          chartsSlot={
            results.analytics ? (
              <MetricsChart analytics={results.analytics as any} />
            ) : undefined
          }
        />
      </div>
    </div>
  );
}
