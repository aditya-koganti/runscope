import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { Pagination } from "../components/Pagination";
import { QueryState } from "../components/QueryState";
import type { Page, Project } from "../domain/types";

export function ProjectsPage() {
  const { accessToken, user } = useAuth();
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const projects = useQuery({
    queryKey: ["projects", search, page],
    queryFn: () =>
      apiRequest<Page<Project>>(
        `/projects?page=${page}&page_size=20&search=${encodeURIComponent(search)}`,
        {},
        accessToken ?? undefined,
      ),
  });
  const createProject = useMutation({
    mutationFn: () =>
      apiRequest<Project>(
        "/projects",
        {
          method: "POST",
          body: JSON.stringify({ name, description }),
        },
        accessToken ?? undefined,
      ),
    onSuccess: async () => {
      setName("");
      setDescription("");
      setShowCreate(false);
      setPage(1);
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
  const canWrite = user?.role !== "viewer";

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  }

  function submitProject(event: FormEvent) {
    event.preventDefault();
    createProject.mutate();
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Projects</h1>
          <p>Organize related experiments and trusted training runs.</p>
        </div>
        {canWrite ? (
          <button
            className="button button-primary"
            onClick={() => setShowCreate((value) => !value)}
            type="button"
          >
            {showCreate ? "Close" : "New project"}
          </button>
        ) : null}
      </div>

      {showCreate ? (
        <form className="panel editor-form" onSubmit={submitProject}>
          <div>
            <label htmlFor="project-name">Project name</label>
            <input
              id="project-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              minLength={2}
              maxLength={120}
              required
            />
          </div>
          <div>
            <label htmlFor="project-description">Description</label>
            <textarea
              id="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={2000}
              rows={3}
            />
          </div>
          {createProject.isError ? (
            <div className="form-error" role="alert">
              Project creation failed. Check the values and retry.
            </div>
          ) : null}
          <button
            className="button button-primary"
            disabled={createProject.isPending || name.trim().length < 2}
            type="submit"
          >
            {createProject.isPending ? "Creating…" : "Create project"}
          </button>
        </form>
      ) : null}

      <form className="toolbar" role="search" onSubmit={submitSearch}>
        <label className="sr-only" htmlFor="project-search">
          Search projects
        </label>
        <input
          id="project-search"
          placeholder="Search projects"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />
        <button className="button button-secondary" type="submit">
          Search
        </button>
      </form>

      <QueryState
        loading={projects.isPending}
        error={projects.isError}
        onRetry={() => void projects.refetch()}
      >
        {projects.data?.items.length ? (
          <section className="panel table-panel" aria-label="Projects">
            <table>
              <thead>
                <tr>
                  <th scope="col">Project</th>
                  <th scope="col">Description</th>
                  <th scope="col">Updated</th>
                </tr>
              </thead>
              <tbody>
                {projects.data.items.map((project) => (
                  <tr key={project.id}>
                    <td>
                      <Link className="table-link" to={`/projects/${project.id}`}>
                        {project.name}
                      </Link>
                    </td>
                    <td>{project.description || "No description"}</td>
                    <td>{new Date(project.updated_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={projects.data.page}
              pages={projects.data.pages}
              total={projects.data.total}
              onPage={setPage}
            />
          </section>
        ) : (
          <section className="panel empty-state">
            <div className="empty-icon" aria-hidden="true">
              P
            </div>
            <h2>{search ? "No matching projects" : "No projects yet"}</h2>
            <p>
              {search
                ? "Try a different name or description."
                : "Create a project to give experiments a durable home."}
            </p>
          </section>
        )}
      </QueryState>
    </>
  );
}
