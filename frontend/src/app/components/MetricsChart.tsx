"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import styles from "./MetricsChart.module.css";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface FileMetric {
  file_path: string;
  loc: number;
  functions: number;
  classes: number;
  cyclomatic_complexity: number;
  is_python: boolean;
  tier?: string;
}

interface AnalyticsData {
  file_metrics?: FileMetric[];
  summary?: {
    total_files?: number;
    total_python_files?: number;
    total_loc?: number;
    avg_complexity?: number;
    complexity_distribution?: Record<string, number>;
  };
  top_complex_files?: FileMetric[];
  tech_debt_score?: number;
}

interface MetricsChartProps {
  analytics: AnalyticsData;
}

/* ------------------------------------------------------------------ */
/*  Color config                                                       */
/* ------------------------------------------------------------------ */

const TIER_COLORS: Record<string, string> = {
  simple:  "hsl(155, 75%, 50%)",
  medium:  "hsl(28, 95%, 58%)",
  complex: "hsl(0, 80%, 60%)",
};

const PIE_COLORS = [
  "hsl(155, 75%, 50%)",
  "hsl(28, 95%, 58%)",
  "hsl(0, 80%, 60%)",
];

/* ------------------------------------------------------------------ */
/*  Custom Tooltip                                                     */
/* ------------------------------------------------------------------ */

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: Record<string, unknown> }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipLabel}>
        {String(d.name || d.file_path || "")}
      </p>
      {d.loc !== undefined && (
        <p className={styles.tooltipValue}>LOC: {String(d.loc)}</p>
      )}
      {d.cyclomatic_complexity !== undefined && (
        <p className={styles.tooltipValue}>
          Complexity: {String(d.cyclomatic_complexity)}
        </p>
      )}
      {d.tier !== undefined && (
        <p className={styles.tooltipValue}>Tier: {String(d.tier)}</p>
      )}
      {d.value !== undefined && (
        <p className={styles.tooltipValue}>Count: {String(d.value)}</p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function MetricsChart({ analytics }: MetricsChartProps) {
  const metrics = analytics.file_metrics ?? [];
  const dist = analytics.summary?.complexity_distribution ?? {};

  if (metrics.length === 0) return null;

  /* Scatter data — Complexity vs LOC */
  const scatterData = metrics.map((m) => ({
    ...m,
    name: m.file_path.split("/").pop() || m.file_path,
  }));

  /* Bar data — LOC per file (top 15) */
  const barData = [...metrics]
    .sort((a, b) => b.loc - a.loc)
    .slice(0, 15)
    .map((m) => ({
      name: m.file_path.split("/").pop() || m.file_path,
      loc: m.loc,
      tier: m.tier || "simple",
    }));

  /* Pie data — complexity tier distribution */
  const pieData = Object.entries(dist)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  return (
    <div className={styles.chartsWrapper}>
      {/* 1. Scatter Plot: Complexity vs LOC */}
      <div className={styles.chartSection}>
        <h4 className={styles.chartTitle}>
          Cyclomatic Complexity vs Lines of Code
        </h4>
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="loc"
              name="LOC"
              label={{ value: "Lines of Code", position: "bottom", offset: -2, fill: "hsl(230,15%,62%)", fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey="cyclomatic_complexity"
              name="Complexity"
              label={{ value: "Complexity", angle: -90, position: "insideLeft", fill: "hsl(230,15%,62%)", fontSize: 11 }}
            />
            <RechartsTooltip content={<CustomTooltip />} />
            <Scatter data={scatterData}>
              {scatterData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={TIER_COLORS[entry.tier || "simple"] || TIER_COLORS.simple}
                  fillOpacity={0.8}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* 2. Bar Chart: LOC per file */}
      <div className={styles.chartSection}>
        <h4 className={styles.chartTitle}>Lines of Code per File (Top 15)</h4>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            data={barData}
            margin={{ top: 10, right: 20, bottom: 40, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: "hsl(230,15%,62%)" }}
              angle={-35}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fontSize: 11, fill: "hsl(230,15%,62%)" }} />
            <RechartsTooltip content={<CustomTooltip />} />
            <Bar dataKey="loc" radius={[4, 4, 0, 0]}>
              {barData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={TIER_COLORS[entry.tier] || TIER_COLORS.simple}
                  fillOpacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 3. Pie Chart: Complexity tier distribution */}
      {pieData.length > 0 && (
        <div className={styles.chartSection}>
          <h4 className={styles.chartTitle}>Complexity Tier Distribution</h4>
          <div className={styles.pieRow}>
            <div className={styles.pieChart}>
              <ResponsiveContainer width={200} height={200}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={
                          TIER_COLORS[entry.name] ||
                          PIE_COLORS[i % PIE_COLORS.length]
                        }
                      />
                    ))}
                  </Pie>
                  <RechartsTooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className={styles.pieLegend}>
              {pieData.map((entry, i) => (
                <div key={entry.name} className={styles.legendItem}>
                  <span
                    className={styles.legendDot}
                    style={{
                      background:
                        TIER_COLORS[entry.name] ||
                        PIE_COLORS[i % PIE_COLORS.length],
                    }}
                  />
                  <span>
                    {entry.name}: {entry.value} file
                    {entry.value !== 1 ? "s" : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
