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
