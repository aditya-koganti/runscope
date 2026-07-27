import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type { Experiment, Page, Project, Run } from "../domain/types";

export function ExperimentDetailPage() {
  const { experimentId = "" } = useParams();
  const { accessToken, user } = useAuth();
  const experiment = useQuery({
    queryKey: ["experiment", experimentId],
    queryFn: () =>
      apiRequest<Experiment>(
        `/experiments/${experimentId}`,
        {},
        accessToken ?? undefined,
      ),
  });
  const project = useQuery({
    queryKey: ["project", experiment.data?.project_id],
    enabled: Boolean(experiment.data?.project_id),
    queryFn: () =>
      apiRequest<Project>(
        `/projects/${experiment.data?.project_id}`,
        {},
        accessToken ?? undefined,
      ),
  });
  const runs = useQuery({
    queryKey: ["runs", { experimentId }],
    queryFn: () =>
      apiRequest<Page<Run>>(
        `/runs?experiment_id=${experimentId}&page_size=100`,
        {},
        accessToken ?? undefined,
      ),
  });
  const bestRun = runs.data?.items.find((run) => run.status === "SUCCEEDED");

  return (
    <QueryState
      loading={experiment.isPending}
      error={experiment.isError}
      onRetry={() => void experiment.refetch()}
    >
      {experiment.data ? (
        <>
          <div className="breadcrumbs">
            <Link to="/experiments">Experiments</Link>
            <span>/</span>
            {project.data ? (
              <Link to={`/projects/${project.data.id}`}>{project.data.name}</Link>
            ) : (
              <span>Project</span>
            )}
            <span>/</span>
            <span>{experiment.data.name}</span>
          </div>
          <div className="page-heading">
            <div>
              <p className="eyebrow">Experiment</p>
              <h1>{experiment.data.name}</h1>
              <p>{experiment.data.description || "No experiment description."}</p>
              <div className="tag-row">
                {experiment.data.tags.map((tag) => (
                  <span className="tag" key={tag}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            {user?.role !== "viewer" ? (
              <Link
                className="button button-primary action-link"
                to={`/experiments/${experimentId}/runs/new`}
              >
                Create run
              </Link>
            ) : null}
          </div>
          <section className="metric-grid" aria-label="Experiment summary">
            <article className="metric-card">
              <span>Total runs</span>
              <strong>{runs.data?.total ?? 0}</strong>
              <small>Tracked executions</small>
            </article>
            <article className="metric-card">
              <span>Successful run</span>
              <strong>{bestRun ? "Yes" : "—"}</strong>
              <small>{bestRun ? "Open it below" : "Complete a run to compare"}</small>
            </article>
          </section>
          <section className="section-heading">
            <div>
              <h2>Runs</h2>
              <p>Training attempts and their recorded outcomes.</p>
            </div>
          </section>
          <QueryState
            loading={runs.isPending}
            error={runs.isError}
            onRetry={() => void runs.refetch()}
          >
            {runs.data?.items.length ? (
              <section className="panel table-panel">
                <table>
                  <thead>
                    <tr>
                      <th>Run</th>
                      <th>Status</th>
                      <th>Resources</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.data.items.map((run) => (
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
                <h2>No runs in this experiment</h2>
                <p>Create a run to train the trusted Iris classification template.</p>
              </section>
            )}
          </QueryState>
        </>
      ) : null}
    </QueryState>
  );
}
