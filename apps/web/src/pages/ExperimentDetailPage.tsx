import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type { Experiment, Project } from "../domain/types";

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
              <button className="button button-primary" disabled type="button">
                Create run · next phase
              </button>
            ) : null}
          </div>
          <section className="metric-grid" aria-label="Experiment summary">
            <article className="metric-card">
              <span>Total runs</span>
              <strong>0</strong>
              <small>No run data yet</small>
            </article>
            <article className="metric-card">
              <span>Best metric</span>
              <strong>—</strong>
              <small>Complete a run to compare</small>
            </article>
          </section>
          <section className="panel empty-state">
            <h2>No runs in this experiment</h2>
            <p>Registered training-template execution arrives in the next slice.</p>
          </section>
        </>
      ) : null}
    </QueryState>
  );
}
