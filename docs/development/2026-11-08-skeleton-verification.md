# Skeleton verification — 8 November 2026

The initial application skeleton was exercised on Windows through Pinokio 8.3.7,
using the ordinary launcher default action. These checks cover the implemented
workbench and integration boundaries, not historical-script reading accuracy.

## Results

| Check | Observed result |
| --- | --- |
| Pinokio Install | Completed with Python 3.12.16, PostgreSQL 16.15, pgvector 0.8.6, locked Python dependencies, `npm ci` and production frontend build |
| Start and URL capture | Managed DB, Alembic migration and FastAPI started; capture group 1 supplied the loopback Open Web UI URL |
| Health and OpenAPI | Database ready, implemented feature flags accurate, documented API routes present; unfinished generation flags false |
| Backend tests | 46 passed against an isolated PostgreSQL test database, including adapter boundaries and lifecycle regressions |
| Python lint | Ruff passed for backend, tests, lifecycle scripts and optional worker |
| Frontend checks | Typecheck, ESLint, 8 Vitest tests and production build passed |
| Dependency audit | npm reported zero known vulnerabilities in the installed dependency tree |
| Real Chrome flow | Chat draft retained across view changes; dossier created; valid PNG imported; manual mixed-script reading saved and recovered after page reload; Arabic language and RTL applied |
| Stop | App and owned PostgreSQL listening ports closed after Pinokio Stop |
| Reset and clean reinstall | Backend venv, frontend dependencies and build removed and recreated through Pinokio; the new venv used managed Python 3.12 |
| Durable data after reinstall | Same dossier and transcript IDs/text recovered; downloaded original bytes matched their pre-reset SHA-256 hash |
| Browser flow after reinstall | The same end-to-end flow passed against the rebuilt application |

The database tests use a separate `compass_test` database and temporary schemas.
Browser tests create explicitly named `Skeleton browser check …` records in the
local workbench. Their white 32 × 24 PNG is a neutral file-handling fixture, and
their text is labelled as a manual fixture note. Such test records are not sources
or automatic readings. Screenshots contain only those synthetic records.

## Integration defects caught and fixed

- Full-image HTTP readers now identify image MIME from verified bytes. Immutable
  assets have hash-only filenames, so extensions cannot determine their type.
- Malformed PNG checksums return `422 invalid_image` rather than an unexpected
  server error. A regression includes decodable pixels with a bad IDAT checksum.
- If graceful PostgreSQL cleanup fails, bounded termination and log closure apply
  only to the child owned by that lifecycle instance. Reused or external servers
  are not terminated by that fallback.
- Reading drafts survive background job completion, and stale save results cannot
  update a different selected image.

## What these checks do not establish

No model weights, Kraken/Torch runtime or WSL distribution were installed. No
live OCR/vision inference or paid provider call was made. The configured-reader
adapters were tested at their request/response and process boundaries; actual
model, projector, checkpoint compatibility and reading quality still require
deliberate setup and trials with the user's material. A route marked configured
is not an account or runtime probe.

Corpus import, grounded Chat, autonomous web research, generated Roundtable turns,
translation, dossier export/import and complete backup/restore UI remain future
implementation. Their boundaries are visible in the interface and API. Linux and
macOS launcher operation was not exercised during this Windows verification.

The backend tests emit one upstream Starlette TestClient deprecation warning;
all assertions pass. This record is local verification, not a claim that remote
GitHub Actions have already completed.

## Actual captures

- [Research workspace](images/skeleton-research.png)
- [Arabic RTL workspace](images/skeleton-arabic.png)
