# RunScope Product Requirements

## Purpose

RunScope is a portfolio-quality, open-source experiment and CPU job-management
platform for ML engineers and data scientists. It demonstrates the control-plane
and execution-plane concerns of a small ML platform without pretending to be
production cluster infrastructure.

## Primary workflow

A signed-in researcher creates a project and experiment, selects an approved
training template, supplies schema-validated parameters and CPU/memory requests,
submits a run, observes status/logs/metrics, and downloads generated artifacts.
Researchers can cancel eligible runs, retry failed runs, and compare successful
runs. Viewers have read-only access. Administrators manage templates and
platform-level data.

## Required capabilities

- Local sign-in and role-based authorization.
- Project and experiment CRUD, search, filtering, sorting, and pagination.
- Registry of trusted versioned training templates.
- Durable run lifecycle, logs, metrics, events, notes, tags, and artifacts.
- Real scikit-learn classification execution.
- Slow cancellable/failable demonstration execution.
- Resource-aware scheduling across multiple worker processes.
- Kafka-compatible versioned events through Redpanda.
- MinIO-backed artifacts through an S3 abstraction.
- SSE live updates with REST fallback and reconnect behavior.
- Worker capacity and dependency-health views.
- Run comparison for two to five completed runs.

## Personas

- **Viewer:** audits projects, experiments, runs, workers, and health.
- **Researcher:** creates work and controls authorized runs.
- **Administrator:** has researcher access plus platform/template management.

## Non-goals

- Arbitrary user code, shell commands, images, or packages.
- GPU scheduling, HPC semantics, distributed training, or autoscaling.
- Multi-tenant enterprise identity, SSO, fine-grained organization policy, or
  security claims beyond a local portfolio demonstration.
- Production durability, high availability, or unbounded workload scale.

## Success criteria

The documented Docker Compose workflow can execute the primary workflow using
real PostgreSQL persistence, a real registered scikit-learn template, durable
artifacts, and tested lifecycle behavior. Any environment-dependent verification
that cannot run is recorded explicitly rather than inferred.

