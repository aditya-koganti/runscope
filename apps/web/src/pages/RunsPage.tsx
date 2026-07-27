import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { Pagination } from "../components/Pagination";
import { QueryState } from "../components/QueryState";
import type { Page, Run, RunStatus } from "../domain/types";

const statuses: RunStatus[] = [
  "QUEUED",
  "SCHEDULING",
  "RUNNING",
  "SUCCEEDED",
  "FAILED",
  "CANCELLING",
  "CANCELLED",
];

export function RunsPage() {
  const { accessToken } = useAuth();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const runs = useQuery({
    queryKey: ["runs", { page, status }],
    queryFn: () =>
      apiRequest<Page<Run>>(
        `/runs?page=${page}&page_size=20${status ? `&status=${status}` : ""}`,
        {},
        accessToken ?? undefined,
      ),
  });

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Execution</p>
          <h1>Runs</h1>
          <p>Inspect training history, status, ownership, and retry lineage.</p>
        </div>
        <Link className="button button-primary action-link" to="/runs/compare">
          Compare completed runs
        </Link>
      </div>
      <div className="toolbar">
        <label className="sr-only" htmlFor="run-status-filter">
          Filter by status
        </label>
        <select
          id="run-status-filter"
          value={status}
          onChange={(event) => {
            setPage(1);
            setStatus(event.target.value);
          }}
        >
          <option value="">All statuses</option>
          {statuses.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>
      <QueryState
        loading={runs.isPending}
        error={runs.isError}
        onRetry={() => void runs.refetch()}
      >
        {runs.data?.items.length ? (
          <section className="panel table-panel" aria-label="Runs">
            <table>
              <thead>
                <tr>
                  <th scope="col">Run</th>
                  <th scope="col">Status</th>
                  <th scope="col">Attempt</th>
                  <th scope="col">Resources</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.data.items.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <Link className="table-link" to={`/runs/${run.id}`}>
                        {run.id.slice(0, 8)}
                      </Link>
                      <small className="cell-detail">
                        {run.parent_run_id
                          ? `Retry of ${run.parent_run_id.slice(0, 8)}`
                          : "Original run"}
                      </small>
                    </td>
                    <td>
                      <span
                        className={`status-badge status-${run.status.toLowerCase()}`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td>{run.attempt_number}</td>
                    <td>
                      {run.requested_cpu} CPU · {run.requested_memory_mb} MB
                    </td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={runs.data.page}
              pages={runs.data.pages}
              total={runs.data.total}
              onPage={setPage}
            />
          </section>
        ) : (
          <section className="panel empty-state">
            <h2>No runs found</h2>
            <p>Submit a run from an experiment or change the status filter.</p>
          </section>
        )}
      </QueryState>
    </>
  );
}
