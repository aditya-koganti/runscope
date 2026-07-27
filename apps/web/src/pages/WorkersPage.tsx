import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type { Worker } from "../domain/types";

function utilization(total: number, available: number) {
  return total > 0 ? Math.round(((total - available) / total) * 100) : 0;
}

function heartbeatAge(value: string) {
  const seconds = Math.max(0, Math.round((Date.now() - Date.parse(value)) / 1000));
  return seconds < 60 ? `${seconds}s ago` : `${Math.floor(seconds / 60)}m ago`;
}

export function WorkersPage() {
  const { accessToken } = useAuth();
  const workers = useQuery({
    queryKey: ["workers"],
    queryFn: () =>
      apiRequest<Worker[]>("/workers", {}, accessToken ?? undefined),
    refetchInterval: 5_000,
  });

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Execution pool</p>
          <h1>Workers</h1>
          <p>Heartbeat freshness, allocatable CPU and memory, and active leases.</p>
        </div>
      </div>
      <QueryState
        loading={workers.isPending}
        error={workers.isError}
        onRetry={() => void workers.refetch()}
      >
        {workers.data?.length ? (
          <section className="worker-grid" aria-label="Workers">
            {workers.data.map((worker) => {
              const cpu = utilization(worker.total_cpu, worker.available_cpu);
              const memory = utilization(
                worker.total_memory_mb,
                worker.available_memory_mb,
              );
              return (
                <article className="panel worker-card" key={worker.id}>
                  <div className="worker-heading">
                    <div>
                      <Link className="table-link" to={`/workers/${worker.id}`}>
                        {worker.name}
                      </Link>
                      <small>Heartbeat {heartbeatAge(worker.last_heartbeat_at)}</small>
                    </div>
                    <span
                      className={`status-badge status-${worker.status.toLowerCase()}`}
                    >
                      {worker.status}
                    </span>
                  </div>
                  <div className="utilization">
                    <div>
                      <span>CPU</span>
                      <strong>
                        {worker.available_cpu.toFixed(1)} / {worker.total_cpu.toFixed(1)} free
                      </strong>
                    </div>
                    <progress max={100} value={cpu} aria-label={`${worker.name} CPU use`} />
                    <div>
                      <span>Memory</span>
                      <strong>
                        {worker.available_memory_mb} / {worker.total_memory_mb} MB free
                      </strong>
                    </div>
                    <progress
                      max={100}
                      value={memory}
                      aria-label={`${worker.name} memory use`}
                    />
                  </div>
                  <p>{worker.current_run_count} active run leases</p>
                </article>
              );
            })}
          </section>
        ) : (
          <section className="panel empty-state">
            <h2>No workers registered</h2>
            <p>Start a worker service to register capacity and heartbeats.</p>
          </section>
        )}
      </QueryState>
    </>
  );
}
