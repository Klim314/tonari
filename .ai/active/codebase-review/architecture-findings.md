# Architecture Findings

## Purpose

This document captures architecture-level findings from the Tonari codebase review.

Unlike `findings.md`, which focuses on correctness and operational defects, this file
focuses on structural issues, why they exist, and how to approach them incrementally.

Each finding includes:

- ID
- Priority
- Status
- Area
- Files
- Root cause
- Explanation
- Proposed solution
- Suggested approach

## Status Values

- `open`
- `planned`
- `in progress`
- `deferred`
- `done`

## Priority Model

- `Now`: high leverage, blocks future cleanup, or reduces active delivery friction
- `Next`: important structural improvement, but can wait until the first layer of cleanup lands
- `Later`: worthwhile, but should follow the earlier seams to avoid churn

## Findings

### A-001

- ID: `A-001`
- Priority: `Now`
- Status: `done`
- Area: `backend / translation workflow boundary`
- Files:
  - `backend/app/routers/works.py`
  - `backend/services/translation_stream.py`
  - `backend/services/explanation_stream.py`
  - `backend/services/prompt.py`
  - `backend/agents/translation_agent.py`
  - `backend/agents/explanation_agent.py`
- Root cause: The codebase evolved from direct router-driven orchestration toward a service-based design, but the streaming translation and explanation flows were only partially extracted.
- Explanation: Most CRUD-like flows already use focused services. The main remaining concentration point is the streaming path in `backend/app/routers/works.py`, especially the translation loop, status transitions, prompt override resolution, agent construction, and SSE event contract. The existing services handle segment lifecycle and prompt lookup, but they do not own the full workflow. This makes the translation path harder to test in isolation and harder to evolve when concurrency, retries, or alternate execution backends are introduced.
- Proposed solution: Introduce an application-level orchestration layer for translation and explanation flows.
- Suggested approach:
  1. Add a `TranslationWorkflow` service that owns:
     - translation start/resume decisions
     - prompt snapshot resolution
     - agent construction
     - per-segment execution loop
     - translation status transitions
  2. Add an `ExplanationWorkflow` service that owns:
     - segment eligibility checks
     - context assembly
     - explanation generation and caching policy
  3. Keep `TranslationStreamService` and `ExplanationStreamService` as lower-level state helpers.
  4. Reduce the router to HTTP validation, dependency wiring, and SSE adaptation.

### A-002

- ID: `A-002`
- Priority: `Now`
- Status: `done`
- Area: `backend / translation architecture consistency`
- Files:
  - `backend/app/routers/works.py`
  - `backend/app/routers/chapter_translations.py`
  - `backend/app/translation_service.py`
  - `backend/services/translation_stream.py`
- Root cause: The codebase still contains both a newer streaming translation model and an older synchronous translation prototype.
- Explanation: The work-scoped endpoints in `backend/app/routers/works.py` represent the current product direction, while `backend/app/routers/chapter_translations.py` still exposes a separate synchronous creation flow built on `segment_and_translate()`. That leaves two translation architectures in the repository, with different lifecycle assumptions and different ownership boundaries. Even if only one is actively used by the UI, the duplicate model increases maintenance cost and creates ambiguity about the canonical flow.
- Proposed solution: Choose one authoritative translation architecture and retire or clearly isolate the other.
- Suggested approach:
  1. Declare the work-scoped streaming flow authoritative.
  2. Deprecate the legacy `chapter_translations` route family or move it under an explicit `legacy` namespace.
  3. Remove dead synchronous-path helpers once tests and callers are migrated.
  4. Ensure all future translation features target one lifecycle only.

### A-003

- ID: `A-003`
- Priority: `Now`
- Status: `done`
- Area: `frontend / server-state architecture`
- Files:
  - `frontend/src/client/`
  - `frontend/src/clientConfig.ts`
  - `frontend/src/components/PromptEditor/PromptEditor.tsx`
  - `frontend/src/hooks/usePrompt.ts`
  - `frontend/src/hooks/useWorks.ts`
  - `frontend/src/hooks/useWork.ts`
  - `frontend/src/hooks/useWorkChapters.ts`
  - `frontend/src/hooks/usePrompts.ts`
  - `frontend/src/hooks/usePromptVersions.ts`
  - `frontend/src/hooks/useWorkPromptDetail.ts`
- Root cause: The frontend adopted generated API bindings, but stopped short of adopting a shared query/cache layer.
- Explanation: The current hooks repeat the same `useEffect` + `loading/error/data` pattern with ad hoc refresh tokens and local invalidation rules. The prompt editor is the clearest example: it increments a local refresh token after save so both prompt detail and prompt versions refetch, and each hook manages its own abort, loading, and error behavior. The generated client is already the right low-level contract boundary, but without a server-state layer the app keeps rebuilding the same fetching logic and cannot express cache invalidation cleanly. This is the highest-leverage frontend architecture fix because it removes repeated boilerplate, replaces manual refresh-token plumbing with query invalidation, and makes later route, mutation, and state refactors much easier.
- Proposed solution: Standardize frontend data access on generated bindings plus TanStack Query.
- Suggested approach:
  1. Add TanStack Query at the app root.
  2. Introduce domain query modules:
     - `queries/works.ts`
     - `queries/prompts.ts`
     - `queries/chapters.ts`
     - `queries/translations.ts`
  3. Replace the current fetch hooks incrementally with `useQuery`/`useMutation` wrappers over the generated SDK.
  4. Centralize invalidation after mutations such as:
     - work import
     - prompt create/update/delete
     - prompt assignment
     - group creation/deletion
     - translation reset/regenerate
  5. Keep streaming hooks custom for now, but have them invalidate TanStack queries when runs complete.

### A-004

- ID: `A-004`
- Priority: `Next`
- Status: `planned`
- Area: `frontend / routing and page boundaries`
- Files:
  - `frontend/src/App.tsx`
  - `frontend/src/hooks/useBrowserLocation.ts`
  - `frontend/src/pages/LandingPage.tsx`
  - `frontend/src/pages/WorkDetailPage.tsx`
  - `frontend/src/pages/ChapterDetailPage.tsx`
  - `frontend/src/pages/LabPage.tsx`
- Root cause: The app started small enough that custom history handling was cheaper than adopting a routing framework.
- Explanation: Route parsing in `frontend/src/App.tsx` is currently handwritten, and navigation is managed through `useBrowserLocation`. This works for a small app, but it makes nested layouts, route loaders, search params, and future route expansion more manual than necessary. The repo already depends on `react-router-dom`, so the architecture is carrying a custom solution without a strong reason to keep it.
- Proposed solution: Migrate to route objects and nested layouts with `react-router-dom`.
- Suggested approach:
  1. Introduce route definitions for:
     - landing
     - prompts
     - prompt lab
     - work detail
     - chapter detail
  2. Replace regex parsing with route params.
  3. Add shared layouts where appropriate.
  4. Migrate navigation callbacks to router navigation helpers.
  5. Do this after TanStack Query is in place so route migration does not also carry data-fetch rewrites.

### A-005

- ID: `A-005`
- Priority: `Next`
- Status: `planned`
- Area: `frontend / transport boundary consistency`
- Files:
  - `frontend/src/clientConfig.ts`
  - `frontend/src/hooks/useChapterTranslationStream.ts`
  - `frontend/src/hooks/useScrapeStatus.ts`
  - `frontend/src/pages/LabPage.tsx`
  - `frontend/src/pages/WorkDetailPage.tsx`
- Root cause: Non-streaming API access and streaming access were implemented along different paths without a shared transport abstraction.
- Explanation: The codebase already improved base-URL handling, but there is still a split between generated SDK calls and custom `fetch`/`EventSource` logic. That split is justified for streaming, but the app lacks a formal transport boundary for those cases. Without one, error mapping, retries, auth headers, and stream lifecycle conventions can diverge by feature.
- Proposed solution: Keep the generated SDK for regular requests and add a small shared transport layer for stream-capable endpoints.
- Suggested approach:
  1. Add a `lib/transport` or `lib/streams` module for:
     - SSE URL construction
     - common event parsing
     - stream teardown conventions
     - shared error mapping
  2. Move `EventSource` setup out of page-level code and into reusable helpers.
  3. Keep `fetch`-stream use in the prompt lab behind the same abstraction family.

### A-006

- ID: `A-006`
- Priority: `Next`
- Status: `planned`
- Area: `backend / model and provider resolution`
- Files:
  - `backend/app/config.py`
  - `backend/constants/llm.py`
  - `backend/app/routers/works.py`
  - `backend/app/routers/lab.py`
  - `backend/agents/translation_agent.py`
- Root cause: Provider support was added incrementally, leaving model selection, API key selection, and agent construction spread across multiple layers.
- Explanation: The app already has a provider-aware model registry and provider-specific API key settings, but the resolution path is not fully centralized. The lab flow resolves provider/model explicitly, while the work translation router still injects `translation_api_key` directly. That split makes it easier for different code paths to drift in behavior.
- Proposed solution: Add a single backend resolver for model/provider/client configuration.
- Suggested approach:
  1. Create a `ModelResolutionService` or `LLMRuntimeResolver`.
  2. Make it responsible for:
     - resolving the model id
     - looking up provider metadata
     - selecting the correct API key
     - selecting base URL overrides
     - constructing agent dependencies
  3. Use it in both chapter translation and prompt lab paths.

### A-007

- ID: `A-007`
- Priority: `Next`
- Status: `planned`
- Area: `backend / process-local background execution`
- Files:
  - `backend/services/scrape_manager.py`
  - `backend/app/routers/works.py`
  - `docs/translation-agent.md`
- Root cause: Long-running work was implemented inside the API process for speed of iteration.
- Explanation: Scrape jobs and stream subscriptions currently depend on in-process memory and API-process lifetime. That is acceptable for local development and early-stage product work, but it does not provide durable job execution or cross-process coordination. This is a real architecture limit, but it is not the first thing to address unless product usage or deployment topology requires it.
- Proposed solution: Move long-running execution and event coordination onto more durable boundaries when operational needs justify it.
- Suggested approach:
  1. First, extract workflows cleanly so execution backend becomes swappable.
  2. Then introduce:
     - a worker queue for scrape and translation jobs
     - durable job state
     - durable event replay or polling fallback
  3. Avoid doing this before `A-001`, because otherwise the queue refactor will cement router-owned workflow logic.

### A-008

- ID: `A-008`
- Priority: `Next`
- Status: `planned`
- Area: `frontend / page orchestration complexity`
- Files:
  - `frontend/src/pages/WorkDetailPage.tsx`
  - `frontend/src/components/chapterDetail/translation/TranslationPanel.tsx`
  - `frontend/src/hooks/usePromptOverride.ts`
  - `frontend/src/components/PromptsLandingPane.tsx`
- Root cause: As features accumulated, pages became the easiest place to combine view state, mutation state, and transport behavior.
- Explanation: Several pages and top-level components now act as both presentation layer and state machine. `WorkDetailPage` coordinates pagination, selection, grouping, deletion, scrape refresh, and navigation. `TranslationPanel` mixes stream lifecycle, editing, modal orchestration, and mutation calls. This is manageable today, but it becomes harder to test and harder to reason about once the app adds richer interactions.
- Proposed solution: Move workflow-heavy UI logic into dedicated controller hooks or domain modules.
- Suggested approach:
  1. After TanStack Query lands, create focused controller hooks:
     - `useWorkDetailController`
     - `useTranslationPanelController`
     - `usePromptEditorController`
  2. Keep components primarily responsible for rendering and event wiring.
  3. Treat this as a follow-on cleanup, not the first migration.

### A-009

- ID: `A-009`
- Priority: `Next`
- Status: `planned`
- Area: `backend / bounded context organization`
- Files:
  - `backend/app/models.py`
  - `backend/app/schemas.py`
  - `backend/app/routers/`
  - `backend/services/`
- Root cause: The domain surface expanded faster than the original flat-file layout.
- Explanation: The repository now has enough domain surface that single-file `models.py` and `schemas.py` are starting to carry too many concepts at once. The `models.py` side is a notably cheap win because it can be split mechanically while preserving the existing import surface. That gives immediate benefits in navigation, edit locality, and LLM context efficiency. The `schemas.py` side is broader and should still wait until the main workflow seams are cleaner.
- Proposed solution: Split `models.py` early as a mechanical refactor, then handle broader bounded-context reorganization later.
- Suggested approach:
  1. First, split `backend/app/models.py` into a package while preserving current imports via `backend/app/models/__init__.py`.
  2. Start with domain files such as:
     - `catalog`
     - `translation`
     - `prompts`
     - `scraping`
     - `grouping`
  3. Do not change model behavior, relationships, or naming in the same refactor.
  4. After the main workflow seams are stabilized, consider a broader bounded-context reorganization for schemas, services, and routers.

### A-010

- ID: `A-010`
- Priority: `Later`
- Status: `planned`
- Area: `frontend / design system maturity`
- Files:
  - `frontend/src/main.tsx`
  - `frontend/src/index.css`
  - `frontend/src/components/`
- Root cause: Chakra was adopted as a component toolkit, but the app never formalized product-specific tokens, theme rules, or layout primitives.
- Explanation: The current UI works, but it is still effectively assembled from default Chakra primitives. That is acceptable early on, but a growing product benefits from semantic tokens, shared typography, consistent spacing, and page-level layout primitives. This is real architecture work, but it should follow the data and routing cleanup so you do not restyle moving targets.
- Proposed solution: Introduce a custom Chakra theme and a small set of app-level primitives.
- Suggested approach:
  1. Add semantic color tokens and typography primitives.
  2. Create reusable page-shell and panel patterns.
  3. Standardize spacing and status color usage.

## Recommended Implementation Order

### Phase 1: Handle First

These changes unlock later work and reduce the most day-to-day friction.

1. `A-003` Frontend server-state architecture
   - Highest leverage frontend improvement.
   - Pairs well with your preference for generated bindings + TanStack Query.
   - Reduces boilerplate before other frontend refactors.

2. `A-001` Backend translation workflow boundary
   - Highest leverage backend architecture improvement.
   - Makes future concurrency, job execution, and testing work cleaner.

3. `A-002` Backend translation architecture consistency
   - Remove or isolate the legacy synchronous path once the authoritative workflow is clear.
   - Prevents ongoing split-brain maintenance.

4. `A-006` Backend model/provider resolution
   - Small-to-medium effort with good payoff.
   - Reduces drift across translation paths.

5. `A-009` Split `models.py` into a package while preserving import compatibility
   - Cheap structural win.
   - Improves navigation and lowers LLM context bloat.
   - Should stay mechanical and behavior-preserving.

### Phase 2: Handle Next

These are strong follow-ons after the first seams are in place.

6. `A-004` Frontend routing and page boundaries
7. `A-005` Frontend transport boundary consistency
8. `A-008` Frontend page orchestration complexity
9. `A-007` Backend process-local background execution

### Phase 3: Handle Later

These are worthwhile once the runtime and workflow seams are stabilized.

10. `A-010` Frontend design system maturity

## Practical Recommendation

If the team wants the best sequence with the least churn:

1. Standardize frontend data access around generated bindings + TanStack Query.
2. Extract backend translation workflow ownership out of the router.
3. Retire the legacy translation path so there is one canonical model.
4. Unify model/provider resolution across all LLM-backed flows.
5. Split `backend/app/models.py` into a package as a mechanical compatibility-preserving refactor.
6. Migrate routing and then clean up page/controller boundaries.
7. Only after those seams are stable, decide whether durable workers/events are worth the operational cost.

This order keeps the early work close to current delivery pain, avoids premature large-scale renames, and creates clean seams before any heavier infrastructure changes.
