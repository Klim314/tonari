# Translation Runtime

This document describes the current translation and explanation flow used by the backend and the
reader UI.

## Configuration

Relevant environment variables live in `.env` and `.env.example`.

- `TRANSLATION_MODEL`
  Default model for chapter translation when a work has no assigned prompt version. Current
  default: `gpt-5.2`.
- `TRANSLATION_API_KEY`
  API key used by the chapter translation path today. If unset, the backend falls back to the stub
  lorem-ipsum stream.
- `TRANSLATION_API_BASE_URL`
  Optional base URL override for OpenAI-compatible endpoints.
- `TRANSLATION_CHUNK_CHARS`
  Chunk size used by the stub fallback stream.
- `TRANSLATION_CONTEXT_SEGMENTS`
  Number of preceding translated segments to include as context for each segment request.
- `OPENAI_API_KEY` / `GEMINI_API_KEY`
  Additional provider-specific keys used by some paths, notably the prompt lab.
- `PROMPT_OVERRIDE_SECRET`
  Secret used to sign one-off prompt override tokens.
- `PROMPT_OVERRIDE_TOKEN_TTL_SECONDS`
  Expiry window for prompt override tokens.

After changing runtime settings, restart the dev stack so the FastAPI process reloads config.

## Chapter Translation Flow

Chapter translation is driven by the `/works/{work_id}/chapters/{chapter_id}` routes.

1. The backend resolves the chapter translation record or creates one if it does not exist.
2. The chapter text is segmented into newline-delimited slices and stored in
   `translation_segments`.
3. The backend selects the translation prompt and model in this order:
   - one-off prompt override token, if provided
   - latest version of the work's assigned prompt
   - global defaults from config
4. The translation agent streams each pending segment.
5. Each completed segment is persisted immediately.
6. When all pending segments finish, the chapter translation status becomes `completed`.

If no usable API key is available, the agent falls back to the lorem-ipsum stub stream. This keeps
the streaming UI usable for local smoke tests, but it is not a real translation path.

## Streaming Endpoints

Primary endpoints:

- `GET /works/{work_id}/chapters/{chapter_id}/translate/stream`
  Stream a full chapter translation.
- `GET /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/retranslate/stream`
  Retranslate one segment, optionally with an `instruction` query parameter.
- `GET /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/explain/stream`
  Stream an explanation for one translated segment.
- `POST /lab/stream`
  Prompt-lab translation stream. This path is ephemeral and does not persist data.

Common SSE events emitted by the chapter translation flow:

- `translation-status`
- `segment-start`
- `segment-delta`
- `segment-complete`
- `translation-complete`
- `translation-error`

## State and Reset Operations

Useful non-streaming endpoints:

- `GET /works/{work_id}/chapters/{chapter_id}/translation`
  Return the current translation state and segment payloads.
- `DELETE /works/{work_id}/chapters/{chapter_id}/translation`
  Reset a chapter translation and rebuild its segments.
- `POST /works/{work_id}/chapters/{chapter_id}/regenerate-segments`
  Discard and regenerate segment boundaries for the chapter.
- `PATCH /works/{work_id}/chapters/{chapter_id}/segments/batch`
  Apply manual segment edits. This clears cached explanations for edited segments.
- `POST /works/{work_id}/chapters/{chapter_id}/prompt-overrides`
  Create a signed one-off prompt override token for a translation run.

## Prompt and Model Resolution

Work-level prompt selection is stored separately from translation runs.

- A work can be assigned a default prompt.
- A prompt can have many versions.
- Chapter translation uses the latest version of the assigned prompt unless a prompt override token
  is supplied.
- Prompt versions can change both the template and the model used for a run.

The prompt lab is separate from the persisted chapter translation flow. It accepts raw text,
explicit model selection, and an explicit template, and it does not create or update database
records.

## Error Handling

- Translation failures are surfaced through `translation-error` SSE events.
- On failure, the backend marks the chapter translation as `error`.
- If a client disconnects during streaming, the translation is left in a resumable state rather
  than being discarded.

## Verification

For local verification:

- use a short chapter to confirm streaming behavior
- check `/models` to confirm available model ids
- use the chapter detail UI to confirm reset, retranslate, and explanation flows
- run `just test` after translation-path changes
