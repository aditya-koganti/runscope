# Test Strategy

## Phase 4 verification snapshot

- 92 backend tests pass, including all state/status pairs, real scikit-learn
  execution, model deserialization, authenticated artifact download, and the
  full API run workflow.
- 5 frontend component tests pass; ESLint, TypeScript, and the production build
  pass.
- Playwright verifies sign-in, project/experiment creation, real classification
  completion, logs, metrics, and a browser download.
- Alembic revision `0003` was applied against PostgreSQL and the trusted
  template was seeded successfully.

## Phase 5 verification snapshot

- 93 Python tests pass across API, contracts, and worker, including duplicate
  event consumption as a durable no-op.
- Alembic revision `0004` was applied to PostgreSQL.
- The composed API, Redpanda, worker, and MinIO path completed real training and
  an authenticated artifact request through Playwright.
- A read-only database check recorded four published outbox messages, four
  processed-message records, and durable artifact metadata after repeated test
  runs. These are local verification counts, not benchmark results.

## Phase 6 verification snapshot

- The Python gate remains at 93 passing tests, including a controlled Redis
  failure that still reaches durable `SUCCEEDED`.
- Frontend lint/type checks, 6 Vitest tests, and the production build pass.
- Playwright observes `Live: connected`, receives the worker-driven completion,
  renders logs/metrics, and verifies the authenticated artifact response.
- The first integration attempt intentionally informed the final design:
  missing Redis previously exposed that an ephemeral publish could interrupt
  work. The dependency graph and worker error boundary now prevent that class of
  failure.

## Phase 7 verification snapshot

- 94 Python tests pass, including command authorization, cancellation state,
  validated retry overrides and lineage, normalized notes/tags, comparison, and
  duplicate-ID rejection.
- Frontend ESLint and TypeScript checks pass; 6 Vitest tests and the production
  Vite build pass in the development image.
- The production API/worker and web images build successfully, and all seven
  Compose services start with the API and dependencies healthy.
- A 34-second real Chromium workflow signs in, creates project/experiment data,
  completes and downloads a classification artifact, cancels a live slow run,
  retries an intentional failure to success, saves metadata, and compares the
  two successful runs.

## Phase 8 verification snapshot

- 100 Python tests pass. Scheduler coverage includes compatible assignment,
  insufficient capacity, priority ordering, duplicate invocation, expired
  leases, stale workers, and restart-safe reconciliation.
- Frontend ESLint and TypeScript checks, 6 Vitest tests, and the production
  Vite build pass with live overview and worker-capacity pages.
- Alembic revision `0005` applied successfully to PostgreSQL. The nine-service
  Compose topology runs a separate scheduler and two independently identified
  workers.
- The real Chromium workflow passed through scheduler assignment and targeted
  worker execution, then rendered both workers. Four workflow allocations were
  persisted and all four released; both workers returned to full capacity.

## Phase 9 verification snapshot

- 107 Python tests pass under Python 3.12. They include bounded artifact retries,
  temporary broker recovery, Redis-independent durable execution, secret-key
  redaction, correlation isolation, stable unexpected-error responses, degraded
  readiness, and Prometheus metric exposure.
- Frontend ESLint and TypeScript checks pass; 7 Vitest tests and the production
  Vite build pass. The platform-health component test covers dependency latency,
  scheduler status, capacity, and outbox backlog.
- `docker compose config --quiet` passes and all nine rebuilt services start.
  PostgreSQL, Redis, Redpanda, MinIO, and the API reported healthy.
- The real Chromium workflow passed in 21.7 seconds and exercised classification,
  artifact download, cancellation, intentional failure/retry, comparison, both
  workers, and the authenticated platform-health page.

## Phase 10 verification snapshot

- The Python 3.12 development image contains the declared dev dependency set;
  the existing 107-test backend suite remains the correctness baseline.
- The Node 22.22 development image installs the locked React 19/React Router 8
  tree with `npm ci`; frontend lint, TypeScript, 7 Vitest tests, and the
  production build pass.
- Production API and web containers build and run as non-root users. All nine
  Compose services start, and the web origin successfully proxies API health.
- The final full Chromium workflow passes through the production proxy in 24.2
  seconds (19.5 seconds in the test). It covers real execution, artifacts,
  cancellation, failure/retry, comparison, workers, and platform health.
- Kustomize renders ten Kubernetes resources, all ten of which pass
  kubeconform 0.6.7 against Kubernetes 1.29 schemas. No cluster rollout was
  performed.
- The 5-user read/SSE and 2-user mutating Locust smoke runs completed without
  failures. Exact latency and scheduling results are recorded in
  `docs/PERFORMANCE.md`.
- `npm audit --audit-level=high` reports zero vulnerabilities. The Python audit
  and Docker Scout image scans were not allowed locally because they may
  disclose dependency metadata; equivalent blocking CI gates are configured
  but not claimed as executed.

## Layers

- **Backend unit:** state transitions (all valid and invalid pairs), validation,
  permissions, registry safety, error mapping, idempotency, and storage/broker
  contracts.
- **API:** authentication and roles, CRUD, pagination/search, run commands and
  reads, telemetry, artifacts, workers, health, and structured errors.
- **Scheduler:** priority/capacity selection, duplicate invocations, leases,
  expiry, stale workers, and restart reconciliation.
- **Worker:** registered execution, duplicate assignments, cancellation, success,
  failure, artifact failure, bounded retry, and terminal-state protection.
- **Frontend:** auth, route protection, generated forms, validation, loading,
  empty/error states, tables/charts/status, SSE state, and role controls.
- **Integration:** PostgreSQL/Redis/Redpanda/MinIO-backed boundaries.
- **End to end:** the thirteen-step product workflow in the product brief.
- **Reliability:** duplicate messages and controlled dependency/restart failures.

## Principles

Unit tests use deterministic clocks/IDs where time or identity matters. Service
integration tests are marked and skipped only when their documented dependency
profile is absent. Skips are reported, never described as passes. The primary
Compose E2E suite must exercise actual services, not mock HTTP responses.

## Phase gates

Each phase runs the smallest complete relevant set plus formatting, lint, and
type checks. Frontend changes require a production build. Infrastructure changes
require `docker compose config`. Final verification runs all supported checks
from a clean working state and records exact counts and skips.
