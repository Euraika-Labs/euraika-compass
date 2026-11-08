# Source-grounded chat

Compass has a first chat path through configured model connections, imported text
editions, PostgreSQL retrieval and explicit conversation saving. Live inference
evidence is recorded separately: configuration or a model listing does not verify
a complete research conversation, neutrality or historical-script accuracy.

## Start in the interface

1. In **Connections**, add **Mistral**, a title, your private API key and an exact
   account model ID. The recommended default is `mistral-large-4-0`. Saving a
   connection does not call a model.
2. Explicitly turn off **Local-only** to permit cloud processing. Discover account
   models to confirm an ID, then **Test connection** for one small real inference
   request. A model listing alone does not establish inference permission.
3. In **Sources**, import the editions you want. Starters include JPS 1917 English
   Torah, KJV English Bible and Pickthall's English Quran translation. They are
   electronic text editions, not manuscripts or substitutes for original-language
   editions. See [corpus imports](corpus-imports.md) for coverage and use limits.
4. In **Chat**, select an enabled connection, persona and answer language, then
   ask a question. Source selection restricts the editions used. The five personas
   change conversational method and share the same neutral evidence policy.
5. Inspect citation wording, edition, source URL and snapshot metadata. Read
   neighboring verses where available and distinguish quotation from interpretation.
6. Choose **Save conversation**, enter a title and optionally attach it to a
   dossier. Saving includes all validated temporary turns. Reopen the saved
   conversation to continue it in PostgreSQL.

Local OpenAI-compatible servers are also supported, with loopback-only custom
URLs. Other cloud providers use fixed official endpoints and their own keys and
account model IDs. Failed requests never silently select another model.

## Retrieval and model behavior

The backend freezes the selected configuration for a turn. Changes to its
provider, model, endpoint, enabled state, credential or cloud policy invalidate
the turn before its next model request. Planning, answering and any format repair
use the same selected model.

Mistral Large 4 planning uses `reasoning_effort="low"` and at most 2,048 completion
tokens; answering uses `"high"` and at most 8,192. One format/citation repair may
use the same answer budget. A connection test uses low effort and at most 512
tokens. These are ceilings, not promised usage or answer lengths. Explicit tests
and chats can incur provider charges. The recommendation follows the official
[model card](https://docs.mistral.ai/models/mistral-large-4) and
[reasoning guide](https://docs.mistral.ai/inference/conversations/reasoning);
it is not a theological benchmark or neutrality guarantee.

Current retrieval combines **lexical PostgreSQL full-text search** and an LLM
rewrite into short search queries. The rewrite can bridge a Dutch, Arabic or
French question to English starter texts. Exact passage references also work.
The model receives selected stored passages, provenance and permitted recent
conversation context. It must cite supplied `[S1]` identifiers and state limits.
Missing or unknown source references and unmatched long explicit quotations are
rejected. After at most one repair, an invalid answer fails without saving a turn.

Chat expands up to nine selected search passages with their immediate neighboring
verses, within the same edition and chapter. It sends existing text only, capped
at 27 passage items and 28,000 source-text characters. Citation inspection can also
fetch context with `GET /api/v1/passages/{id}/context?radius=1` (radius zero to two).
Nearby context is not whole-book interpretation. Lexical matching, query rewriting
and edition coverage can miss relevant passages; absence from retrieval does not
establish agreement or disagreement.

There is **no semantic embedding/reranking pipeline yet**, despite the pgvector
schema foundations. Chat does not autonomously search the web, discover or
download manuscripts, or generate Roundtable discussions. Starter imports are
explicit catalog downloads. Broader web research and Roundtable generation remain
future work.

## Private processing and saving

Local-only mode is the default and blocks cloud inference even when keys exist.
Cloud retrieval requires the source's stored `external_processing` permission to
be the boolean `true`. Restricted source-derived assistant history is omitted
from cloud context; client-supplied assistant history is not validated evidence.
Keys stay backend-only, and connection responses reveal only whether a key is
set. Connection and cloud-policy changes refresh reader configuration without
enabling any OCR route.

Temporary chats live in server memory, with a **30-minute inactivity window** and
**40 validated turns**. Restarting loses temporary sessions. A full 40-turn session
can still be saved. Explicit saving preserves all its questions, validated answers,
citation snapshots, warnings, selected model, persona and language. Later successful
turns in a saved conversation persist automatically. Invalid answers do not append
a turn. Saving does not publish or share the conversation.

Consistent evidence standards and attributed interpretations support neutral
research; they cannot guarantee a model has no religious, cultural or linguistic
bias. Open citations and compare competing readings yourself.

## API examples

Use the actual loopback URL shown by Pinokio. These examples contain no key and
assume `MISTRAL_API_KEY` is already set in the launcher's private `settings.env`.
Alternatively, enter a key in the app's Connections form. A connection with no
available credential remains unconfigured.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/connections \
  -H 'Content-Type: application/json' \
  -d '{"title":"Mistral research","provider":"mistral","model_id":"mistral-large-4-0","enabled":true}'

curl -X PATCH http://127.0.0.1:8000/api/v1/chat-settings \
  -H 'Content-Type: application/json' -d '{"local_only":false}'

curl http://127.0.0.1:8000/api/v1/connections
curl http://127.0.0.1:8000/api/v1/corpus/starters
curl -X POST http://127.0.0.1:8000/api/v1/corpus/starters/jps-1917-torah/import
```

Replace `CONNECTION_ID` with the returned ID. The next request performs real
inference: normally planning and answering, with one possible format/citation repair.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"How do these texts discuss mourning?","connection_id":"CONNECTION_ID","persona_id":"comparative","language":"en"}'
```

Use the returned `session_id` as `SESSION_UUID` to save all validated turns.
Temporary follow-ups send `session_id` to `/chat`; saved follow-ups instead send
the saved conversation's `id` as `conversation_id`.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/conversations \
  -H 'Content-Type: application/json' \
  -d '{"title":"My mourning research","session_id":"SESSION_UUID"}'

curl http://127.0.0.1:8000/api/v1/conversations
```

Schemas are at `/docs` and `/openapi.json`. Focused checks from `app/backend`:
`python -m pytest tests/test_connections.py tests/test_chat.py tests/test_corpus.py`.
PostgreSQL cases require the dedicated test database described in the
[development guide](README.md). Automated provider tests use boundary doubles
and do not make paid inference calls.
