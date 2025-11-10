# Work & Chapter Scraping To-Dos

## Backend
- [x] Introduce `WorksService`/`ChaptersService` with `get_chapters_for_work` and `get_chapter` helpers that accept a SQLAlchemy session and hide pagination/404 logic.
- [x] Implement `POST /works/import` that accepts a URL, routes it to the matching scraper, upserts a `Work`, and seeds baseline metadata (source, external id, last_scraped_at).
- [x] Build chapter scraping orchestration that takes a work id + start/end/rescrape flag, fetches missing chapters sequentially, and replaces content when requested.
- [x] Expose `GET /chapters/{chapter_id}` returning the full chapter payload (title, idx, normalized_text) for the reader/sync UI.
- [x] Update existing works/chapters routers to reuse the new services and ensure pagination + total counts remain accurate.
- [x] Add unit tests around the new service methods and integration tests for the ingestion + chapter scrape routes.

## Frontend
- [x] Add an "Add New Work" dialog to `WorksPage` that validates the pasted URL, hits `/works/import`, and refreshes the works list on success.
- [x] Create a `WorkDetailPage` showing work metadata, a paginated chapter list (titles only), and a scrape-control panel for selecting ranges/rescrape.
- [x] Implement hooks (`useWork`, `useWorkChapters`, `useScrapeChapters`) to drive the Work page and keep it in sync with backend status.
- [x] Provide a minimal chapter viewer or drawer that loads chapter details via `GET /chapters/{id}` to confirm scraped content.

## Docs & Ops
- [ ] Document the new scraping workflow (curl examples, expected payloads, env vars) so manual testers can follow the flow end-to-end.
