# ADR 0001: Store Artifacts in Postgres (JSONB) for MVP

- Status: Accepted
- Date: 2025-11-07

## Context
We need to persist translation outputs (bitext JSONL lines), exports (bilingual/target-only Markdown), and QA summaries. Using an object store adds operational overhead early on and complicates backups and local development.

## Decision
For the MVP, store all artifacts directly in Postgres using JSONB columns.
- Artifacts table shape: `(id, job_id, kind, format, data jsonb, size_bytes, created_at)`.
- Examples:
  - `kind=bitext, format=jsonl, data={ lines: [{src_id, src, tgt, flags: []}], meta: {chapter_id} }`
  - `kind=bilingual_md, format=md, data={ content: "..." }`
  - `kind=target_md, format=md, data={ content: "..." }`
  - `kind=qa_summary, format=json, data={ counts, ratios, samples[] }`

## Rationale
- Simplicity: single persistence layer and backup story (pg_dump).
- Local-first: easy for developers and small deployments.
- Speed: fewer moving parts to ship MVP quickly.

## Consequences
- Pros:
  - One backup/restore mechanism; fewer services to operate.
  - Faster iteration on schema and artifact shapes.
- Cons:
  - DB size growth; potential I/O and vacuum pressure for large artifacts.
  - Large binary assets (e.g., PDFs) are less efficient in DB.

## Mitigations
- Enforce artifact size caps per job.
- Prefer text artifacts; gzip large text and store as base64 when needed.
- Prune intermediate artifacts and keep canonical exports.
- Index by `(job_id, kind)` and track `size_bytes` to monitor growth.

## Alternatives Considered
- Object storage (S3/MinIO): better for scale, but adds complexity (credentials, lifecycle policies, consistency). Postpone until artifacts exceed comfortable DB thresholds.
- Filesystem storage: simple but brittle across environments and harder to back up coherently with DB metadata.

## Rollback / Evolution Path
- Introduce an abstraction layer in the API (ArtifactRepository) with Postgres-backed implementation now; add S3-backed implementation later.
- Background migration job can stream artifacts from DB to object storage, replacing `data` with pointers (`uri`, `checksum`) while keeping metadata in Postgres.

