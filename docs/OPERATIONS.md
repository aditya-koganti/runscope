# Operations

## Local topology

Docker Compose runs web, API, scheduler, two workers, PostgreSQL, Redis,
Redpanda, and MinIO. Health checks and dependency-aware readiness prevent a
process being called ready before required services respond.

## Configuration

All runtime settings use environment variables documented in `.env.example`.
Startup validates required values. Production-style secrets are referenced, not
stored in source. Demo defaults are explicitly local-only.

## Service behavior

- API exposes process liveness at `/api/v1/health`, required-dependency
  readiness at `/api/v1/ready`, authenticated detailed dependency health at
  `/api/v1/platform/dependencies`, a durable control-plane summary at
  `/api/v1/platform/summary`, and Prometheus metrics at `/api/v1/metrics`.
- Scheduler and worker emit structured JSON logs and heartbeat health.
- Correlation IDs enter at HTTP or message boundaries and propagate through
  logs/events.
- Scheduler reconciliation recovers queued runs, expired leases, and stale
  workers.
- Workers use bounded retries for transient broker/storage operations and do not
  overwrite terminal run state.

## Recovery guidance

Restarting API is safe because client state is durable and SSE reconnects.
Restarting the scheduler is safe because allocation uses leases and locks.
Restarting a worker can leave a lease until expiry; reconciliation requeues safe
work according to its attempt state. Artifact upload failures fail a run with a
stable code rather than report false success.

## Foundation commands

Copy `.env.example` to an untracked `.env`, then use `make setup` and `make dev`.
Windows systems without GNU Make can run `python -m pip install -e ".[dev]"`,
`npm ci --prefix apps/web`, and `docker compose up --build` directly. API
liveness is `/api/v1/health`; readiness is `/api/v1/ready`.

Apply schema changes with `make migrate` and create the local-only viewer,
researcher, and administrator accounts with `make seed`. Seeding is idempotent;
it does not print passwords or tokens.

Workers use stable `RUNSCOPE_WORKER_NAME` values. CPU and memory declarations
are allocatable educational capacity, not operating-system isolation. The
default heartbeat is every three seconds; leases expire after 30 seconds and a
worker becomes stale after 15 seconds without a heartbeat.

Artifact-store retry count/base delay and the outbox attempt ceiling are
configured with `RUNSCOPE_STORAGE_MAX_ATTEMPTS`,
`RUNSCOPE_STORAGE_RETRY_BASE_SECONDS`, and `RUNSCOPE_OUTBOX_MAX_ATTEMPTS`.
Retries are finite. Exhausted unpublished messages remain durable and visible in
the platform summary for operator investigation.
