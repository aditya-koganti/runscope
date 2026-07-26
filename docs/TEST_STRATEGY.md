# Test Strategy

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

