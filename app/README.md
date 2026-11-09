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

The app supports dossiers with original photos and revision history, model
connections, text editions, and conversations with inspectable corpus and online
evidence. See the [grounded-chat guide](../docs/development/grounded-chat.md)
for search and citations. Roundtable generation and dossier export/import are
planned, as described in the [development guide](../docs/development/README.md).
See the root README for the Pinokio Install/Start quick start.
