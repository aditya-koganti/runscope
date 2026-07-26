import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { Pagination } from "../components/Pagination";
import { QueryState } from "../components/QueryState";
import type { Experiment, Page } from "../domain/types";

export function ExperimentsPage() {
  const { accessToken } = useAuth();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const experiments = useQuery({
    queryKey: ["experiments", { search, page }],
    queryFn: () =>
      apiRequest<Page<Experiment>>(
        `/experiments?page=${page}&page_size=20&search=${encodeURIComponent(search)}`,
        {},
        accessToken ?? undefined,
      ),
  });

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Experiments</h1>
          <p>Search and review experiment definitions across projects.</p>
        </div>
      </div>
      <form className="toolbar" role="search" onSubmit={submitSearch}>
        <label className="sr-only" htmlFor="experiment-search">
          Search experiments
        </label>
        <input
          id="experiment-search"
          placeholder="Search experiments"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />
        <button className="button button-secondary" type="submit">
          Search
        </button>
      </form>
      <QueryState
        loading={experiments.isPending}
        error={experiments.isError}
        onRetry={() => void experiments.refetch()}
      >
        {experiments.data?.items.length ? (
          <section className="panel table-panel" aria-label="Experiments">
            <table>
              <thead>
                <tr>
                  <th scope="col">Experiment</th>
                  <th scope="col">Tags</th>
                  <th scope="col">Updated</th>
                </tr>
              </thead>
              <tbody>
                {experiments.data.items.map((experiment) => (
                  <tr key={experiment.id}>
                    <td>
                      <Link className="table-link" to={`/experiments/${experiment.id}`}>
                        {experiment.name}
                      </Link>
                      <small className="cell-detail">{experiment.description}</small>
                    </td>
                    <td>
                      <div className="tag-row">
                        {experiment.tags.map((tag) => (
                          <span className="tag" key={tag}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>{new Date(experiment.updated_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={experiments.data.page}
              pages={experiments.data.pages}
              total={experiments.data.total}
              onPage={setPage}
            />
          </section>
        ) : (
          <section className="panel empty-state">
            <h2>{search ? "No matching experiments" : "No experiments yet"}</h2>
            <p>Create an experiment from a project detail page.</p>
          </section>
        )}
      </QueryState>
    </>
  );
}
