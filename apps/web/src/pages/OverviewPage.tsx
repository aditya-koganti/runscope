import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "../api/client";

interface Health {
  status: "ok";
  service: string;
}

export function OverviewPage() {
  const health = useQuery({
    queryKey: ["api-health"],
    queryFn: () => apiRequest<Health>("/health"),
  });

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Control plane</p>
          <h1>Overview</h1>
          <p>Operational status and recent machine-learning activity.</p>
        </div>
        <div
          className={`health-pill ${health.isError ? "health-error" : ""}`}
          aria-live="polite"
        >
          <span aria-hidden="true" />
          {health.isPending
            ? "Checking API"
            : health.isError
              ? "API unavailable"
              : "API operational"}
        </div>
      </div>
      <section className="metric-grid" aria-label="Run summary">
        {[
          ["Active runs", "0"],
          ["Queued runs", "0"],
          ["Failed runs", "0"],
          ["Workers online", "0"],
        ].map(([label, value]) => (
          <article className="metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>Awaiting domain data</small>
          </article>
        ))}
      </section>
      <section className="panel empty-state">
        <div className="empty-icon" aria-hidden="true">
          ↗
        </div>
        <h2>No runs yet</h2>
        <p>Create a project and experiment before submitting a registered template.</p>
      </section>
    </>
  );
}
