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
