import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import type { Page, PlatformSummary, Run } from "../domain/types";

interface Health {
  status: "ok";
  service: string;
}

export function OverviewPage() {
  const { accessToken } = useAuth();
  const health = useQuery({
    queryKey: ["api-health"],
    queryFn: () => apiRequest<Health>("/health"),
  });
  const runs = useQuery({
    queryKey: ["overview-runs"],
    queryFn: () =>
      apiRequest<Page<Run>>(
        "/runs?page_size=100",
        {},
        accessToken ?? undefined,
      ),
    refetchInterval: 5_000,
  });
  const summary = useQuery({
    queryKey: ["platform-summary"],
    queryFn: () =>
      apiRequest<PlatformSummary>(
        "/platform/summary",
        {},
        accessToken ?? undefined,
      ),
    refetchInterval: 5_000,
  });
  const runItems = Array.isArray(runs.data?.items) ? runs.data.items : [];
  const metrics = [
    ["Active runs", summary.data?.active_runs ?? 0, "currently executing"],
    ["Queue depth", summary.data?.queue_depth ?? 0, "waiting for capacity"],
    ["Failed runs", summary.data?.failed_runs ?? 0, "durable failures"],
    [
      "Success rate",
      `${((summary.data?.success_rate ?? 0) * 100).toFixed(1)}%`,
      "terminal runs",
    ],
    [
      "Average duration",
      summary.data?.average_duration_seconds == null
        ? "—"
        : `${summary.data.average_duration_seconds.toFixed(1)}s`,
      "completed runs",
    ],
    [
      "Workers online",
      `${summary.data?.workers_online ?? 0}/${summary.data?.workers_total ?? 0}`,
      "fresh heartbeats",
    ],
    [
      "Available CPU",
      (summary.data?.available_cpu ?? 0).toFixed(1),
      `of ${(summary.data?.total_cpu ?? 0).toFixed(1)} cores`,
    ],
    [
      "Outbox backlog",
      summary.data?.unpublished_messages ?? 0,
      "unpublished events",
    ],
  ] as const;

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Control plane</p>
          <h1>Overview</h1>
          <p>Operational status and recent machine-learning activity.</p>
        </div>
        <div
          className={`health-pill ${health.isError ? "health-error" : ""}`}
          aria-live="polite"
        >
          <span aria-hidden="true" />
          {health.isPending
            ? "Checking API"
            : health.isError
              ? "API unavailable"
              : "API operational"}
        </div>
      </div>
      <section className="metric-grid" aria-label="Run summary">
        {metrics.map(([label, value, detail]) => (
          <article className="metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </section>
      {runItems.length ? (
        <section className="panel table-panel" aria-label="Recent activity">
          <table>
            <thead>
              <tr>
                <th scope="col">Recent run</th>
                <th scope="col">Status</th>
                <th scope="col">Resources</th>
                <th scope="col">Created</th>
              </tr>
            </thead>
            <tbody>
              {runItems.slice(0, 8).map((run) => (
                <tr key={run.id}>
                  <td>
                    <Link className="table-link" to={`/runs/${run.id}`}>
                      {run.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>
                    <span
                      className={`status-badge status-${run.status.toLowerCase()}`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td>
                    {run.requested_cpu} CPU · {run.requested_memory_mb} MB
                  </td>
                  <td>{new Date(run.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : (
        <section className="panel empty-state">
          <div className="empty-icon" aria-hidden="true">
            ↗
          </div>
          <h2>No runs yet</h2>
          <p>Create a project and experiment before submitting a registered template.</p>
        </section>
      )}
    </>
  );
}
