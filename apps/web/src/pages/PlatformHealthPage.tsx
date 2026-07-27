import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type { DependencyHealth, PlatformSummary } from "../domain/types";

export function PlatformHealthPage() {
  const { accessToken } = useAuth();
  const dependencies = useQuery({
    queryKey: ["platform-dependencies"],
    queryFn: () =>
      apiRequest<DependencyHealth>(
        "/platform/dependencies",
        {},
        accessToken ?? undefined,
      ),
    refetchInterval: 5_000,
  });
  const summary = useQuery({
    queryKey: ["platform-summary"],
    queryFn: () =>
      apiRequest<PlatformSummary>(
        "/platform/summary",
        {},
        accessToken ?? undefined,
      ),
    refetchInterval: 5_000,
  });

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Platform health</h1>
          <p>Bounded live probes and durable control-plane backlog.</p>
        </div>
        {dependencies.data ? (
          <span
            className={`status-badge status-${dependencies.data.status === "healthy" ? "online" : "failed"}`}
          >
            {dependencies.data.status}
          </span>
        ) : null}
      </div>
      <QueryState
        loading={dependencies.isPending || summary.isPending}
        error={dependencies.isError || summary.isError}
        onRetry={() => {
          void dependencies.refetch();
          void summary.refetch();
        }}
      >
        <section className="dependency-grid" aria-label="Dependency health">
          {Object.entries(dependencies.data?.dependencies ?? {}).map(
            ([name, dependency]) => (
              <article className="panel dependency-card" key={name}>
                <div>
                  <strong>{name}</strong>
                  <span
                    className={`status-badge status-${dependency.status === "healthy" ? "online" : "failed"}`}
                  >
                    {dependency.status}
                  </span>
                </div>
                <p>{dependency.latency_ms.toFixed(2)} ms probe latency</p>
              </article>
            ),
          )}
        </section>
        {summary.data ? (
          <section className="metric-grid health-metrics" aria-label="Platform capacity">
            <article className="metric-card">
              <span>Queue depth</span>
              <strong>{summary.data.queue_depth}</strong>
              <small>durable queued runs</small>
            </article>
            <article className="metric-card">
              <span>Outbox backlog</span>
              <strong>{summary.data.unpublished_messages}</strong>
              <small>awaiting Redpanda</small>
            </article>
            <article className="metric-card">
              <span>Available CPU</span>
              <strong>{summary.data.available_cpu.toFixed(1)}</strong>
              <small>of {summary.data.total_cpu.toFixed(1)} cores</small>
            </article>
            <article className="metric-card">
              <span>Available memory</span>
              <strong>{summary.data.available_memory_mb}</strong>
              <small>of {summary.data.total_memory_mb} MB</small>
            </article>
          </section>
        ) : null}
      </QueryState>
    </>
  );
}
