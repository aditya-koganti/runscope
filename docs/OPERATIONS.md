# Operations

## Local topology

Docker Compose will run web, API, scheduler, worker, PostgreSQL, Redis, Redpanda,
and MinIO. Health checks and dependency-aware readiness prevent a process being
called ready before required services respond.

## Configuration

All runtime settings use environment variables documented in `.env.example`.
Startup validates required values. Production-style secrets are referenced, not
stored in source. Demo defaults are explicitly local-only.

## Service behavior

- API exposes liveness, readiness, dependency health, and Prometheus metrics.
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

Exact commands and troubleshooting steps will be added as services are built and
verified.

