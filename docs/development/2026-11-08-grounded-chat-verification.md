# Real model and source-grounded chat verification — 8 November 2026

Compass was tested through its running Pinokio application on Windows, with a
real Mistral account and real imported text editions. Credentials and downloaded
texts remain in the private application-data directory, outside Git.

## Exercised behavior

| Check | Result |
| --- | --- |
| Mistral discovery and inference | Account model listing succeeded; an explicit `mistral-large-4-0` connection returned a real inference response |
| Source imports | JPS 1917 Torah: 5,852 passages; KJV Bible: 31,102; Pickthall Quran: 6,236; 43,190 indexed passages in total |
| Real Chrome chat | An English interface sent a Dutch comparative question with answer language Auto; the answer was returned in Dutch with inspectable stored source passages |
| Citation identity | Every returned citation's exact text, edition revision and source-snapshot hash matched `GET /passages/{id}` |
| Saving | The temporary conversation was explicitly saved through the UI and reopened after page reload with its references intact |
| Other Chrome flows | Connection/source/chat UI contract and existing dossier/image/manual-transcription flow passed |
| Backend | 129 tests passed with real PostgreSQL integration, including cloud permissions, immutable sources, unknown-reference rejection, cancellation, saved turn order and fixed model selection |
| Frontend | 18 unit tests, TypeScript, ESLint and production build passed; npm audit reported zero known vulnerabilities |
| Python checks | Ruff passed for backend, tests, migrations, lifecycle scripts and optional worker |

The final live run's model stages took approximately 72 seconds in total. That
is an observation for one comparative question, not a latency guarantee.
The live test is explicitly opt-in; normal tests do not consume provider credit.
GitHub Actions results are reported separately from these local checks.

## Corrections found during integration

- High-effort inference needed a longer bounded wait than the initial lightweight
  request timeout. The chosen model and reasoning effort stay unchanged.
- Candidate selection needed enough token capacity for reasoning before its short
  JSON response. Its low-effort ceiling is now 8,192 tokens.
- Keyword overlap brought in legally relevant passages that did not answer the
  emotional question. The planner now preserves intent and proposes references
  only as checked lookup hints; candidate relevance is assessed within each
  selected collection.
- An unequal example schema could steer one collection toward an empty selection.
  It was removed. Each selected collection receives the same instructions and may
  still return no relevant evidence; there is no forced consensus or quotation.
- Literal model quotations could differ from the stored edition. Answers now use
  paraphrases; the source panel supplies the actual stored wording. Existing
  reference and quotation checks still reject invalid output.
- An English repair instruction could change an Auto answer's language. The
  original question language is now fixed for the entire turn and any repair.
- Temporary turns retain their original generation timestamps when saved together,
  preserving their sequence rather than ordering equal save timestamps by UUID.

These are practical implementation checks, not a theological evaluation program.
Reference identity does not prove a paraphrase, interpretation or historical claim.
The live output also showed occasional mixed-language wording, so language polish
and interpretive accuracy remain review tasks rather than certified properties.

## Scope and captures

The starter texts are **English electronic translations**, not manuscript images
or original Hebrew, Greek or Arabic editions. Torah/Bible memberships overlap and
must not be counted as independent evidence. Source-specific provenance and rights
notes are retained; the software licence does not relicense the downloaded texts.

Autonomous web research, generated Roundtable turns, original-language starter
editions, vector retrieval, installed local OCR/HTR weights and full dossier
export/import remain further implementation. Only Mistral was exercised with a
live provider; other transports have request/response boundary tests.

The screenshots show a deliberately generic QA question and synthetic dossier
records, with no API key or personal conversation content:

- [Actual chat and source panel](images/grounded-chat.png)
- [Saved conversation after reopening](images/saved-grounded-chat.png)

See the [chat guide](grounded-chat.md) for configuration and the opt-in live check,
and [corpus notes](corpus-imports.md) for exact source snapshots and import limits.
