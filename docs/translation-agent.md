# Translation Agent & Regeneration Flow

This prototype now uses a LangChain 1.x agent (ChatOpenAI) to perform the JP→EN chapter
translations. The same agent powers the synchronous chapter-translation endpoint and the
streaming SSE feed consumed by the reader UI.

## Configuration

Set the following environment variables (see `backend/.env.example`):

- `TRANSLATION_API_KEY` – OpenAI-compatible API key. Leave blank to fall back to lorem ipsum
  placeholders for local UI smoke tests.
- `TRANSLATION_MODEL` – Defaults to `gpt-4o-mini`; update if you prefer another model id.
- `TRANSLATION_API_BASE_URL` – Override for self-hosted/proxy endpoints. Leave empty for the
  default OpenAI API domain.
- `TRANSLATION_CHUNK_CHARS` – Controls how many characters are emitted per streaming chunk when
  the fallback lorem generator is active. This also serves as a soft target for chunking output
  when the real provider streams very large deltas.

After changing these values, recycle the `api-dev` container (e.g. `just dev-down && just dev-up`)
so the FastAPI process reloads the new settings.

## How the agent runs

1. The backend segments chapters on newline boundaries (collapsing blank sequences) and stores the
   offsets in `translation_segments`.
2. For each pending segment, the LangChain agent streams the translation text. SSE events bubble
   every delta so the frontend can render partial output.
3. Completed segments are persisted immediately; if the stream disconnects mid-segment, the
   translation remains pending and can be resumed later.

If no API key is configured, the agent transparently falls back to the lorem ipsum generator so
operators can still validate the workflow without incurring model cost.

## Regenerating a translation

- The REST API now exposes `DELETE /works/{work_id}/chapters/{chapter_id}/translation`, which
  wipes the stored translation segments and resets the translation status to `pending`.
- The Chapter Detail page surfaces a **Regenerate** button. Clicking it issues the delete request
  and automatically restarts the streaming translation once the reset succeeds.

You can also call the endpoint manually (replace the ids as needed):

```bash
curl -X DELETE http://localhost:8087/api/works/1/chapters/5/translation
```

The response mirrors the `GET` payload and can be used to inspect the fresh segment layout before
triggering the stream.

## Error handling

- SSE now emits a `translation-error` event with the provider exception string if the LangChain
  call fails. The frontend surfaces this via the translation panel alert.
- The backend leaves the translation status as `error` so operators can investigate and retry via
  the regenerate control.

## Local testing tips

- With no API key, the lorem fallback still exercises the streaming plumbing; this is handy for
  CI or dev containers without secrets.
- When developing against the real provider, prefer short sample chapters to limit token usage.
- Use `just test` or `just sanity` after dependency upgrades to ensure the API container still
  boots with the new LangChain stack.
