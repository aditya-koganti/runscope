# Architecture Decisions

## ADR-001: PostgreSQL is the durable source of truth

**Status:** Accepted.

Messages are at-least-once notifications. Services confirm current database
state and use transactions before side effects. This avoids treating broker
retention or process memory as the run ledger.

## ADR-002: UUID identifiers and UTC timestamps

**Status:** Accepted.

UUIDs avoid coordination between independently running services. All persisted
timestamps are timezone-aware UTC; localization is a presentation concern.

## ADR-003: Durable outbox and consumer deduplication

**Status:** Accepted.

`OutboxMessage` closes the database-to-broker publication gap, while
`ProcessedMessage` makes at-least-once delivery safe. These two infrastructure
tables are documented additions to the requested domain model.

## ADR-004: Static trusted template registry

**Status:** Accepted.

Database template rows expose metadata and schemas, but executable functions are
resolved only from code registered at build time. A database edit cannot inject
code. The key and version pair identifies the executable contract.

## ADR-005: REST recovery under SSE

**Status:** Accepted.

Redis/SSE provides responsiveness, not exclusive delivery. Event IDs,
`Last-Event-ID`, and cursor reads recover gaps, and all screens remain useful
with ordinary REST refreshes.

## ADR-006: CSS modules and TanStack Query without Redux initially

**Status:** Accepted.

Server state belongs in TanStack Query. Authentication and live-connection state
are small enough for React context. Redux Toolkit will be introduced only if a
genuine cross-feature client-state need emerges.

## ADR-007: Docker Compose is the reference local environment

**Status:** Accepted.

Compose provides reproducible PostgreSQL, Redis, Redpanda, and MinIO services.
Kubernetes artifacts are educational deployment examples added after local
behavior works; they are not a claim of production readiness.

## ADR-008: Frontend browser tests are co-located with the web package

**Status:** Accepted.

Executable Playwright specs live in `apps/web/e2e` rather than root `tests/e2e`
so Node resolves the web package's locked `@playwright/test` dependency without
a second root dependency installation. Cross-service Python integration tests
remain under root `tests/integration`.

## ADR-009: Synchronous execution is a disposable vertical-slice adapter

**Status:** Accepted.

Phase 4 executes a trusted template inside the API request after persisting the
run as `RUNNING`. This proves validation, lifecycle, persistence, and artifacts
without hiding them behind messaging. The execution service is isolated so
Phase 5 can move the same trusted registry into a separate worker. Synchronous
execution is not presented as the final operational architecture.

## ADR-010: API-hosted outbox dispatcher with worker-side deduplication

**Status:** Accepted for the local educational topology.

Submission stores the versioned envelope and `QUEUED` transition atomically.
The API lifespan dispatcher publishes unpublished rows to Redpanda with bounded
backoff. Workers commit Kafka offsets only after handling an event and record
the `(event_id, consumer_name)` pair. A crash after work but before the
deduplication write is still safe because the worker re-reads terminal run
state. A dedicated outbox deployment would be preferable at larger scale.

## ADR-011: Redis/SSE is best-effort over durable REST state

**Status:** Accepted.

Worker live publishes are deliberately outside the durable transaction and
cannot fail a run. The browser consumes SSE with an Authorization header through
streaming `fetch`, deduplicates event IDs, reconnects after disconnect, and
keeps low-frequency REST polling. Heartbeats keep intermediaries from silently
closing idle streams. Redis loss reduces responsiveness but not correctness.

## ADR-012: Cancellation is cooperative and retries create child runs

**Status:** Accepted.

The API records `RUNNING -> CANCELLING`; the trusted slow template re-reads that
durable status at bounded checkpoints before recording `CANCELLED`. It does not
kill a process mid-write. A retry copies and revalidates the failed run's
parameters into a new queued child, increments `attempt_number`, and preserves
the failed parent as immutable history. The demonstration retry UI changes only
the explicit `fail_intentionally` parameter; arbitrary code remains impossible.

## ADR-013: Targeted assignments use one consumer group per worker identity

**Status:** Accepted for the local educational topology.

The scheduler polls and locks durable queued runs, reserves CPU/memory through
an expiring allocation, and publishes `run.assigned`. Each configured worker
name maps to a stable database UUID and therefore a stable Kafka consumer
group. Every worker sees assignments but only the target accepts one; this
avoids an untargeted shared group handing a lease to the wrong process. It is
simple and correct for a small pool, but a production fleet would use partition
routing or a dedicated dispatch protocol to avoid broadcast overhead.

## ADR-014: Heartbeats extend leases and reconciliation owns recovery

**Status:** Accepted.

Worker heartbeats recompute capacity from active database allocations and
extend their lease expiries. Scheduler reconciliation marks stale workers,
requeues work that never started, fails running work whose worker vanished, and
releases capacity transactionally. Completed, failed, and cancelled execution
paths also release their allocations before committing final state.

## ADR-015: Health signals are bounded views over durable state

**Status:** Accepted.

Liveness proves only that the API process responds. Readiness runs concurrent,
two-second probes for PostgreSQL, Redis, Redpanda, and MinIO and returns 503 when
a required dependency is unavailable. Scheduler heartbeat is reported in the
authenticated dependency view but does not make the API itself unready.
Prometheus labels use route templates rather than user-controlled paths, while
run, queue, worker, and outbox gauges are refreshed from PostgreSQL on scrape.

## ADR-016: Retry infrastructure boundaries, not domain commands

**Status:** Accepted.

S3-compatible artifact operations use a configurable finite exponential retry
wrapper and end in a stable `ArtifactStorageError`. The outbox records bounded
publish attempts and the exception type, without persisting credentials or
exception messages. Domain commands are not blindly replayed; durable state,
optimistic concurrency, and consumer deduplication remain their safety
mechanisms.
