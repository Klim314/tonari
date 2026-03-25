# Codebase Review — Current State

## Status

- State: `in progress`
- Started: 2026-03-25
- Last updated: 2026-03-25

## Findings Summary

| ID | Severity | Status | Area |
|----|----------|--------|------|
| F-001 | P1 | confirmed | backend / scrape lifecycle |
| F-002 | P1 | confirmed | backend / translation streaming |
| F-003 | P1 | confirmed | backend / prompt versioning |
| F-004 | P1 | confirmed | frontend / build and chapter detail |
| F-005 | P2 | resolved | frontend / API contract handling |
| F-006 | P1 | confirmed | data model / migrations |
| F-007 | P1 | confirmed | backend / prompt assignment lifecycle |
| F-008 | P1 | confirmed | data model / translation lifecycle |
| F-009 | P2 | confirmed | data model / chapter groups |
| F-010 | P2 | resolved | tests / contract coverage |
| F-011 | P2 | confirmed | tooling / lint signal |

## Current Focus

Major findings consolidated. Remediation of individual findings in progress.

## Next Steps

- Continue remediation of confirmed findings (prioritize P1s)
- Complete unchecked review lanes (see checklist.md)

## Open Review Lanes

- Backend translation and explanation deeper pass
- Backend chapter-group behavior deeper pass
- Service-layer boundaries and exception-handling sweep
- Cross-cutting logging/observability pass
- Cross-cutting security/validation pass
- Cross-cutting performance and duplication/dead-code pass
- Frontend prompt-editing flow pass

## Open Questions

- Should final review outputs remain under `.ai/active/` or be promoted into `docs/` once stabilized?
- Are the failing scrape tests stale after an intentional shift to async job-based scraping, or does the current API still violate intended product behavior?

## Blockers

- `just lint-web` is not reliable in this sandbox due to `snap-confine` permission requirements.
