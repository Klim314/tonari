## Agents-Specific Instructions (Gemini / Codex)

### Long-Running Task Tracking

When working on multi-session tasks under `.ai/active/`, use a two-file pattern for progress tracking:

- **`state.md`** — Compact current state. Contains: status, findings/task summary table, current focus, next steps, blockers, open questions. **Overwritten** (not appended to) each session to stay small. This is what you read first when resuming work.
- **`log.md`** — Append-only session history. Add a dated entry at the end of each session summarizing what was done and decisions made. Only read this when you need to understand *why* a past decision was made.

The goal: `state.md` stays small enough to always fit in context. `log.md` grows freely but is never loaded by default.

When starting a session on an existing task:
1. Read `state.md` to understand current state
2. Do the work
3. Overwrite `state.md` with updated state
4. Append a session entry to `log.md`

### Active Tasks

See `.ai/active/` for in-progress work. Each subdirectory is a self-contained task with its own process docs and artifacts.
