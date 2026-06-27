# Phase 1 Review

## Review — claude-opus-4-8[1m] — 2026-06-28

**Files reviewed**: backend/app/kakuyomu/parser.py, backend/app/kakuyomu/scraper.py, backend/app/scrapers/text.py, backend/app/syosetu/parser.py, backend/services/scrape_manager.py, backend/app/main.py, backend/app/models.py, backend/app/schemas.py, backend/alembic/versions/8eb2a39579b1_chapter_source_chapter_id.py, backend/tests/test_kakuyomu_parser.py, backend/tests/test_kakuyomu_scraper.py
**Changes**: Adds a Kakuyomu scraper that reads the ordered episode TOC + metadata from the page's embedded Apollo cache, caches opaque episode ids per work to bridge positional chapter numbers into the shared scrape loop, extracts shared text-normalize/ruby helpers, and records a diagnostic `source_chapter_id` per chapter.

### Important
- **[services/scrape_manager.py:159]** `scraper.build_chapter_url(...)` runs directly on the asyncio event loop, but for Kakuyomu it lazily triggers a *blocking* synchronous HTTP fetch (`_episode_ids` → `self.http_client.fetch`) on the first chapter of a cold work. Unlike `scrape_chapter` (which is correctly wrapped in `run_in_threadpool`), this call will stall the whole event loop — including SSE heartbeats/broadcasts for every other work — for the duration of the work-page request. The Syosetu path is pure string-building so this was previously free; the new source breaks that assumption.
  → Wrap the URL build in `run_in_threadpool` as well (`chapter_url = await run_in_threadpool(scraper.build_chapter_url, work.source_id, sort_key)`), or pre-warm the TOC once before the loop via `run_in_threadpool` so the per-iteration call is a guaranteed cache hit.

- **[app/kakuyomu/scraper.py:31,97-103]** The registered scraper is a process-wide singleton (`scraper_registry.register(KakuyomuScraper())` at import) whose `_toc_cache` is never invalidated. For a still-serializing work (`serial_status == "RUNNING"`, as the fixture is), once the TOC is cached, newly published episodes are invisible until the process restarts, and a re-scrape requesting chapter N+1 will raise `ScraperError("out of range")` forever. The cache also grows unbounded over process lifetime.
  → Add a TTL or explicit invalidation (e.g. re-fetch when a requested index exceeds the cached length, or refresh the cache at the start of each scrape job). At minimum document the staleness window; "out of range" on a running work is a confusing operator-facing error.

- **[app/kakuyomu/scraper.py:31]** The shared `_toc_cache` on a singleton is mutated from worker threads (`build_chapter_url` is invoked via `run_in_threadpool` for `scrape_chapter` siblings, and per the fix above could be threaded). `dict` get/set on a single key is GIL-atomic so this won't corrupt, but two concurrent jobs for the same cold work id can both fetch and both write — wasteful, not incorrect. Acceptable; noting for completeness.

- **[services/scrape_manager.py:7-15 / app/kakuyomu/parser.py:73]** `_source_chapter_id_from_url` derives the id from the URL's trailing segment, but the *authoritative* episode id is already known inside the scraper (`episode_ids[index-1]`) and the parser already pairs `(episode_id, title)`. Re-deriving it by string-splitting the URL is fragile (a trailing slash, query string, or fragment on a Kakuyomu URL would change the result) and couples `scrape_manager` to URL shape conventions of every source. Works today for both shapes, but consider having the scraper expose the source id directly rather than reverse-engineering it from the URL.

### Minor
- **[app/kakuyomu/parser.py:70-72]** `chapter_ref.get("__ref")` / `union_ref.get("__ref")` assume each list element is a dict. If Apollo ever stores a bare ref string or null in `tableOfContentsV2`/`episodeUnions`, this raises `AttributeError` instead of a clean `ScraperError`. Parsing untrusted upstream JSON — guard with `isinstance(chapter_ref, dict)` or wrap the loop in the same `ScraperError` translation used by `_load_apollo_state`.
- **[app/kakuyomu/parser.py:123-125]** Body extraction falls back from `find_all("p", recursive=False)` to `find_all("p")` to whole-node text. Reasonable, but `get_text(separator="", strip=False)` on each `<p>` means an empty `<p>` yields `""` and produces blank lines; `normalize_text` collapses 3+ newlines to 2 but a single intentional-vs-accidental blank line is indistinguishable. Likely fine given the fixture passes; flagging that empty-paragraph handling is implicit.
- **[app/kakuyomu/scraper.py:33-34]** `matches()` uses `endswith(_HOSTNAME)` which would also match e.g. `evilkakuyomu.jp` (no dot boundary). Low risk since the registry resolves by exact hostname-set membership first, but the Syosetu scraper has the same loose check — consistent, not a regression.
- **[app/main.py:107]** The `from app.kakuyomu import scraper as _kakuyomu_scraper` form is correct and necessary as noted (a plain `import app.kakuyomu.scraper` rebinds nothing here, but the chosen form is the safe one and avoids the `app` name collision). No action; confirmed correct.
- **[alembic/.../8eb2a39579b1.py:20-21]** Nullable column with no default and no backfill is the right call for a diagnostic field — existing rows stay `NULL`, no data-loss risk. Fine.
- **[.env.example]** Drops `GEMINI_API_KEY` and routes Gemini through OpenRouter. Unrelated to the Kakuyomu change; ensure no code still reads `GEMINI_API_KEY` before committing.

### Summary
Solid, well-tested scraper with correct Apollo traversal and a proper wrong-work guard; safe to commit functionally, but the blocking-TOC-fetch on the event loop and the never-invalidated singleton cache should be addressed before this runs against live, still-serializing works.

---

## Resolution — claude-opus-4-8[1m] — 2026-06-28

Addressed the review findings:

- **[Important] Blocking TOC fetch on event loop** — `build_chapter_url` is now called via `run_in_threadpool` in `services/scrape_manager.py` so the cold/refresh HTTP fetch can't stall the loop or SSE broadcasts.
- **[Important] Never-invalidated singleton cache** — `build_chapter_url` now refreshes the TOC once (`_episode_ids(..., refresh=True)`) when a requested index exceeds the cached length, so re-scrapes of a still-serializing work pick up new episodes without a restart. New test: `test_build_chapter_url_refreshes_stale_toc`.
- **[Important] Fragile URL-derived source id** — `_source_chapter_id_from_url` now uses `urlparse(...).path`, so query strings / fragments / trailing slashes are ignored. Test extended to cover `?utm=x#top`.
- **[Minor] Malformed Apollo entries** — TOC traversal now guards `isinstance(..., dict)` on chapter/union/episode refs, raising clean `ScraperError` instead of `AttributeError`.
- **[Minor] Loose `matches()`** — Kakuyomu `matches()` now requires an exact host or a `.kakuyomu.jp` subdomain boundary (no longer matches `evilkakuyomu.jp`).
- **[Minor] `.env.example` / GEMINI_API_KEY** — verified no code reads `GEMINI_API_KEY`; pre-existing/unrelated change, safe.
- **[Important, noted-only] Concurrent double-fetch** and **[Minor] empty-paragraph handling** — left as-is per the reviewer's "acceptable" assessment.

Verification: 33 targeted tests pass (kakuyomu + syosetu + async-scraping + chapters-service); `ruff check` clean.

---
