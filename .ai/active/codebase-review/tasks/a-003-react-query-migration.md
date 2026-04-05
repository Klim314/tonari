# A-003 Task Plan — TanStack Query Migration

## Status

- Finding: `A-003`
- Source: `architecture-findings.md`
- Status: `planned`
- Owner: `frontend`
- Last updated: `2026-04-05`

## Goal

Move frontend server-state handling toward TanStack Query while preserving the generated API client as the transport boundary.

This task exists to replace repeated `useEffect` + `loading/error/data` hooks and local refresh-token plumbing with shared query keys, mutation wrappers, and explicit invalidation.

## Why This Exists

Current frontend data access is split across many custom hooks and component-local mutations:

- `frontend/src/hooks/useWorks.ts`
- `frontend/src/hooks/useWork.ts`
- `frontend/src/hooks/useWorkChapters.ts`
- `frontend/src/hooks/usePrompts.ts`
- `frontend/src/hooks/usePrompt.ts`
- `frontend/src/hooks/usePromptVersions.ts`
- `frontend/src/hooks/useWorkPromptDetail.ts`
- `frontend/src/hooks/useWorkPrompts.ts`
- `frontend/src/hooks/useChapter.ts`
- `frontend/src/components/PromptEditor/PromptEditor.tsx`
- `frontend/src/components/PromptsLandingPane.tsx`
- `frontend/src/pages/WorkDetailPage.tsx`

The current shape duplicates:

- request lifecycle handling
- abort wiring
- loading/error state
- refetch sequencing after mutations
- ad hoc refresh-token propagation

## Scope

In scope:

- add TanStack Query provider at the app root
- define shared query keys and domain query modules
- migrate read hooks to query-backed implementations
- migrate high-value mutations to `useMutation`
- centralize cache invalidation rules
- keep streaming hooks custom, but connect them to query invalidation

Out of scope for this task:

- router migration from custom location handling to `react-router-dom`
- replacing the generated client
- fully redesigning streaming transport
- broad page/component redesign unrelated to data flow

## Target Architecture

1. Generated client remains the low-level API contract boundary.
2. Query modules own:
   - query keys
   - query option builders
   - mutation functions
   - invalidation helpers where useful
3. UI consumes domain hooks backed by TanStack Query rather than handwritten fetch state machines.
4. Streaming hooks remain custom, but invalidate relevant queries on terminal events.

## Proposed File Layout

- `frontend/src/queries/works.ts`
- `frontend/src/queries/prompts.ts`
- `frontend/src/queries/chapters.ts`
- `frontend/src/queries/translations.ts`
- `frontend/src/lib/queryClient.ts`
- optional: `frontend/src/hooks/useDebouncedValue.ts`

## Rollout Strategy

Prefer an incremental migration with compatibility wrappers.

Do not rewrite every page to direct `useQuery` usage in one pass. First move existing hooks onto TanStack Query internally so page churn stays small and behavior changes remain localized.

## Phases

### Phase 1 — Infrastructure

- add `@tanstack/react-query`
- create `QueryClient` setup in `frontend/src/lib/queryClient.ts`
- wrap app root in `QueryClientProvider`
- choose conservative defaults:
  - `retry: false` for most queries initially
  - `refetchOnWindowFocus: false`
  - moderate `staleTime`
  - use placeholder/previous-data behavior for paginated lists where needed

Deliverable:

- app boots with a shared query client and no feature behavior changes

### Phase 2 — Query Modules and Keys

Create domain query modules with stable key factories.

Initial keys:

- `works.all`
- `works.list(searchQuery)`
- `works.detail(workId)`
- `works.chapters(workId, { limit, offset })`
- `works.chapter(workId, chapterId)`
- `works.chapterGroups(workId)`
- `prompts.all`
- `prompts.list(searchQuery)`
- `prompts.detail(promptId)`
- `prompts.versions(promptId)`
- `prompts.workDetail(workId)`
- `prompts.workList(workId, searchQuery)`

Requirements:

- forward TanStack `signal` into generated-client requests
- normalize query arg construction in one place
- preserve current `getApiErrorMessage()` behavior at the hook boundary

Deliverable:

- domain query modules exist and can be imported without changing UI yet

### Phase 3 — Read Hook Migration

Migrate current read hooks to use TanStack Query internally:

- `useWorks`
- `useWork`
- `useWorkChapters`
- `usePrompts`
- `usePrompt`
- `usePromptVersions`
- `useWorkPromptDetail`
- `useWorkPrompts`
- `useChapter`

Notes:

- keep current return shapes temporarily where practical:
  - `data`
  - `loading`
  - `error`
- remove `refreshToken` dependencies from implementations first
- remove `refreshToken` parameters from call sites after mutation invalidation lands
- keep search debounce outside the query layer via `useDebouncedValue`

Deliverable:

- repeated `useEffect` fetch hooks are eliminated without a broad page rewrite

### Phase 4 — Prompt Domain Mutations

Migrate prompt-related writes first because they currently have the most explicit manual refresh coupling.

Mutation targets:

- prompt create
- prompt update
- prompt delete
- prompt append version
- work prompt assignment

Primary current touchpoints:

- `frontend/src/components/PromptEditor/PromptEditor.tsx`
- `frontend/src/components/PromptsLandingPane.tsx`
- `frontend/src/components/WorkPromptSelector.tsx`
- `frontend/src/hooks/usePromptOverride.ts`

Invalidation rules:

- prompt create:
  - invalidate `prompts.list(*)`
- prompt update:
  - invalidate `prompts.detail(promptId)`
  - invalidate `prompts.list(*)`
- prompt append version:
  - invalidate `prompts.detail(promptId)`
  - invalidate `prompts.versions(promptId)`
  - invalidate `prompts.workDetail(workId)` if the prompt is assigned to a work in active view
- prompt delete:
  - invalidate `prompts.list(*)`
  - remove or invalidate `prompts.detail(promptId)`
  - remove or invalidate `prompts.versions(promptId)`
- work prompt assignment:
  - invalidate `prompts.workDetail(workId)`
  - invalidate `prompts.workList(workId, *)`
  - invalidate `works.detail(workId)` only if assignment metadata is surfaced there later

Deliverable:

- prompt save/create/delete flows stop using local refresh counters

### Phase 5 — Work and Chapter Mutation Migration

Migrate work/chapter mutations next.

Mutation targets:

- work import
- chapter-group create
- chapter-group delete
- chapter-group member add
- scrape request
- scrape cancel where appropriate

Primary current touchpoints:

- `frontend/src/components/AddWorkModal.tsx`
- `frontend/src/components/CreateChapterGroupModal.tsx`
- `frontend/src/components/AddToGroupModal.tsx`
- `frontend/src/pages/WorkDetailPage.tsx`
- `frontend/src/components/ScrapeModal.tsx`

Invalidation rules:

- work import:
  - invalidate `works.list(*)`
- chapter-group create/delete/member add:
  - invalidate `works.chapters(workId, *)`
  - invalidate `works.chapterGroups(workId)` if introduced
- scrape queued:
  - optional immediate invalidate `works.chapters(workId, *)`
- scrape completed or partial:
  - invalidate `works.chapters(workId, *)`
  - invalidate `works.detail(workId)` if counts/status derive from scrape results

Deliverable:

- work detail flows stop depending on page-local chapter refresh tokens

### Phase 6 — Streaming Integration

Keep streaming hooks custom for now:

- scrape status
- chapter translation streams
- explanation generation streams
- lab streaming

But integrate them with query invalidation:

- on completed/partial scrape, invalidate chapters and affected work detail
- on translation completion/reset/regenerate, invalidate chapter/work translation-related queries
- on explanation completion, invalidate chapter detail if explanation state is queried

Deliverable:

- streams become first-class writers into the shared cache lifecycle

### Phase 7 — Cleanup

- remove obsolete `refreshToken` state from components and pages
- remove dead helper code for manual refetch orchestration
- consolidate any remaining raw `fetch` mutation helpers behind domain modules
- document query-key conventions for future frontend work

Deliverable:

- no core page depends on local refresh tokens for server-state consistency

## Suggested Implementation Order

1. query client and provider
2. query modules and key factories
3. read-hook compatibility migration
4. prompt mutations and invalidation
5. work/chapter mutations and invalidation
6. streaming invalidation integration
7. cleanup and follow-up notes

## Risks

- search UX regressions if debouncing behavior changes
- over-invalidation causing unnecessary refetch churn
- under-invalidation causing stale prompt/work views
- query-key drift if modules are added without conventions
- mixing direct `fetch` mutations and generated-client mutations during transition

## Guardrails

- keep generated client authoritative for non-streaming requests
- do not combine this with the router migration
- avoid page-by-page direct `useQuery` rewrites in the first pass
- prefer invalidating precise domains over broad global invalidation
- preserve existing user-facing loading and error behavior until tests/manual checks are updated

## Verification Checklist

- prompt list/search still debounces correctly
- prompt save refreshes prompt detail and version history without local counters
- prompt create/delete updates prompt list consistently
- work prompt assignment updates current prompt view and selector results
- work import updates works list
- chapter-group create/delete/add-member updates chapter list correctly
- scrape completion updates chapter list without manual page refresh
- frontend typecheck passes
- frontend lint/build pass after migration slices land

## Open Questions

- Should query modules expose `queryOptions(...)` only, or also exported hook wrappers?
- Should raw `fetch` chapter-group endpoints be migrated by regenerating the SDK first, or wrapped temporarily in local mutation helpers?
- Do any translation/explanation completion paths need dedicated `translations` query keys immediately, or can that module begin as a placeholder?

## Exit Criteria

This task is complete when:

- root query infrastructure is in place
- the main read hooks are query-backed
- prompt and work/chapter mutations invalidate shared cache entries instead of using refresh tokens
- streaming completion paths invalidate affected queries
- obsolete refresh-token plumbing has been removed from primary flows
