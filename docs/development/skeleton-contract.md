# Skeleton implementation contract

The first implementation is an honest, runnable personal research skeleton. PostgreSQL is the only durable database. No sample religious answers, fabricated manuscript readings or automatic model downloads are used to simulate implemented research. Grounded corpus chat, autonomous web research and generated Roundtable discussion remain visibly unfinished until their evidence pipelines exist.

## Work surfaces

- `app/backend/compass/`: FastAPI/domain/storage, SQLAlchemy and Alembic. The `adapters/` subtree is independently owned.
- `app/frontend/`: React/TypeScript/Vite with EN/NL/AR/FR/DE and RTL.
- `app/config/`: model, persona and source-policy JSON; no credentials.
- `app/scripts/`: bootstrap, managed PostgreSQL lifecycle, development helpers.
- Root Pinokio scripts supervise the app; user data lives outside Git and synced folders.

## API surface under `/api/v1`

All successful lists use `{ "items": [...] }`. Errors use `{ "error": { "code": "stable_code", "message": "safe message" } }` and an appropriate non-2xx status. IDs are UUID strings except stable model/persona IDs.

- `GET /health`: `{status, version, database:{ready, message}, features:{...}}`. No credentials or full connection URL.
- `GET /models`: route fields `{id, title, model_id, provider, kind, enabled, configured, available, status, message, capabilities}`. No endpoint credentials or secrets. `kind` is `htr`, `vision`, `ocr` or `chat`.
- `PATCH /models/{id}` body `{enabled: boolean}`: explicitly enable/disable a known route; returns its safe route metadata. Enabling never configures keys or downloads a model.
- `GET /personas`: `{items:[{id,name,description}]}`.
- `GET /dossiers`; `POST /dossiers` body `{title, question?}`; `GET /dossiers/{id}`; `PATCH /dossiers/{id}` body `{title?,question?,notes?,expected_revision}`. Dossier fields `{id,title,question,notes,revision,created_at,updated_at}`. Conflicts return 409.
- `POST /images`: multipart `file`, `dossier_id`. Initial image imports require an explicitly created dossier; temporary Chat attachments are not implemented or silently saved. Image fields `{id,dossier_id,filename,media_type,width,height,sha256,created_at}`.
- `GET /dossiers/{id}/images`; `GET /images/{id}/content` (original validated image).
- `POST /transcription-jobs`: `{image_id,route_id,language?,region?}`; region is `{x,y,width,height}` in original pixel coordinates. Returns `{id,image_id,route_id,status,message,created_at,updated_at,transcription_id?}`.
- `GET /jobs/{id}`; `POST /jobs/{id}/cancel`; `GET /jobs/{id}/events` SSE with JSON job snapshots.
- `GET /images/{id}/transcriptions`: immutable revisions with `{id,image_id,parent_id,text,kind,engine,model_id,language,regions,warnings,created_at}`. `kind` is `automatic` or `user_corrected`. `POST /transcriptions/{id}/revisions` body `{text}` creates a new user-corrected revision.
- `POST /images/{id}/transcriptions` body `{text,language?}` starts an explicit manual reading (`user_corrected`, `parent_id:null`) when no OCR is configured. This does not pretend machine recognition occurred.
- Chat/research/Roundtable generation actions that are not yet grounded return an explicit `not_implemented` error or are disabled with explanation; no outbound model calls or invented answers to fill the UI.

## Adapter contract

`compass.adapters.registry.ModelRegistry(config_path: Path, state_path: Path | None = None, environ: Mapping[str,str] | None = None)` exposes:

- `list_routes() -> list[dict]`, `get_route(route_id) -> dict`, `set_enabled(route_id, enabled) -> dict`.
- `async transcribe(route_id: str, image_path: Path, language: str | None = None) -> TranscriptionResult`.

`compass.adapters.base.TranscriptionResult` has `text`, `engine`, `model_id`, `regions: list[dict]`, `warnings: list[str]`. Adapter errors derive from `AdapterError` with `code` and safe `message`. Availability is computed without contacting paid services. Local-only and enabled/capability checks apply at dispatch. Disconnected or missing models never yield synthetic text.

Chosen starter routes: Kraken 7.1/historical PP-OCRv6 medium with explicit model path/command; BiblIA, Meleagre, Muharaf and AraMS profiles; local Qwen3.8-27B GGUF Q5 + vision projector via a configured localhost OpenAI-compatible image endpoint; optional Mistral `mistral-ocr-4-1`; optional documented cloud vision profiles. Large runtimes/weights are separately installed by the user. No keys are copied into repository files.

## Initial verification

Meaningful routing/pin/local-only tests, API failure tests, real PostgreSQL migration/dossier/upload/revision checks, frontend typecheck/build and a real browser path. Managed Pinokio Install/Start/Stop must be tried. A blocked model route is expected until configured, not a failed app startup. No inference or paid API use is authorized during verification.
