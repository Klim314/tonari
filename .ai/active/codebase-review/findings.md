# Codebase Review Findings

## Usage

Record only evidence-backed findings here.

Suggested fields per finding:

- ID
- Severity
- Status
- Area
- Files
- Summary
- Risk
- Recommended action
- Test follow-up

## Status Values

- `open`
- `confirmed`
- `in progress`
- `resolved`
- `deferred`

## Findings

### F-001

- ID: `F-001`
- Severity: `P1`
- Status: `confirmed`
- Area: `backend / scrape lifecycle`
- Files:
  - `backend/services/scrape_manager.py`
  - `backend/app/routers/works.py`
  - `frontend/src/hooks/useScrapeStatus.ts`
  - `frontend/src/components/ScrapeModal.tsx`
- Summary: The async scrape job runner logs per-chapter scrape errors and still marks the job `completed`, while the request endpoint always returns a `pending` placeholder response with no error or partial-result information.
- Risk: A scrape can silently finish with missing chapters while the UI sees only `completed` and a progress bar. This hides content gaps from users, breaks retry decisions, and diverges from the richer synchronous `ChapterScrapeSummary` semantics already implemented in `ChaptersService`.
- Recommended action: Unify job execution with `ChaptersService` summary/error accounting, persist per-job errors, and emit terminal `partial` or `failed` states when any requested chapters fail. The request endpoint should either validate obvious failures up front or expose a durable job status payload that includes partial errors.
- Test follow-up: Add API and SSE tests that cover mixed-success ranges, unsupported decimal chapters, and scraper exceptions, asserting the final job status and surfaced error payloads.

### F-002

- ID: `F-002`
- Severity: `P1`
- Status: `confirmed`
- Area: `backend / translation streaming`
- Files:
  - `backend/app/routers/works.py`
  - `backend/services/translation_stream.py`
- Summary: Chapter translation streaming has no concurrency control. Each request loads the same pending segments and writes translated text back to shared rows without any lock, claim, or compare-and-swap guard.
- Risk: Multiple clients or reconnecting sessions can translate the same chapter at the same time, causing duplicated model cost and last-writer-wins overwrites on `TranslationSegment.tgt`. The router already carries a TODO acknowledging this gap.
- Recommended action: Add a translation-run claim or lock at the chapter-translation level before streaming begins, reject or attach observers to duplicate requests, and make reset/regenerate operations coordinate with in-flight runs instead of mutating shared rows underneath them.
- Test follow-up: Add concurrency tests that open two translation streams for the same chapter and assert that only one run performs translation work while the other is rejected or attached read-only.

### F-003

- ID: `F-003`
- Severity: `P1`
- Status: `confirmed`
- Area: `backend / prompt versioning and translation provenance`
- Files:
  - `backend/app/models.py`
  - `backend/app/routers/works.py`
  - `backend/services/prompt.py`
- Summary: `ChapterTranslation` has `prompt_version_id` plus snapshot columns for model/template/parameters, but the active translation path never populates them. Each stream request resolves the work's current latest prompt version at runtime, so a resumed or partially retranslated chapter can mix outputs from different prompt/model versions with no stored provenance.
- Risk: Translation artifacts become non-reproducible and non-auditable. A prompt edit between streaming runs can change later segments of the same chapter translation without any DB record of which version or model produced which output.
- Recommended action: Bind a translation to an immutable prompt/model snapshot when the run starts or when the translation row is first created. Persist `prompt_version_id`, `model_snapshot`, `template_snapshot`, and `parameters_snapshot`, and ensure resume/retranslate operations reuse that stored snapshot unless the user explicitly starts a new translation run.
- Test follow-up: Add tests that start a translation, change the work's prompt version, resume or retranslate a segment, and assert that the existing `ChapterTranslation` keeps using the original snapshot unless explicitly reset.

### F-004

- ID: `F-004`
- Severity: `P1`
- Status: `confirmed`
- Area: `frontend / build and chapter detail workflow`
- Files:
  - `frontend/src/components/chapterDetail/translation/TranslationPanel.tsx`
  - `frontend/src/hooks/useChapterTranslationStream.ts`
  - `frontend/src/clientConfig.ts`
  - `frontend/src/components/WorkCard.tsx`
  - `frontend/src/hooks/useChapter.ts`
  - `frontend/src/hooks/usePrompt.ts`
  - `frontend/src/hooks/usePromptVersions.ts`
  - `frontend/src/hooks/useWorkChapters.ts`
  - `frontend/src/hooks/useWorkPromptDetail.ts`
- Summary: The frontend does not currently typecheck or build. The chapter-detail translation UI imports a missing `RetranslateModal`, consumes `updateSegmentText` even though the hook interface omits it, and multiple hooks/config components no longer match the generated client’s nullability and prop typing requirements.
- Risk: The current tree cannot produce a releasable frontend artifact. That blocks CI from validating chapter-detail, prompt, and work-detail flows and hides additional regressions behind a broken baseline.
- Recommended action: Finish or revert the incomplete refactor as one coherent unit. Restore the missing translation modal or remove the dependency, align `TranslationStreamHook` with its implementation/consumers, then fix generated-client call sites and component props until `npm --prefix frontend run build` passes again.
- Test follow-up: Gate CI on the frontend build, then add focused coverage around chapter-detail translation editing/retranslation and the affected hooks once the type boundary is stable.

### F-005

- ID: `F-005`
- Severity: `P2`
- Status: `resolved`
- Area: `frontend / API contract handling`
- Files:
  - `frontend/src/clientConfig.ts`
  - `frontend/src/pages/WorkDetailPage.tsx`
  - `frontend/src/components/AddToGroupModal.tsx`
  - `frontend/src/components/CreateChapterGroupModal.tsx`
  - `frontend/src/components/ChapterGroupRow.tsx`
  - `frontend/src/components/ScrapeModal.tsx`
  - `frontend/src/components/chapterDetail/translation/ExplanationPanel.tsx`
  - `frontend/src/hooks/useScrapeStatus.ts`
  - `frontend/src/hooks/useChapterTranslationStream.ts`
- Summary: The frontend mixes generated-client calls that honor `VITE_API_BASE_URL` with adjacent raw `fetch` and `EventSource` calls hard-coded to `/api`. Core work-detail and chapter-detail mutations are split across both patterns.
- Risk: Environments that serve the backend at any non-default path or origin will fail only on selected actions such as chapter-group mutations, scrape cancel, or explanation regeneration, while other requests continue working. That makes deployment issues selective and difficult to diagnose.
- Recommended action: Centralize URL construction for all HTTP and SSE traffic, preferably through the generated client or a shared base-URL helper. Remove raw `/api` call sites unless there is a documented reason they must bypass the client.
- Test follow-up: Add a smoke test that runs the frontend with a non-default `VITE_API_BASE_URL` and exercises group management plus scrape/explanation actions.

### F-006

- ID: `F-006`
- Severity: `P1`
- Status: `resolved`
- Area: `data model / migrations`
- Files:
  - `backend/app/models.py`
  - `backend/alembic/versions/6727872b16b1_add_scrape_jobs.py`
  - `backend/app/db.py`
- Summary: The ORM defines a real `scrape_jobs` table, but the Alembic revision named `add_scrape_jobs` never creates it. Instead, application startup calls `Base.metadata.create_all()`, which can backfill missing tables outside migration history.
- Risk: A database created from Alembic alone is not guaranteed to contain `scrape_jobs`, even though the runtime depends on it. Environments that separate migrations from app startup can fail at runtime, and environments that do hit startup end up with schema state that Alembic does not describe.
- Recommended action: Add an explicit Alembic revision that creates `scrape_jobs` with the expected indexes and constraints, then remove `create_all()` from normal startup paths so migrations are the only schema authority.
- Test follow-up: Add a schema smoke test that provisions a fresh database via Alembic only and verifies required tables and constraints exist before the app starts.

### F-007

- ID: `F-007`
- Severity: `P1`
- Status: `confirmed`
- Area: `backend / prompt assignment lifecycle`
- Files:
  - `backend/app/models.py`
  - `backend/services/works.py`
  - `backend/services/prompt.py`
  - `backend/app/routers/prompts.py`
- Summary: Prompt deletion is soft (`deleted_at`), but work assignments are hard FKs in `work_prompts`, and `set_work_default_prompt()` accepts any existing prompt row without checking whether it is deleted. Reads later hide deleted prompts by filtering `Prompt.deleted_at IS NULL`.
- Risk: A work can retain or receive an assignment to a soft-deleted prompt. After that, read paths behave as if no prompt is assigned, and update endpoints can commit successfully and then fail their own follow-up read with `404`.
- Recommended action: Reject deleted prompts during assignment, and define explicit behavior for existing assignments when a prompt is soft-deleted, either by clearing `work_prompts` or by exposing deleted assignments intentionally.
- Test follow-up: Add coverage for deleting an assigned prompt and for attempting to assign a soft-deleted prompt to a work.

### F-008

- ID: `F-008`
- Severity: `P1`
- Status: `confirmed`
- Area: `data model / translation lifecycle`
- Files:
  - `backend/app/models.py`
  - `backend/services/translation_stream.py`
  - `backend/app/routers/chapter_translations.py`
  - `backend/app/routers/works.py`
- Summary: The schema allows multiple `chapter_translations` rows per chapter, but the current work-scoped translation flow assumes there is only one and always uses the first row returned for that chapter. The legacy `/chapter-translations/` route still creates a brand-new row on every call.
- Risk: Repeated calls can split segment state, explanations, and edits across multiple translation rows while the main chapter endpoints keep reading only the oldest one. Newer translations become effectively hidden and unreachable from the current UI/API flow.
- Recommended action: Either enforce one translation per chapter with a DB uniqueness constraint and migrate callers to upsert semantics, or make multiple translations a first-class concept and update every read/write path to address them explicitly.
- Test follow-up: Add a regression test that creates two translations for one chapter and asserts the intended selection behavior explicitly.

### F-009

- ID: `F-009`
- Severity: `P2`
- Status: `confirmed`
- Area: `data model / chapter groups`
- Files:
  - `backend/app/models.py`
  - `backend/alembic/versions/78bfe9799614_chapter_groups.py`
  - `backend/services/chapter_groups.py`
- Summary: `chapter_group_members` only enforces that each chapter belongs to at most one group and that member order is unique within a group. The database does not enforce that a chapter and its group belong to the same work.
- Risk: Service-layer validation currently prevents cross-work membership, but any future bug, script, or manual SQL can create impossible-looking rows that corrupt chapter-group listings and ordering assumptions.
- Recommended action: Encode same-work membership structurally, for example with a carried `work_id` plus composite foreign keys or a schema shape that makes cross-work membership impossible.
- Test follow-up: Add a migration or integrity test that proves cross-work memberships are rejected at the DB layer.

### F-010

- ID: `F-010`
- Severity: `P2`
- Status: `resolved`
- Area: `tests / contract coverage`
- Files:
  - `backend/tests/test_api.py`
  - `backend/tests/test_async_scraping.py`
  - `backend/tests/test_works_api.py`
  - `backend/app/routers/works.py`
  - `backend/app/routers/chapter_translations.py`
  - `backend/app/translation_service.py`
- Summary: The failing backend tests are mostly still asserting the older synchronous scrape contract and sentence-level translation slicing, while the current implementation uses async scrape jobs and newline-delimited segmentation.
- Risk: The suite is red for contract drift rather than the code’s intended behavior, so it no longer protects the actual scrape lifecycle or translation flow. Future regressions in the current design can slip through because the baseline is already broken.
- Recommended action: Decide which behavior is authoritative. If the async scrape/job model and newline segmentation are intentional, rewrite the affected tests around the current API and SSE semantics. If not, revert the implementation changes instead of patching the tests.
- Test follow-up: Add coverage for `pending` scrape job creation, `409` on active jobs, stale-job timeout handling, async scrape failure reporting, and newline-delimited translation segmentation.

### F-011

- ID: `F-011`
- Severity: `P2`
- Status: `resolved`
- Area: `tooling / lint signal`
- Files:
  - `justfile`
  - `backend/agents/base_agent.py`
  - `backend/agents/explanation_agent.py`
  - `backend/tests/routers/test_lab.py`
  - `backend/tests/test_async_scraping.py`
  - `backend/tests/test_chapter_groups.py`
  - `backend/tests/test_prompts_validation.py`
  - `frontend/src/pages/WorkDetailPage.tsx`
  - `frontend/src/components/PromptsLandingPane.tsx`
- Summary: `just lint` currently reports hundreds of Ruff diagnostics, and frontend lint is also failing on a mix of formatting drift and real issues. The lint baseline is noisy enough that it no longer provides a trustworthy regression signal.
- Risk: Once lint stays red by default, teams stop treating it as actionable. That weakens review discipline and makes it easier for real defects to hide among routine style failures.
- Recommended action: Re-establish a zero-failure lint baseline. Separate mechanical formatting cleanups from semantic fixes, land them independently, and only then enforce lint as a blocking gate.
- Test follow-up: After cleanup, enforce lint in CI and consider changed-files linting for faster feedback.

## Hotspot Summary

- `Backend scrape lifecycle`: async scrape orchestration has diverged from the shared chapter-scrape service, so failures, job state, migration history, and tests are no longer aligned.
- `Backend translation lifecycle`: translation streaming mutates shared state without concurrency control and does not persist prompt/model provenance, while legacy routes still create parallel translation rows.
- `Prompt assignment and snapshots`: prompt soft-delete semantics and translation snapshot semantics are incomplete, which makes prompt selection and historical translation behavior hard to trust.
- `Frontend chapter-detail and work-detail flows`: the current chapter-detail translation slice does not build, and adjacent work/chapter actions use inconsistent API base handling.
- `Schema and tooling governance`: Alembic is not the sole source of truth for schema evolution, backend tests drift from live contracts, and lint is too noisy to serve as a release gate.

## Remediation Backlog

- `Quick win`: restore a green frontend build by fixing the incomplete chapter-detail refactor and re-enabling `npm --prefix frontend run build` in CI.
- `Quick win`: realign backend tests with the intended async scrape and newline-segmentation contracts, or revert the implementation drift if those behaviors were not intended.
- `Quick win`: reject soft-deleted prompts in work assignment flows and add regression tests around delete/assign behavior.
- `Structural`: make Alembic the only schema authority by adding the missing `scrape_jobs` migration and removing runtime `create_all()` from normal startup.
- `Structural`: enforce a single authoritative translation lifecycle, including one explicit cardinality model for `chapter_translations`, persisted prompt/model snapshots, and concurrency control around streaming runs.
- `Structural`: consolidate scrape execution onto one service path so job state, partial failures, SSE updates, and API responses all reflect the same source of truth.
- `Structural`: centralize frontend API/SSE URL construction so environment configuration applies uniformly across generated-client and raw request flows.
