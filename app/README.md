# Application source

- `backend/`: Python/FastAPI, PostgreSQL schema/migrations and API tests.
- `frontend/`: React/TypeScript/Vite, localization and workbench.
- `config/`: public model/persona/source-policy metadata; never credentials.
- `workers/`: optional OCR/HTR and image-server integration contracts.
- `scripts/manage.py`: managed local PostgreSQL, migration and server lifecycle.
- `runtime/` and backend `env/`: generated ignored dependencies, not source.

Use root Pinokio Install/Start for the managed Windows flow. The default data path
is a per-user local application-data directory, outside this checkout and OneDrive.
An external PostgreSQL URL can be configured explicitly for development. SQLite is
not used as a fallback.

The first live slice is a dossier with an original photo and manually entered or
configured-engine transcript revisions. Corpus-grounded conversation, web search
and AI Roundtable generation are scaffolded, clearly unavailable capabilities.
Actual model inference, corpus grounding and dossier export/import remain unfinished
or unverified as described in the [development guide](../docs/development/README.md).
See the root README for the Pinokio Install/Start quick start.
