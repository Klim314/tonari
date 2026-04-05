# Codebase Review — Session Log

Append-only. Each session adds an entry. Only consult when you need to understand past decisions.

## 2026-03-25 — Initial review

- Created persistent review workspace in `.ai/active/codebase-review/`.
- Defined review principles, phases, severity model, and deliverables.
- Established initial artifact split: plan, progress, findings, and checklist.
- Added `process.md` to define main-agent ownership, subagent coordination, scratch-note conventions, and consolidation rules.
- Confirmed the current dev environment is running via `docker compose ps` (`db`, `api-dev`, `frontend` all up).
- Ran `just test`: failed with 7/79 tests failing. Failures cluster in chapter translation segmentation (`backend/tests/test_api.py`) and scrape job / scrape endpoint behavior (`backend/tests/test_async_scraping.py`, `backend/tests/test_works_api.py`).
- Ran `just lint`: failed with 270 Ruff diagnostics. Errors are concentrated in `backend/agents/*`, selected service files, and multiple backend test modules.
- Ran `npm --prefix frontend run lint`: failed with 23 Biome diagnostics. Most are formatting drift in recently touched UI files plus explicit `any` usage in `frontend/src/pages/WorkDetailPage.tsx`.
- Ran `npm --prefix frontend run build`: failed with TypeScript errors in `frontend/src/clientConfig.ts`, `frontend/src/components/WorkCard.tsx`, `frontend/src/components/chapterDetail/translation/TranslationPanel.tsx`, and several data hooks.
- Established hotspot map from baseline and entry-point inspection.
- Spawned bounded review lanes: frontend workflows/build health, data model/migrations, tests/tooling.
- Consolidated confirmed findings `F-001` through `F-011` into `findings.md`.
- Added hotspot summary and remediation backlog to `findings.md`.

## 2026-03-25 — F-005 remediation

- Resolved `F-005`: centralized frontend API URL construction.
  - Added `apiUrl()` helper in `frontend/src/clientConfig.ts` backed by the single `VITE_API_BASE_URL` constant.
  - Replaced all 8 hardcoded `/api` fetch/EventSource call sites across 7 files to use `apiUrl()`.
  - Consolidated duplicate base-URL logic in `useScrapeStatus.ts` and `useChapterTranslationStream.ts`.
  - Verified no remaining hardcoded `/api` fetch/EventSource patterns in `frontend/src/`.
  - Build output unchanged — no new errors introduced (pre-existing F-004 errors remain).

## 2026-03-25 — F-010 remediation

- Resolved `F-010`: realigned backend tests with the current async scrape-job and newline-segmentation contracts.
- Updated `backend/tests/test_api.py` to assert newline-delimited translation segments, including explicit whitespace-segment handling.
- Replaced stale `ChaptersService` scrape-job assertions in `backend/tests/test_async_scraping.py` with `ScrapeManager` coverage for job creation, active-job lookup, stale-job timeout handling, async progress updates, `409` concurrency rejection, and async failure on missing source data.
- Updated `backend/tests/test_works_api.py` to assert `pending` scrape-job creation responses and added scrape-status SSE coverage for idle state, active-job bootstrap state, and forwarded broadcast events.
- Ran `docker compose exec api-dev pytest tests/test_api.py tests/test_async_scraping.py tests/test_works_api.py`: `22 passed`.

## 2026-03-26 — F-011 remediation (backend ruff)

- Resolved `F-011` (backend): cleared all 34 ruff diagnostics to reach a zero-error baseline.
- Fixed 25 E501 (line length) by rewrapping long comments and splitting string literals.
- Fixed 4 F841 (unused variables) across services and tests — removed or prefixed with `_`.
- Fixed 2 B007 (unused loop variables) in routers and scripts — prefixed with `_`.
- Fixed 2 B904 (raise from) in `ingest.py` and `schemas.py`.
- Fixed 1 UP007 (union syntax) in `base_agent.py` — `Union[X, Y]` → `X | Y`.
- Fixed 1 N806 (naming) in `test_lab.py` — `MockAgent` → `mock_agent_cls`.
- Ran `docker compose exec api-dev ruff check .`: `All checks passed!`
- Frontend lint (`just lint-web`) not yet addressed.

## 2026-04-05 — F-004 remediation

- Resolved `F-004`: frontend type-boundary regressions blocking typecheck/build were fixed.
- Updated `frontend/src/clientConfig.ts` to guard optional generated-client config fields.
- Aligned `TranslationStreamHook` with its implementation by adding `updateSegmentText`.
- Fixed `WorkCard` typing by splitting anchor vs non-anchor rendering and keeping the select handler safe at the call sites.
- Updated affected fetch hooks to use narrowed local ids after null guards so generated-client path params stay typed as `number`.
- Corrected `ScrapeModal` log updates to use the component's structured log shape.
- Ran `npm --prefix frontend run typecheck`: passed.

## 2026-04-05 — A-003 remediation planning

- Created `.ai/active/codebase-review/tasks/` for execution-oriented remediation plans tied to review findings.
- Added `tasks/a-003-react-query-migration.md` to capture the TanStack Query migration plan for architecture finding `A-003`.
- Kept the task plan separate from `plan.md` so review strategy and remediation execution remain distinct artifacts.
