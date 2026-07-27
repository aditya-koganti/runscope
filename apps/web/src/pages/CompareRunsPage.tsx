import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router";

import { ApiError, apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type { Page, Run, RunComparison } from "../domain/types";

const chartColors = ["#64d7b3", "#82aaff", "#f2b36d", "#d98cff", "#ff8f9a"];

function displayValue(value: unknown) {
  if (value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function CompareRunsPage() {
  const { accessToken } = useAuth();
  const [selected, setSelected] = useState<string[]>([]);
  const candidates = useQuery({
    queryKey: ["runs", { status: "SUCCEEDED", pageSize: 100 }],
    queryFn: () =>
      apiRequest<Page<Run>>(
        "/runs?status=SUCCEEDED&page_size=100",
        {},
        accessToken ?? undefined,
      ),
  });
  const comparison = useMutation({
    mutationFn: () =>
      apiRequest<RunComparison>(
        "/runs/compare",
        {
          method: "POST",
          body: JSON.stringify({ run_ids: selected }),
        },
        accessToken ?? undefined,
      ),
  });

  const parameterNames = Array.from(
    new Set(comparison.data?.items.flatMap((item) => Object.keys(item.parameters))),
  ).sort();
  const metricNames = Array.from(
    new Set(comparison.data?.items.flatMap((item) => Object.keys(item.metrics))),
  ).sort();
  const chartData =
    comparison.data?.items.map((item) => ({
      run: item.run.id.slice(0, 8),
      ...item.metrics,
    })) ?? [];

  return (
    <>
      <div className="breadcrumbs">
        <Link to="/runs">Runs</Link>
        <span>/</span>
        <span>Compare</span>
      </div>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Analysis</p>
          <h1>Compare runs</h1>
          <p>Select two to five successful runs to compare final values.</p>
        </div>
      </div>
      <QueryState
        loading={candidates.isPending}
        error={candidates.isError}
        onRetry={() => void candidates.refetch()}
      >
        {candidates.data?.items.length ? (
          <section className="panel compare-picker" aria-label="Completed runs">
            {candidates.data.items.map((run) => (
              <label key={run.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(run.id)}
                  disabled={!selected.includes(run.id) && selected.length === 5}
                  onChange={(event) =>
                    setSelected((current) =>
                      event.target.checked
                        ? [...current, run.id]
                        : current.filter((id) => id !== run.id),
                    )
                  }
                />
                <span>
                  <strong>Run {run.id.slice(0, 8)}</strong>
                  <small>
                    Attempt {run.attempt_number} · {new Date(run.created_at).toLocaleString()}
                  </small>
                </span>
              </label>
            ))}
            <button
              className="button button-primary"
              type="button"
              disabled={selected.length < 2 || comparison.isPending}
              onClick={() => comparison.mutate()}
            >
              {comparison.isPending
                ? "Comparing…"
                : `Compare ${selected.length || ""} runs`}
            </button>
          </section>
        ) : (
          <section className="panel empty-state compact">
            <h2>No successful runs yet</h2>
            <p>Complete at least two runs before comparing them.</p>
          </section>
        )}
      </QueryState>
      {comparison.isError ? (
        <div className="form-error" role="alert">
          {comparison.error instanceof ApiError
            ? comparison.error.message
            : "The runs could not be compared."}
        </div>
      ) : null}
      {comparison.data ? (
        <div className="comparison-results">
          <section className="panel table-panel" aria-label="Parameter comparison">
            <div className="panel-title">
              <h2>Parameters</h2>
            </div>
            <table>
              <thead>
                <tr>
                  <th scope="col">Parameter</th>
                  {comparison.data.items.map((item) => (
                    <th key={item.run.id} scope="col">
                      <Link to={`/runs/${item.run.id}`}>{item.run.id.slice(0, 8)}</Link>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parameterNames.map((name) => (
                  <tr key={name}>
                    <th scope="row">{name}</th>
                    {comparison.data.items.map((item) => (
                      <td key={item.run.id}>{displayValue(item.parameters[name])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel table-panel" aria-label="Metric comparison">
            <div className="panel-title">
              <h2>Final metrics</h2>
            </div>
            <table>
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  {comparison.data.items.map((item) => (
                    <th key={item.run.id} scope="col">
                      {item.run.id.slice(0, 8)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metricNames.map((name) => (
                  <tr key={name}>
                    <th scope="row">{name}</th>
                    {comparison.data.items.map((item) => (
                      <td
                        className={
                          comparison.data.best_by_metric[name] === item.run.id
                            ? "best-value"
                            : undefined
                        }
                        key={item.run.id}
                      >
                        {item.metrics[name]?.toFixed(4) ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel detail-panel" aria-label="Metric comparison chart">
            <h2>Metric overlay</h2>
            <div className="chart">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={chartData}>
                  <CartesianGrid stroke="#26374c" />
                  <XAxis dataKey="run" stroke="#8194aa" />
                  <YAxis stroke="#8194aa" />
                  <Tooltip />
                  <Legend />
                  {metricNames.map((name, index) => (
                    <Bar
                      key={name}
                      dataKey={name}
                      fill={chartColors[index % chartColors.length]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
