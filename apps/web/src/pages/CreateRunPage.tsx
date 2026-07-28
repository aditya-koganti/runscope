import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError, apiRequest } from "../api/client";
import { useAuth } from "../auth/authState";
import { QueryState } from "../components/QueryState";
import type {
  Experiment,
  ParameterProperty,
  Run,
  TrainingTemplate,
} from "../domain/types";

function initialValues(template?: TrainingTemplate): Record<string, string> {
  const values: Record<string, string> = {};
  for (const [name, property] of Object.entries(
    template?.parameter_schema.properties ?? {},
  )) {
    values[name] = String(property.default ?? "");
  }
  return values;
}

function serializeValue(value: string, property: ParameterProperty) {
  if (property.type === "integer") return Number.parseInt(value, 10);
  if (property.type === "number") return Number.parseFloat(value);
  if (property.type === "boolean") return value === "true";
  return value;
}

export function CreateRunPage() {
  const { experimentId = "" } = useParams();
  const { accessToken } = useAuth();
  const navigate = useNavigate();
  const [templateKey, setTemplateKey] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [cpu, setCpu] = useState("1");
  const [memory, setMemory] = useState("512");
  const [priority, setPriority] = useState("0");

  const experiment = useQuery({
    queryKey: ["experiment", experimentId],
    queryFn: () =>
      apiRequest<Experiment>(
        `/experiments/${experimentId}`,
        {},
        accessToken ?? undefined,
      ),
  });
  const templates = useQuery({
    queryKey: ["training-templates"],
    queryFn: () =>
      apiRequest<TrainingTemplate[]>("/templates", {}, accessToken ?? undefined),
  });
  const effectiveTemplateKey = templateKey || templates.data?.[0]?.key || "";
  const selected = useMemo(
    () =>
      templates.data?.find(
        (template) => template.key === effectiveTemplateKey,
      ),
    [effectiveTemplateKey, templates.data],
  );

  const createRun = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error("Select a training template");
      const parameters = Object.fromEntries(
        Object.entries(selected.parameter_schema.properties ?? {}).map(
          ([name, property]) => [
            name,
            serializeValue(
              values[name] ?? String(property.default ?? ""),
              property,
            ),
          ],
        ),
      );
      return apiRequest<Run>(
        "/runs",
        {
          method: "POST",
          body: JSON.stringify({
            experiment_id: experimentId,
            template_key: selected.key,
            template_version: selected.version,
            parameters,
            requested_cpu: Number(cpu),
            requested_memory_mb: Number(memory),
            priority: Number(priority),
          }),
        },
        accessToken ?? undefined,
      );
    },
    onSuccess: (run) => navigate(`/runs/${run.id}`),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    createRun.mutate();
  }

  return (
    <QueryState
      loading={experiment.isPending || templates.isPending}
      error={experiment.isError || templates.isError}
      onRetry={() => {
        void experiment.refetch();
        void templates.refetch();
      }}
    >
      <div className="breadcrumbs">
        <Link to={`/experiments/${experimentId}`}>
          {experiment.data?.name ?? "Experiment"}
        </Link>
        <span>/</span>
        <span>New run</span>
      </div>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Trusted execution</p>
          <h1>Create run</h1>
          <p>
            Choose a reviewed template. RunScope validates every parameter before
            executing the built-in training code.
          </p>
        </div>
      </div>
      {templates.data?.length ? (
        <form className="panel editor-form run-form" onSubmit={submit}>
          <div>
            <label htmlFor="run-template">Training template</label>
            <select
              id="run-template"
              value={effectiveTemplateKey}
              onChange={(event) => {
                setTemplateKey(event.target.value);
                setValues(
                  initialValues(
                    templates.data?.find(
                      (template) => template.key === event.target.value,
                    ),
                  ),
                );
              }}
            >
              {templates.data.map((template) => (
                <option key={template.id} value={template.key}>
                  {template.name} | {template.version}
                </option>
              ))}
            </select>
            <small>{selected?.description}</small>
          </div>
          <div className="form-section">
            <h2>Template parameters</h2>
            <div className="form-grid">
              {Object.entries(selected?.parameter_schema.properties ?? {}).map(
                ([name, property]) => (
                  <div key={name}>
                    <label htmlFor={`parameter-${name}`}>
                      {property.title ?? name.replaceAll("_", " ")}
                    </label>
                    {property.type === "boolean" ? (
                      <select
                        id={`parameter-${name}`}
                        value={values[name] ?? String(property.default ?? false)}
                        onChange={(event) =>
                          setValues((current) => ({
                            ...current,
                            [name]: event.target.value,
                          }))
                        }
                      >
                        <option value="false">No</option>
                        <option value="true">Yes</option>
                      </select>
                    ) : (
                      <input
                        id={`parameter-${name}`}
                        type={
                          property.type === "integer" || property.type === "number"
                            ? "number"
                            : "text"
                        }
                        step={property.type === "integer" ? 1 : "any"}
                        min={property.minimum}
                        max={property.maximum}
                        value={values[name] ?? String(property.default ?? "")}
                        onChange={(event) =>
                          setValues((current) => ({
                            ...current,
                            [name]: event.target.value,
                          }))
                        }
                        required
                      />
                    )}
                    <small>{property.description}</small>
                  </div>
                ),
              )}
            </div>
          </div>
          <div className="form-section">
            <h2>Resource request</h2>
            <div className="form-grid three">
              <div>
                <label htmlFor="run-cpu">CPU cores</label>
                <input
                  id="run-cpu"
                  type="number"
                  min="0.1"
                  max="4"
                  step="0.1"
                  value={cpu}
                  onChange={(event) => setCpu(event.target.value)}
                  required
                />
              </div>
              <div>
                <label htmlFor="run-memory">Memory (MB)</label>
                <input
                  id="run-memory"
                  type="number"
                  min="128"
                  max="8192"
                  value={memory}
                  onChange={(event) => setMemory(event.target.value)}
                  required
                />
              </div>
              <div>
                <label htmlFor="run-priority">Priority</label>
                <input
                  id="run-priority"
                  type="number"
                  min="-10"
                  max="10"
                  value={priority}
                  onChange={(event) => setPriority(event.target.value)}
                  required
                />
              </div>
            </div>
          </div>
          {createRun.isError ? (
            <div className="form-error" role="alert">
              {createRun.error instanceof ApiError
                ? createRun.error.message
                : "The run could not be created."}
            </div>
          ) : null}
          <button
            className="button button-primary"
            disabled={createRun.isPending || !selected}
            type="submit"
          >
            {createRun.isPending ? "Training model..." : "Create and execute run"}
          </button>
        </form>
      ) : (
        <section className="panel empty-state compact">
          <h2>No training templates available</h2>
          <p>Run the seed command to register trusted templates.</p>
        </section>
      )}
    </QueryState>
  );
}
