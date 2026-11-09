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
5. Open a citation to inspect the quoted edition and an available original-language
   passage or published translation beside it. The cited edition stays the anchor.
   A mapped reference may display a different verse number; an uncertain match is
   labelled for comparison only. Source and licence links remain visible.
   For online context, enable **Web research** for the question. Its citations
   show a separate evidence card with the consulted excerpt and a link to the source.
6. Choose **Save conversation**, enter a title and optionally attach it to a
   dossier. Saving includes all validated temporary turns. Reopen the saved
   conversation to continue it in PostgreSQL.

Local OpenAI-compatible servers are also supported, with loopback-only custom
URLs. Other cloud providers use fixed official endpoints and their own keys and
account model IDs. Failed requests never silently select another model.

## Retrieval and model behavior

The backend freezes the selected configuration for a turn. Changes to its
provider, model, endpoint, enabled state, credential or cloud policy invalidate
the turn before its next model request. Planning, relevance selection, answering and any format repair
use the same selected model.

Mistral Large 4 planning uses `reasoning_effort="low"` and at most 2,048 completion
tokens. Relevance selection also uses low effort, with an 8,192-token ceiling so
reasoning about many candidates does not consume the entire response budget.
Answering uses `"high"` and at most 8,192 tokens. One format/citation repair may
use the same answer budget. A connection test uses low effort and at most 512
tokens. These are ceilings, not promised usage or answer lengths. Explicit tests
and chats can incur provider charges. The recommendation follows the official
[model card](https://docs.mistral.ai/models/mistral-large-4) and
[reasoning guide](https://docs.mistral.ai/inference/conversations/reasoning);
it is not a theological benchmark or neutrality guarantee.

Current retrieval combines **lexical PostgreSQL full-text search**, a model-assisted
multilingual query plan, and a bounded model selection from actual candidate passages.
The planner can bridge a Dutch, Arabic or French question to English starter texts
and propose verse references as lookup hints. A hint contributes evidence only if
the selected edition actually contains it and its source passes the same filters.
Up to 60 real candidates are considered. Relevance is assessed separately within
each selected collection, rather than displacing one collection with another in
a single global top list. The model may select up to nine existing candidate IDs
in total or return no relevant evidence for a collection. Rejected matches are not
reintroduced to fill a quota. Final `[S1]` labels are assigned after this selection.
The model receives selected stored passages, provenance and permitted recent
conversation context. It must cite supplied `[S1]` identifiers and state limits.
The model is asked to paraphrase and reflect; the citation panel supplies literal
wording directly from the stored edition. Missing or unknown source references
and unmatched long explicit quotations are rejected. Visible ellipses may omit
existing words in order, but cannot introduce new ones. After at most one repair,
an invalid answer fails without saving a turn.

Chat expands up to nine selected search passages with eligible aligned editions
and immediate neighbors within the same edition and chapter. A parallel is model
evidence only if it passes source selection and cloud permissions and has an
established reference alignment. Chat sends existing text only, capped at 27
passage items and 28,000 source-text characters. Citation inspection can also
fetch context with `GET /api/v1/passages/{id}/context?radius=1` (radius zero to two).
Nearby context is not whole-book interpretation. Lexical matching, query rewriting,
model selection and edition coverage can miss relevant passages; absence from
retrieval does not establish agreement or disagreement. Response metadata keeps
retrieved collections separate from collections actually cited in the answer.

`GET /api/v1/passages/{id}/parallel` returns the cited edition and available
parallel readings from local storage. The reader can show the local-only Tanzil
Arabic text beside a Pickthall citation even when the remote model saw only the
English translation. Opening the reader does not send text to a model.

There is **no vector-embedding retrieval or dedicated local reranker worker yet**,
despite the pgvector foundations. The current relevance selector is the selected
chat model. Autonomous manuscript acquisition and Roundtable generation remain
future work. Starter imports are explicit catalog downloads.

## Optional web research

**Web research** starts off for each question. With Local-only off and this option
enabled, the selected model proposes at most two short public search topics.
Only the accepted search terms go to the search services. The planner is asked to
omit personal details, and the backend rejects obvious identifiers and links.
Query minimization is not guaranteed anonymization. The turn records the actual
queries; search services also receive normal connection metadata such as IP address.
Local-only prevents lookup even with a local inference model selected.

The initial search services need no separate API key: [DOAJ](https://doaj.org/terms/)
supplies publisher-deposited abstract metadata under its metadata terms, and
[Wikimedia TextExtracts](https://www.mediawiki.org/wiki/Extension:TextExtracts)
supplies introductory text with a link to the consulted revision. A local model
can also use indexed [OpenAlex abstracts](https://help.openalex.org/data/works/attributes/);
the app keeps those out of cloud prompts when the excerpt's processing rights
are unclear. This is a bounded search of public indexes rather than an
unrestricted crawler or a guarantee of full-text access.

The web sources supplement the editions. A publisher abstract supports what its
authors report; it does not establish what the whole paper says. An encyclopedia
excerpt gives background and is labelled as such. A search snippet or a title alone
is not usable evidence. Only rights-eligible excerpts are sent to a cloud model.
The evidence panel shows the original URL, retrieval time, source type and available
attribution, publication date and licence. The same source markers open both web
evidence and edition passages, each in its own reader. Web evidence has no
scripture collection membership. A failure or lack of usable results does not
disable local corpus retrieval.

Explicitly saving a conversation preserves its cited excerpt and provenance with
the turn. Chat does not add fetched sources to the corpus or retain entire pages.
Earlier web-derived answers are not passed back as trusted evidence to cloud models.

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
inference: normally planning, relevance selection and answering, with one possible
format/citation repair. High-effort Mistral requests have a bounded 240-second
deadline rather than the shorter default for lightweight calls.

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

An opt-in Chrome check exercises a real configured Mistral Large 4.0 connection,
the three imported starters, source inspection, explicit saving and reloading.
It is skipped unless `COMPASS_LIVE_CHAT=1` is deliberately set:

```powershell
$env:COMPASS_BASE_URL = "http://127.0.0.1:<port-shown-by-Pinokio>"
$env:COMPASS_LIVE_CHAT = "1"
# From app/frontend; this makes real provider calls.
npx playwright test e2e/live-chat.spec.ts
```
