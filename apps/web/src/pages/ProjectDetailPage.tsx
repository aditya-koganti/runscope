import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type { Experiment, Page, Project } from "../domain/types";

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  const { accessToken, user } = useAuth();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () =>
      apiRequest<Project>(`/projects/${projectId}`, {}, accessToken ?? undefined),
  });
  const experiments = useQuery({
    queryKey: ["experiments", { projectId }],
    queryFn: () =>
      apiRequest<Page<Experiment>>(
        `/experiments?project_id=${projectId}&page_size=100`,
        {},
        accessToken ?? undefined,
      ),
  });
  const createExperiment = useMutation({
    mutationFn: () =>
      apiRequest<Experiment>(
        "/experiments",
        {
          method: "POST",
          body: JSON.stringify({
            project_id: projectId,
            name,
            description,
            tags: tags
              .split(",")
              .map((tag) => tag.trim())
              .filter(Boolean),
          }),
        },
        accessToken ?? undefined,
      ),
    onSuccess: async () => {
      setName("");
      setDescription("");
      setTags("");
      setShowCreate(false);
      await queryClient.invalidateQueries({ queryKey: ["experiments"] });
    },
  });

  function submitExperiment(event: FormEvent) {
    event.preventDefault();
    createExperiment.mutate();
  }

  return (
    <QueryState
      loading={project.isPending}
      error={project.isError}
      onRetry={() => void project.refetch()}
    >
      {project.data ? (
        <>
          <div className="breadcrumbs">
            <Link to="/projects">Projects</Link>
            <span>/</span>
            <span>{project.data.name}</span>
          </div>
          <div className="page-heading">
            <div>
              <p className="eyebrow">Project</p>
              <h1>{project.data.name}</h1>
              <p>{project.data.description || "No project description."}</p>
            </div>
            {user?.role !== "viewer" ? (
              <button
                className="button button-primary"
                onClick={() => setShowCreate((value) => !value)}
                type="button"
              >
                {showCreate ? "Close" : "New experiment"}
              </button>
            ) : null}
          </div>
          {showCreate ? (
            <form className="panel editor-form" onSubmit={submitExperiment}>
              <div>
                <label htmlFor="experiment-name">Experiment name</label>
                <input
                  id="experiment-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  minLength={2}
                  required
                />
              </div>
              <div>
                <label htmlFor="experiment-description">Description</label>
                <textarea
                  id="experiment-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={3}
                />
              </div>
              <div>
                <label htmlFor="experiment-tags">Tags</label>
                <input
                  id="experiment-tags"
                  value={tags}
                  onChange={(event) => setTags(event.target.value)}
                  placeholder="baseline, iris, review"
                />
                <small>Comma-separated, up to 20 tags.</small>
              </div>
              {createExperiment.isError ? (
                <div className="form-error" role="alert">
                  The experiment could not be created. Names must be unique in a
                  project.
                </div>
              ) : null}
              <button
                className="button button-primary"
                disabled={createExperiment.isPending || name.trim().length < 2}
                type="submit"
              >
                {createExperiment.isPending ? "Creating…" : "Create experiment"}
              </button>
            </form>
          ) : null}
          <section className="section-heading">
            <div>
              <h2>Experiments</h2>
              <p>Configurations and runs tracked inside this project.</p>
            </div>
          </section>
          <QueryState
            loading={experiments.isPending}
            error={experiments.isError}
            onRetry={() => void experiments.refetch()}
          >
            {experiments.data?.items.length ? (
              <div className="card-grid">
                {experiments.data.items.map((experiment) => (
                  <Link
                    className="panel entity-card"
                    key={experiment.id}
                    to={`/experiments/${experiment.id}`}
                  >
                    <div>
                      <h3>{experiment.name}</h3>
                      <p>{experiment.description || "No description"}</p>
                    </div>
                    <div className="tag-row">
                      {experiment.tags.map((tag) => (
                        <span className="tag" key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <section className="panel empty-state compact">
                <h2>No experiments</h2>
                <p>Create an experiment to define a sequence of comparable runs.</p>
              </section>
            )}
          </QueryState>
        </>
      ) : null}
    </QueryState>
  );
}
