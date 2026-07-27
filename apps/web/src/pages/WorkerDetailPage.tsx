import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type { WorkerDetail } from "../domain/types";

export function WorkerDetailPage() {
  const { workerId = "" } = useParams();
  const { accessToken } = useAuth();
  const detail = useQuery({
    queryKey: ["worker", workerId],
    queryFn: () =>
      apiRequest<WorkerDetail>(
        `/workers/${workerId}`,
        {},
        accessToken ?? undefined,
      ),
    refetchInterval: 5_000,
  });

  return (
    <QueryState
      loading={detail.isPending}
      error={detail.isError}
      onRetry={() => void detail.refetch()}
    >
      {detail.data ? (
        <>
          <div className="breadcrumbs">
            <Link to="/workers">Workers</Link>
            <span>/</span>
            <span>{detail.data.worker.name}</span>
          </div>
          <div className="page-heading">
            <div>
              <p className="eyebrow">Worker capacity</p>
              <h1>{detail.data.worker.name}</h1>
              <p>
                Last heartbeat{" "}
                {new Date(detail.data.worker.last_heartbeat_at).toLocaleString()}
              </p>
            </div>
            <span
              className={`status-badge status-${detail.data.worker.status.toLowerCase()}`}
            >
              {detail.data.worker.status}
            </span>
          </div>
          <section className="metric-grid" aria-label="Worker resources">
            <article className="metric-card">
              <span>Available CPU</span>
              <strong>{detail.data.worker.available_cpu.toFixed(1)}</strong>
              <small>of {detail.data.worker.total_cpu.toFixed(1)} cores</small>
            </article>
            <article className="metric-card">
              <span>Available memory</span>
              <strong>{detail.data.worker.available_memory_mb}</strong>
              <small>of {detail.data.worker.total_memory_mb} MB</small>
            </article>
            <article className="metric-card">
              <span>Active leases</span>
              <strong>{detail.data.worker.current_run_count}</strong>
              <small>database-backed</small>
            </article>
          </section>
          {detail.data.active_allocations.length ? (
            <section className="panel table-panel" aria-label="Active allocations">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Run</th>
                    <th scope="col">CPU</th>
                    <th scope="col">Memory</th>
                    <th scope="col">Lease expiry</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.data.active_allocations.map((allocation) => (
                    <tr key={allocation.id}>
                      <td>
                        <Link className="table-link" to={`/runs/${allocation.run_id}`}>
                          {allocation.run_id.slice(0, 8)}
                        </Link>
                      </td>
                      <td>{allocation.cpu}</td>
                      <td>{allocation.memory_mb} MB</td>
                      <td>{new Date(allocation.lease_expires_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : (
            <section className="panel empty-state compact">
              <h2>No active allocations</h2>
              <p>This worker is ready for a resource-compatible queued run.</p>
            </section>
          )}
        </>
      ) : null}
    </QueryState>
  );
}
