# Backlog

Deferred work for the translation-explanation-layer task. Items here are known issues or improvements that are not blocking the current phase.

---

## Force-reset race in `ExplanationWorkflowV2.start(force=True)`

**Severity:** Low priority for now (single-user deployment). Revisit before multi-user or when moving the registry to Redis.

**Location:** [backend/services/explanation_workflow_v2.py:142-159](../../../backend/services/explanation_workflow_v2.py#L142-L159)

**Problem:**
`start(force=True)` runs three awaitable steps sequentially — `registry.cancel` → `regenerate()` → `_ensure_generation`. Between the cancel and the regenerate, a concurrent SSE `subscribe()` can:

1. Observe `status == "pending"` with partial `payload_json` from the cancelled run.
2. Find no registry handle (the cancelled runner's `finally` already deleted it).
3. Start a new producer whose `_run_generation` reads the pre-reset `payload_json` and builds `done_facets` from the stale partial.

When our `regenerate()` then wipes `payload_json`, the subscriber's producer is already committed to skipping facets that no longer exist in storage. The subsequent `_ensure_generation` call from `start` is idempotent and just attaches to the broken producer. Result: artifact ends up permanently missing facets.

**Reachability:** Possible with a single user if the frontend opens a new SSE connection shortly after a `force=true` POST while the previous SSE is still open.

**Fix options (in order of increasing effort / correctness):**
1. **Reorder**: reset before cancel. Narrows but does not close the window (cancelled runner may still write `update_facet` after our reset, before our cancel lands).
2. **Per-artifact async lock**: serialize `start(force)` and `subscribe()`'s lazy-start path on a lock keyed by `artifact_id`. Closes the window. Leaks one `asyncio.Lock` per artifact (fine for single-user; can prune on handle cleanup).
3. **Atomic restart in the registry**: add `GenerationRegistry.restart(artifact_id, reset_fn, producer_factory)` that holds the handle-creation critical section across supersede + reset + start. Most correct; most code.

**Recommendation when picked up:** Option 2 unless we're already refactoring the registry for Redis, in which case fold the restart semantics into the registry itself (option 3).

---

## Multi-worker support for generation registry

**Severity:** Deferred. Tracked separately — the registry is process-local by design until we move it to Redis.

**Location:** [backend/services/explanation_generation_registry.py:133](../../../backend/services/explanation_generation_registry.py#L133)

**Problem:**
`_registry` is a module global. Under `uvicorn --workers >1` (or any multi-process deployment) the POST and the SSE GET can land on different workers: worker A starts the detached task, worker B's `subscribe()` finds no handle and starts a duplicate generation.

**Plan:** Move the registry behind Redis (or a DB advisory lock keyed on `artifact_id`) when we need multi-worker. Until then, single-worker is a deployment requirement.

---
