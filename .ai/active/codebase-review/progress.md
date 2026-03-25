# Codebase Review Progress

## Status

- State: `in progress`
- Started: `2026-03-25`
- Current focus: `session logged; major findings consolidated, deeper review lanes still open`
- Next step: `continue unchecked checklist lanes, starting with selected follow-up area`

## Log

### 2026-03-25

- Created persistent review workspace in `.ai/active/codebase-review/`.
- Defined review principles, phases, severity model, and deliverables.
- Established initial artifact split: plan, progress, findings, and checklist.
- Added `process.md` to define main-agent ownership, subagent coordination, scratch-note conventions, and consolidation rules.
- Confirmed the current dev environment is running via `docker compose ps` (`db`, `api-dev`, `frontend` all up).
- Ran `just test`: failed with 7/79 tests failing. Failures cluster in chapter translation segmentation (`backend/tests/test_api.py`) and scrape job / scrape endpoint behavior (`backend/tests/test_async_scraping.py`, `backend/tests/test_works_api.py`).
- Ran `just lint`: failed with 270 Ruff diagnostics. Errors are concentrated in `backend/agents/*`, selected service files, and multiple backend test modules.
- Ran `npm --prefix frontend run lint`: failed with 23 Biome diagnostics. Most are formatting drift in recently touched UI files plus explicit `any` usage in `frontend/src/pages/WorkDetailPage.tsx`.
- Ran `npm --prefix frontend run build`: failed with TypeScript errors in `frontend/src/clientConfig.ts`, `frontend/src/components/WorkCard.tsx`, `frontend/src/components/chapterDetail/translation/TranslationPanel.tsx`, and several data hooks (`useChapter`, `usePrompt`, `usePromptVersions`, `useWorkChapters`, `useWorkPromptDetail`, `useChapterTranslationStream`).
- Attempted `just lint-web`, but the local `just` wrapper hit a sandbox-specific `snap-confine` capability error before running the recipe. Used the underlying frontend command instead so baseline execution could proceed.
- Recorded that the repo worktree is already dirty across backend, frontend, and docs; review edits will stay confined to `.ai/active/codebase-review/`.
- Established the first hotspot map from baseline and entry-point inspection:
  - scrape lifecycle: `backend/app/routers/works.py`, `backend/services/scrape_manager.py`, `backend/services/chapters.py`
  - translation flow: `backend/app/routers/chapter_translations.py`, `backend/app/translation_service.py`, frontend translation panel/hooks
  - frontend detail flows: `frontend/src/pages/WorkDetailPage.tsx`, `frontend/src/pages/ChapterDetailPage.tsx`
- Spawned bounded review lanes after baseline/system map:
  - frontend workflows and build health
  - data model and migrations
  - tests and tooling
- Consolidated the first confirmed findings into `findings.md`:
  - async scrape jobs can report `completed` while silently dropping chapter-level failures
  - translation streaming lacks concurrency control and can duplicate work / overwrite shared segments
  - translation runs do not persist prompt/model snapshots even though the schema reserves snapshot columns
  - frontend currently fails to typecheck/build
  - frontend API base handling is inconsistent across adjacent flows
  - migration history does not create `scrape_jobs`, with `create_all()` masking the drift at startup
  - soft-deleted prompts can remain assigned or be reassigned
  - multiple `chapter_translations` per chapter are allowed even though the main flow assumes one
  - chapter-group same-work integrity is only enforced in services, not in the schema
- Updated checklist progress for reviewed backend, frontend, data-model, and test lanes.
- Added a hotspot summary and remediation backlog to `findings.md`, and marked the output deliverables complete in `checklist.md`.
- Reviewed `F-005` with the user and confirmed the core issue definition: frontend networking is inconsistent because some flows use environment-aware base URL handling while others hard-code `/api`.
- Clarified session status with the user: this review pass covered the highest-risk lanes and produced actionable findings, but it did not fully complete every planned checklist item.
- Recorded the major work completed in this session:
  - read and used the persistent review workspace under `.ai/active/codebase-review/`
  - ran baseline commands and captured exact failures/blockers
  - mapped repo entry points and hotspot flows
  - spawned bounded subagent lanes for frontend, data-model/migrations, and tests/tooling
  - consolidated canonical findings `F-001` through `F-011`
  - updated `checklist.md` to reflect completed and still-open review lanes
  - added hotspot summary and remediation backlog to `findings.md`
- Recorded the still-open review lanes so the next session starts from a truthful state:
  - backend translation and explanation deeper pass
  - backend chapter-group behavior deeper pass
  - service-layer boundaries and exception-handling sweep
  - cross-cutting logging/observability pass
  - cross-cutting security/validation pass
  - cross-cutting performance and duplication/dead-code pass
  - frontend prompt-editing flow pass

## Open Questions

- Should final review outputs remain under `.ai/active/` or be promoted into `docs/` once stabilized?
- Should findings be grouped primarily by severity or by subsystem in the final write-up?
- Are the failing scrape tests stale after an intentional shift from synchronous scrape summaries to async job-based scraping, or does the current API still violate intended product behavior?

## Blockers

- `just lint-web` is not reliable in this sandbox because the local `just` wrapper hits `snap-confine` permission requirements before executing the recipe.
