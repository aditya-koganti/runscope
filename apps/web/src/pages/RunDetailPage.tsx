import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link, useParams } from "react-router-dom";

import { apiRequest, downloadFile } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type {
  Artifact,
  Experiment,
  Run,
  RunEvent,
  RunLog,
  RunMetric,
  RunParameter,
} from "../domain/types";
import { useRunStream } from "../hooks/useRunStream";

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const { accessToken } = useAuth();
  const streamState = useRunStream(runId, accessToken);
  const request = <T,>(path: string) =>
    apiRequest<T>(path, {}, accessToken ?? undefined);
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => request<Run>(`/runs/${runId}`),
    refetchInterval: (query) =>
      ["SUCCEEDED", "FAILED", "CANCELLED"].includes(
        query.state.data?.status ?? "",
      )
        ? false
        : 1_000,
  });
  const experiment = useQuery({
    queryKey: ["experiment", run.data?.experiment_id],
    enabled: Boolean(run.data?.experiment_id),
    queryFn: () => request<Experiment>(`/experiments/${run.data?.experiment_id}`),
  });
  const metrics = useQuery({
    queryKey: ["run-metrics", runId],
    queryFn: () => request<RunMetric[]>(`/runs/${runId}/metrics`),
    refetchInterval: 5_000,
  });
  const parameters = useQuery({
    queryKey: ["run-parameters", runId],
    queryFn: () => request<RunParameter[]>(`/runs/${runId}/parameters`),
  });
  const logs = useQuery({
    queryKey: ["run-logs", runId],
    queryFn: () => request<RunLog[]>(`/runs/${runId}/logs`),
    refetchInterval: 5_000,
  });
  const events = useQuery({
    queryKey: ["run-events", runId],
    queryFn: () => request<RunEvent[]>(`/runs/${runId}/events`),
    refetchInterval: 5_000,
  });
  const artifacts = useQuery({
    queryKey: ["run-artifacts", runId],
    queryFn: () => request<Artifact[]>(`/runs/${runId}/artifacts`),
    refetchInterval: 5_000,
  });

  return (
    <QueryState
      loading={run.isPending}
      error={run.isError}
      onRetry={() => void run.refetch()}
    >
      {run.data ? (
        <>
          <div className="breadcrumbs">
            <Link to={`/experiments/${run.data.experiment_id}`}>
              {experiment.data?.name ?? "Experiment"}
            </Link>
            <span>/</span>
            <span>Run {run.data.id.slice(0, 8)}</span>
          </div>
          <div className="page-heading">
            <div>
              <p className="eyebrow">Training run</p>
              <h1>Run {run.data.id.slice(0, 8)}</h1>
              <p>Created {formatDate(run.data.created_at)}</p>
            </div>
            <span className={`status-badge status-${run.data.status.toLowerCase()}`}>
              {run.data.status}
            </span>
            <span className={`stream-indicator stream-${streamState}`}>
              Live: {streamState}
            </span>
          </div>
          {run.data.failure_message ? (
            <div className="form-error" role="alert">
              {run.data.failure_message} ({run.data.failure_code})
            </div>
          ) : null}
          <section className="metric-grid" aria-label="Run summary">
            <article className="metric-card">
              <span>CPU request</span>
              <strong>{run.data.requested_cpu}</strong>
              <small>cores</small>
            </article>
            <article className="metric-card">
              <span>Memory request</span>
              <strong>{run.data.requested_memory_mb}</strong>
              <small>MB</small>
            </article>
            <article className="metric-card">
              <span>Attempt</span>
              <strong>{run.data.attempt_number}</strong>
              <small>priority {run.data.priority}</small>
            </article>
            <article className="metric-card">
              <span>Completed</span>
              <strong>{run.data.completed_at ? "Yes" : "No"}</strong>
              <small>{formatDate(run.data.completed_at)}</small>
            </article>
          </section>
          <div className="run-layout">
            <section className="panel detail-panel">
              <h2>Metrics</h2>
              {metrics.data?.length ? (
                <div className="chart">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={metrics.data}>
                      <XAxis dataKey="name" stroke="#8194aa" />
                      <YAxis domain={[0, 1]} stroke="#8194aa" />
                      <Tooltip />
                      <Bar dataKey="value" fill="#64d7b3" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p>No metrics recorded.</p>
              )}
            </section>
            <section className="panel detail-panel">
              <h2>Lifecycle</h2>
              <ol className="timeline">
                {events.data?.map((event) => (
                  <li key={event.id}>
                    <span />
                    <div>
                      <strong>{event.new_status ?? event.event_type}</strong>
                      <small>{formatDate(event.created_at)}</small>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          </div>
          <div className="run-layout">
            <section className="panel detail-panel">
              <h2>Parameters</h2>
              <dl className="property-list">
                {parameters.data?.map((parameter) => (
                  <div key={parameter.id}>
                    <dt>{parameter.name}</dt>
                    <dd>{String(parameter.value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
            <section className="panel detail-panel">
              <h2>Artifacts</h2>
              <div className="artifact-list">
                {artifacts.data?.map((artifact) => (
                  <div key={artifact.id}>
                    <div>
                      <strong>{artifact.name}</strong>
                      <small>{Math.ceil(artifact.size_bytes / 1024)} KB</small>
                    </div>
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => {
                        if (accessToken) {
                          void downloadFile(
                            `/runs/${runId}/artifacts/${artifact.id}/download`,
                            artifact.name,
                            accessToken,
                          );
                        }
                      }}
                    >
                      Download
                    </button>
                  </div>
                ))}
              </div>
            </section>
          </div>
          <section className="panel detail-panel">
            <h2>Logs</h2>
            <div className="log-viewer">
              {logs.data?.map((entry) => (
                <div key={entry.id}>
                  <span>{entry.sequence_number.toString().padStart(3, "0")}</span>
                  <strong>{entry.level}</strong>
                  <code>{entry.message}</code>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </QueryState>
  );
}
