# Implementation Plan

## Delivery status

Phases 0 through 8 are complete as of 2026-07-26. The current vertical slice
uses PostgreSQL-backed run records, a trusted versioned Iris classifier, the
central lifecycle state machine, durable logs/metrics/events, MinIO artifacts,
and a Playwright-verified browser workflow. Run submission uses a
transactional outbox, Redpanda, a separate idempotent worker, and REST polling
as the recovery path under authenticated Redis-backed SSE. A second bounded
template demonstrates honest progress, durable cancellation checkpoints,
controlled failure, retry lineage, metadata, and successful-run comparison.
Queued work is now assigned by a separate priority scheduler using worker
heartbeats, CPU/memory capacity, and expiring PostgreSQL leases.

## Phase 0 — Planning

Create permanent rules and initial product, architecture, model, API, event,
security, testing, operations, performance, limitation, and decision documents.
Gate: documentation review, secret scan, clean diff, focused commit.

## Phase 1 — Foundation

Scaffold the monorepo, FastAPI package, React/Vite app, shared contracts,
SQLAlchemy/Alembic, dependency configuration, JSON logging, correlation IDs,
health/readiness, Docker Compose, Make targets, and test/lint/type infrastructure.

## Phase 2 — Authentication

Add User persistence, hashing/JWT, local seed command, role dependencies,
sign-in UI, in-memory session, protected routes, and authorization tests.

## Phase 3 — Projects and experiments

Add constrained models/migrations, CRUD/search/filter/sort/page APIs and pages,
permission behavior, and one browser CRUD flow.

## Phase 4 — One synchronous real run

Implement the central state machine, template registry, Iris classification,
durable logs/metrics/artifacts using the storage interface, run create/detail
pages, and a successful synchronous end-to-end test.

## Phase 5 — Background worker and messaging

Add versioned contracts, Kafka broker interface/Redpanda adapter, outbox
publication, separate worker, MinIO store, dedupe, and integration tests.

## Phase 6 — Live updates

Add Redis fan-out, run SSE, cursor recovery, frontend reconnect/deduplication,
connection indicators, and REST fallback tests.

## Phase 7 — Cancellation, retry, and comparison

Add slow/failable trusted template, cancellation polling, retry lineage, notes,
tags, comparison API/pages/charts, lifecycle events, and coverage.

## Phase 8 — Scheduler and worker resources

Add worker registration/heartbeat, capacity-aware priority scheduling, leases,
expiry/stale recovery, multiple-worker support, and worker views.

## Phase 9 — Reliability and observability

Add Prometheus metrics, dependency summary, correlation propagation, structured
error mapping, retry policy, audit coverage, redaction, and failure tests.

## Phase 10 — CI/CD, Kubernetes, and performance

Add production images, GitHub Actions checks/scans, Kubernetes manifests with
probes/resources/secret references/migration job, Locust scenarios, and record
only benchmarks executed in the available environment.

## Phase 11 — Portfolio polish

Polish the engineering UI and README, add captured screenshots if available,
demo/verification scripts, remove dead code/placeholders, scan for secrets, and
verify from a clean-equivalent checkout.

## Risk order

The vertical slice precedes messaging because model execution, persistence, and
artifact semantics are the product core. Messaging precedes resource scheduling
because the scheduler must assign work a worker can already consume. Kubernetes
and load tests remain last because they should describe tested application
behavior rather than determine it.
