# Codebase Review Checklist

## Baseline

- [x] Run backend tests
- [x] Run backend lint
- [x] Run frontend lint
- [x] Run frontend build
- [x] Record baseline failures and blockers

## Backend

- [x] Review app entry points and router structure
- [ ] Review ingest and scraping flows
- [x] Review scrape job lifecycle
- [ ] Review translation and explanation flows
- [x] Review prompt and prompt version handling
- [ ] Review chapter group behavior
- [ ] Review service-layer boundaries and exception handling

## Data Model

- [x] Review SQLAlchemy models
- [x] Review DB constraints and cascade behavior
- [x] Review Alembic migration history
- [x] Check model-to-migration alignment

## Frontend

- [x] Review route and navigation patterns
- [x] Review work detail flow
- [x] Review chapter detail flow
- [ ] Review prompt editing flow
- [x] Review API client usage patterns
- [x] Review loading, empty, and error states

## Cross-Cutting

- [x] Review configuration and env handling
- [ ] Review logging and observability
- [ ] Review security and validation concerns
- [ ] Review performance hotspots
- [ ] Review duplication and dead code
- [x] Review typing and contract drift

## Tests

- [x] Review backend test coverage by risk area
- [x] Review frontend automated coverage
- [x] Identify missing regression tests

## Outputs

- [x] Produce prioritized findings list
- [x] Produce hotspot summary by subsystem
- [x] Produce remediation backlog
