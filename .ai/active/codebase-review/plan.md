# Codebase Review Plan

## Purpose

This review tracks the health of the Tonari codebase across backend, frontend, data model, tooling, and tests.

The goal is to:

- identify correctness, data integrity, and operational risks
- document maintainability and design debt
- record testing gaps
- produce a prioritized remediation backlog

## Review Principles

1. Review by risk, not by directory.
2. Start from executable truth: tests, lint, build, and runtime behavior.
3. Trace critical flows end to end across API, service, model, and UI.
4. Separate findings by severity and type.
5. Record only evidence-backed findings with concrete file references.
6. End with actionable remediation, not just observations.

## Severity Model

- `P0`: data loss, corruption, security issue, runaway cost, or broken core workflow
- `P1`: likely bug or major regression risk
- `P2`: maintainability or design issue with near-term cost
- `P3`: cleanup, consistency, or low-risk debt

## Review Phases

### Phase 0: Baseline

- run backend tests
- run backend lint
- run frontend lint
- run frontend build
- record current failures, warnings, and blockers

### Phase 1: System Map

- map primary domains and entry points
- identify critical user and data flows
- define subsystem review order

### Phase 2: Backend Critical Paths

- ingest and scraping
- scrape job lifecycle
- chapter storage and ordering
- translation and explanation flows
- prompt and prompt version management
- chapter grouping and mutation flows

Focus areas:

- transaction boundaries
- idempotency
- partial-failure behavior
- race conditions
- API/schema/model alignment
- DB constraint coverage

### Phase 3: Data Model and Migrations

- SQLAlchemy model design
- Alembic migration history
- uniqueness and cascade assumptions
- nullable/status field correctness
- snapshot and audit fields

### Phase 4: Frontend Behavior

- navigation and route handling
- data fetching patterns
- generated client vs raw fetch usage
- loading, empty, and error states
- state synchronization and refresh logic
- UX regressions in core workflows

### Phase 5: Cross-Cutting Concerns

- configuration and environment handling
- logging and observability
- security and input validation
- performance hotspots
- duplication and dead code
- type safety and contract drift

### Phase 6: Test Assessment

- backend test coverage against risk areas
- frontend coverage and manual test burden
- missing regression tests for critical workflows

### Phase 7: Remediation Output

- produce prioritized findings list
- summarize hotspots by subsystem
- identify quick wins vs structural work
- convert major findings into follow-up tasks

## Initial Review Order

1. Baseline commands and current health
2. Backend translation flow
3. Backend prompts and snapshots
4. Backend chapter groups and ordering
5. Data model and migrations
6. Frontend work detail and chapter detail flows
7. Frontend prompt and translation UI
8. Cross-cutting concerns
9. Test gaps and remediation plan

## Deliverables

- `progress.md`: dated execution log
- `findings.md`: review findings and status
- `checklist.md`: subsystem review checklist

