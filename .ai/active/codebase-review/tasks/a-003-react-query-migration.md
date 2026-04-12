# A-003 Task Plan — TanStack Query Migration

## Status

- Finding: `A-003`
- Source: `architecture-findings.md`
- Status: `in progress`
- Owner: `frontend`
- Last updated: `2026-04-12`

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

### Phase 1 — Infrastructure ✓ Done

- `@tanstack/react-query` added
- `QueryClient` set up in `frontend/src/lib/queryClient.ts` with conservative defaults:
  - `retry: false`
  - `refetchOnWindowFocus: false`
  - `staleTime: 30_000`
- App root wrapped in `QueryClientProvider` in `frontend/src/main.tsx`

### Phase 2 — Query Modules and Keys — Partial

The generated SDK now includes a `frontend/src/client/@tanstack/react-query.gen.ts` file that
exports per-endpoint query key factories and `queryOptions`/`infiniteQueryOptions` builders. These
are used directly by the hooks rather than through manual domain modules.

Manual domain modules (`frontend/src/queries/`) were not created. The generated key factories serve
the same function but are verbose at call sites and do not express domain-level groupings (e.g.
"all prompts for a work") that invalidation needs.

Remaining:
- Create `frontend/src/queries/` domain modules that wrap the generated keys into stable, named
  key hierarchies for use by `invalidateQueries` calls.

### Phase 3 — Read Hook Migration ✓ Done

All main read hooks now use TanStack Query via `useQueryState` in `frontend/src/lib/queryState.ts`:

- `useWorks` ✓
- `useWork` ✓
- `useWorkChapters` ✓
- `usePrompts` ✓
- `usePrompt` ✓
- `usePromptVersions` ✓
- `useWorkPromptDetail` ✓ (uses `useQuery` directly)
- `useWorkPrompts` ✓
- `useChapter` ✓

`useQueryState` preserves the `{ data, loading, error }` return shape and routes error messages
through `getApiErrorMessage`.

Refresh token dependencies have been removed from all read hooks.

### Phase 4 — Prompt Domain Mutations — Partial

`useMutation` is wired up at all prompt mutation sites using generated mutation helpers:

- `PromptEditor.tsx`: `updatePrompt`, `appendPromptVersion`, `deletePrompt` ✓
- `PromptsLandingPane.tsx`: `createPrompt` ✓
- `WorkPromptSelector.tsx`: `updatePrompt` (work prompt assignment) ✓
- `usePromptOverride.ts`: `appendPromptVersion` ✓

**Gap:** `queryClient` is imported at each site but `invalidateQueries` is never called. Mutations
complete but do not update the shared cache, so prompt list and detail views do not reflect saves
unless manually refreshed.

Remaining:
- Wire `invalidateQueries` in `onSuccess` for each mutation, following the invalidation rules below:
  - prompt create: invalidate `prompts.list(*)`
  - prompt update: invalidate `prompts.detail(promptId)`, `prompts.list(*)`
  - prompt append version: invalidate `prompts.detail(promptId)`, `prompts.versions(promptId)`,
    `prompts.workDetail(workId)` if assigned
  - prompt delete: invalidate `prompts.list(*)`, remove `prompts.detail(promptId)` and
    `prompts.versions(promptId)`
  - work prompt assignment: invalidate `prompts.workDetail(workId)`, `prompts.workList(workId, *)`

### Phase 5 — Work and Chapter Mutation Migration — Partial

`useMutation` is wired up at all work/chapter mutation sites:

- `AddWorkModal.tsx`: `importWork` ✓
- `CreateChapterGroupModal.tsx`: `createGroup` ✓
- `AddToGroupModal.tsx`: `addToGroup` ✓
- `WorkDetailPage.tsx`: `deleteGroup` ✓
- `ScrapeModal.tsx`: `queueScrape`, `cancelScrape` ✓

**Same gap as Phase 4:** no `invalidateQueries` calls anywhere. Mutations complete silently without
updating the cache.

Remaining:
- Wire `invalidateQueries` in `onSuccess`:
  - work import: invalidate `works.list(*)`
  - chapter-group create/delete/member add: invalidate `works.chapters(workId, *)`,
    `works.chapterGroups(workId)`
  - scrape queued: optional invalidate `works.chapters(workId, *)`
  - scrape completed or partial: invalidate `works.chapters(workId, *)`, `works.detail(workId)`

### Phase 6 — Streaming Integration

Not started.

Keep streaming hooks custom but wire them to query invalidation on terminal events:

- on completed/partial scrape, invalidate chapters and affected work detail
- on translation completion/reset/regenerate, invalidate affected chapter/translation queries
- on explanation completion, invalidate chapter detail if explanation state is queried

### Phase 7 — Cleanup

Refresh token plumbing has already been removed. Remaining cleanup:
- consolidate any remaining raw `fetch` mutation helpers behind domain modules
- document query-key conventions for future frontend work

## Suggested Implementation Order

1. ~~query client and provider~~ ✓ done
2. query modules and key factories — create `frontend/src/queries/` domain modules wrapping the generated keys
3. ~~read-hook compatibility migration~~ ✓ done
4. prompt mutations and invalidation — add `invalidateQueries` to existing `useMutation` sites
5. work/chapter mutations and invalidation — add `invalidateQueries` to existing `useMutation` sites
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
