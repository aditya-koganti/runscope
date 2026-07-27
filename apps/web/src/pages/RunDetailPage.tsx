import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FormEvent } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError, apiRequest, downloadFile } from "../api/client";
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
  const { accessToken, user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
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
  const cancelRun = useMutation({
    mutationFn: () =>
      apiRequest<Run>(
        `/runs/${runId}/cancel`,
        { method: "POST" },
        accessToken ?? undefined,
      ),
    onSuccess: (updated) => queryClient.setQueryData(["run", runId], updated),
  });
  const retryRun = useMutation({
    mutationFn: () => {
      const failedIntentionally = parameters.data?.find(
        (parameter) => parameter.name === "fail_intentionally",
      )?.value;
      return apiRequest<Run>(
        `/runs/${runId}/retry`,
        {
          method: "POST",
          body: JSON.stringify({
            parameter_overrides:
              failedIntentionally === true ? { fail_intentionally: false } : {},
          }),
        },
        accessToken ?? undefined,
      );
    },
    onSuccess: (retry) => navigate(`/runs/${retry.id}`),
  });
  const updateMetadata = useMutation({
    mutationFn: (body: { notes: string; tags: string[] }) =>
      apiRequest<Run>(
        `/runs/${runId}/metadata`,
        { method: "PATCH", body: JSON.stringify(body) },
        accessToken ?? undefined,
      ),
    onSuccess: (updated) => queryClient.setQueryData(["run", runId], updated),
  });

  function submitMetadata(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    updateMetadata.mutate({
      notes: String(form.get("notes") ?? ""),
      tags: String(form.get("tags") ?? "")
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
    });
  }

  const canControl =
    user?.role === "administrator" ||
    (user?.role === "researcher" && run.data?.created_by === user.id);
  const commandError = cancelRun.error ?? retryRun.error ?? updateMetadata.error;

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
            <div className="heading-actions">
              <span className={`status-badge status-${run.data.status.toLowerCase()}`}>
                {run.data.status}
              </span>
              <span className={`stream-indicator stream-${streamState}`}>
                Live: {streamState}
              </span>
              {canControl && run.data.status === "RUNNING" ? (
                <button
                  className="button button-danger"
                  type="button"
                  disabled={cancelRun.isPending}
                  onClick={() => cancelRun.mutate()}
                >
                  {cancelRun.isPending ? "Cancelling…" : "Cancel run"}
                </button>
              ) : null}
              {canControl && run.data.status === "FAILED" ? (
                <button
                  className="button button-primary"
                  type="button"
                  disabled={retryRun.isPending}
                  onClick={() => retryRun.mutate()}
                >
                  {retryRun.isPending ? "Retrying…" : "Retry run"}
                </button>
              ) : null}
            </div>
          </div>
          {commandError ? (
            <div className="form-error" role="alert">
              {commandError instanceof ApiError
                ? commandError.message
                : "The run could not be updated."}
            </div>
          ) : null}
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
              <span>Worker assignment</span>
              <strong>{run.data.assigned_worker_id ? "Assigned" : "Pending"}</strong>
              <small>
                {run.data.assigned_worker_id ? (
                  <Link to={`/workers/${run.data.assigned_worker_id}`}>
                    {run.data.assigned_worker_id.slice(0, 8)}
                  </Link>
                ) : (
                  "No worker assigned"
                )}
              </small>
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
              {run.data.parent_run_id ? (
                <p>
                  Retried from{" "}
                  <Link className="table-link" to={`/runs/${run.data.parent_run_id}`}>
                    run {run.data.parent_run_id.slice(0, 8)}
                  </Link>
                </p>
              ) : null}
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
          <section className="panel detail-panel metadata-panel">
            <h2>Notes and tags</h2>
            {canControl ? (
              <form className="editor-form metadata-form" onSubmit={submitMetadata}>
                <div>
                  <label htmlFor="run-notes">Notes</label>
                  <textarea
                    id="run-notes"
                    name="notes"
                    rows={3}
                    defaultValue={run.data.notes}
                    placeholder="Record context or conclusions for this run"
                  />
                </div>
                <div>
                  <label htmlFor="run-tags">Tags</label>
                  <input
                    id="run-tags"
                    name="tags"
                    defaultValue={run.data.tags.join(", ")}
                    placeholder="baseline, reviewed"
                  />
                </div>
                <button
                  className="button button-secondary"
                  type="submit"
                  disabled={updateMetadata.isPending}
                >
                  {updateMetadata.isPending ? "Saving…" : "Save metadata"}
                </button>
              </form>
            ) : (
              <>
                <p>{run.data.notes || "No notes recorded."}</p>
                <div className="tag-row">
                  {run.data.tags.map((tag) => (
                    <span className="tag" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </>
            )}
          </section>
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
