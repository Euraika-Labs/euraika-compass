# Developing the Compass skeleton

This repository now contains application source, not just planning documents.
Implemented slices include private dossiers with original images and versioned
readings, real model connections, traceable text imports, lexical retrieval and
source-grounded chat with explicitly saved conversations. Autonomous web research
and AI Roundtable generation remain unfinished. See the [grounded-chat guide](grounded-chat.md)
and [corpus-import guide](corpus-imports.md) for the current flow and its limits.

## Layout

```text
app/
  backend/           FastAPI, SQLAlchemy, PostgreSQL migrations and tests
    compass/adapters/  Kraken, local Qwen and Mistral OCR dispatch
  frontend/          React/TypeScript/Vite, five UI languages and RTL
  config/            Model metadata, personas and source policy
  workers/kraken/    Optional isolated local HTR worker
  scripts/           Managed PostgreSQL lifecycle and local checks
install.js           Pinokio dependency installation; no weights or keys
start.js             Managed DB, migrations and local Web UI
update.js            Fast-forward source update, then dependency repair
reset.js             Generated backend/frontend dependencies only
```

## Pinokio

Install the repository as a Pinokio app and use **Install → Start → Open Web UI**.
The launcher installs Python 3.12, compatible PostgreSQL 16.15/pgvector 0.8.6
binaries, the locked backend dependencies and the frontend production build.
It does not install Kraken/Torch, download weights or enable a paid provider.
Pinokio's normal Stop action stops the supervised app and its owned DB processes.

The native Windows PostgreSQL 16.15/pgvector 0.8.6 path and real backend
migration/persistence tests have been exercised. Full ordinary Pinokio-flow and
browser verification are being completed separately. No historical-image inference
has been verified; configured adapters are not an accuracy claim.

The default private directory is reported by:

```text
app/backend/env/Scripts/python.exe app/scripts/manage.py doctor
```

On Linux/macOS use the venv's `bin/python` instead. The default uses local
application data (`EuraikaLabs/EuraikaCompass`), outside the repository and
OneDrive. It contains PostgreSQL, immutable images and source snapshots, route
settings and private connection configuration.
**Reset dependencies does not remove this directory or model weights.**
An explicitly supplied external `DATABASE_URL` is never stopped by Compass.

Put selected environment settings in that private directory's `settings.env`;
see the root `.env.example`. The launcher loads this file before starting. Keys
are backend-only. Connections can also store provider credentials privately through
the UI. Opening connection metadata makes no network request; **Discover models**
explicitly requests a provider listing, and **Test connection** performs a small
real inference call. Neither operation downloads a model or starts another server.
Local-only is the default. Explicit cloud permission in Connections is required
for remote chat or enabled remote readers; the reader route remains a separate
choice. See [source-grounded chat](grounded-chat.md) for API examples.

## Development commands

After the managed dependencies have been installed:

```powershell
# Backend including real, isolated PostgreSQL tests; no model calls.
app/backend/env/Scripts/python.exe app/scripts/check_postgres.py

# Plain unit/API tests without a database also work, with PG tests skipped.
Set-Location app/backend
env/Scripts/python.exe -m pytest
env/Scripts/python.exe -m ruff check compass tests ../scripts

# Frontend (another terminal, from app/frontend).
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

For an external development DB, set `DATABASE_URL` to PostgreSQL, run
`alembic upgrade head` from `app/backend`, then use `uvicorn compass.main:app`
on loopback. A missing database leaves the shell and model/persona metadata
available with a degraded status; database actions return a clear error.
There is no SQLite substitute.

The real-PostgreSQL helper creates a dedicated `compass_test` database in its own
cache cluster, runs the tests and stops that owned cluster. An explicit
`TEST_DATABASE_URL` must name a database ending in `_test`; each test uses and
cleans its own schema. Do not point developer tests at personal research data.

For frontend development, start the backend and set `COMPASS_API_URL` to its
loopback URL before `npm run dev`. Production uses relative `/api/v1` URLs and
is served by FastAPI. See the frontend package scripts for browser tests.

## API examples

The actual OpenAPI schema is at `/openapi.json`, interactive docs at `/docs`.
Replace the example port with the URL shown by Start. Lists use `{items: [...]}`;
errors use `{error: {code, message}}`. The shared consumer contract is in
[skeleton-contract.md](skeleton-contract.md).

Curl:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl -X POST http://127.0.0.1:8000/api/v1/dossiers \
  -H 'Content-Type: application/json' \
  -d '{"title":"My research","question":"Which readings are visible?"}'
```

JavaScript:

```javascript
const base = "http://127.0.0.1:8000/api/v1";
const routes = await fetch(`${base}/models`).then((r) => r.json());
console.log(routes.items.map(({ title, status }) => ({ title, status })));
```

Python:

```python
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000/api/v1") as client:
    response = client.post("/dossiers", json={"title": "My research"})
    response.raise_for_status()
    dossier = response.json()
    # Deliberately attach this image to a saved research dossier.
    with open("my-photo.png", "rb") as photo:
        image_response = client.post(
            "/images", data={"dossier_id": dossier["id"]},
            files={"file": ("my-photo.png", photo, "image/png")},
        )
    image_response.raise_for_status()
    image = image_response.json()
    manual = client.post(
        f"/images/{image['id']}/transcriptions",
        json={"text": "The letters I can actually read", "language": "en"},
    )
    manual.raise_for_status()
```

Manual text is marked as a user reading, not as OCR output. A correction creates
a new immutable revision; it does not overwrite the first reading. Configured
transcription jobs expose status, cancellation and SSE snapshots. Until a real
reader is installed/configured, requesting it returns a specific unavailable
route error, not invented text. See [the model research](../research/2026-11-08-ocr-htr-model-selection.md)
and `app/workers/` for the selected optional runtime profiles.

## Remaining implementation

- Broader source-package formats, original-language editions and semantic
  embedding/reranking retrieval; the initial text import, lexical retrieval and
  source-grounded chat path is implemented.
- Autonomous web search/extraction under the source policy.
- AI-generated Roundtable turns and synthesis.
- Model/runtime installation UI; actual historical-script quality trials.
- Full dossier export/import and consistent backup/restore UI.
- Temporary Chat image uploads (initial images require an explicit dossier).

These are visible boundaries of the skeleton, not simulated working features.

See the [Windows skeleton verification record](2026-11-08-skeleton-verification.md)
for the exercised Pinokio lifecycle, real PostgreSQL and Chrome checks, actual
screenshots and the limits of that verification.
