# Traceable text corpus imports

The corpus API imports real text into PostgreSQL. Passage text and references retain the selected electronic edition's wording; a separate Unicode-normalized `search_text` column feeds the existing PostgreSQL full-text index. A source being traceable does not make its interpretation true or authoritative.

The starter catalog is deliberately small and explicit. These downloads and parsers were checked against the following snapshots on 8 November 2026:

| Starter ID | Selected edition | Indexed passages | Original download size |
| --- | --- | ---: | ---: |
| `jps-1917-torah` | JPS 1917 English Torah, eBible electronic text; Genesis–Deuteronomy | 5,852 | 3,306,496 bytes |
| `kjv-1769` | KJV English Bible, Scrollmapper/CrossWire electronic text; 66 books | 31,102 | 8,400,187 bytes |
| `pickthall-en` | Pickthall English Quran translation, Tanzil electronic text; 114 surahs | 6,236 | 864,918 bytes |

The JPS selection belongs to both `torah` and `bible`. This is the same text with two collection memberships, not independent evidence. The JPS snapshot contains the full Tanakh archive, but only the five Torah books are indexed. The KJV selection's canon and wording are edition-specific. Pickthall is an English translation, separate from the Arabic Quran. None of these downloads supplies manuscripts, critical apparatus, hadith or tafsir.

The JPS download and public-domain notice are listed by [eBible](https://ebible.org/find/show.php?id=engjps). The pinned KJV JSON comes from [Scrollmapper](https://github.com/scrollmapper/bible_databases/tree/59b18c5af5845728c275d5b7178ad0d024172b1f/sources/en/KJV); [CrossWire](https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=KJV) describes its electronic source and licence, including underlying Crown rights. [Tanzil's own translation repository](https://tanzil.net/trans/) identifies Pickthall and supplies its non-commercial terms and accuracy disclaimer. The application stores those distinctions in `use_limits.rights_note` and provenance rather than applying its own software licence to downloaded texts.

`POST /api/v1/corpus/starters/{id}/import` fetches only a catalog URL. It refuses redirects, bounds transfer size to 20 MiB, checks the pinned SHA-256 and validates the expected passage count. For eBible it reads only the exact `engjps_vpl.txt` ZIP member in memory, with member-count and total decompression limits. It never extracts archive paths or executes bundled SQL. Changed source bytes require review and a catalog update.

The immutable original download is saved under the private data directory at `sources/<sha256>/original`. Inline JSON imports instead preserve a canonical import JSON snapshot and are labelled accordingly. A repeated snapshot and edition identity reuses the existing source. Importing a new revision creates a new source rather than rewriting old citations. Snapshot files, local corpus data and model output do not enter Git.

`GET /api/v1/corpus/search?q=...&collection=torah&source_id=<uuid>` supports repeated collection and source filters, lexical topic matching and explicit references such as `Genesis 1:1`, `1 John 4:8` or `Quran 2:156`. No match returns an empty list. Retrieval is not proof of exhaustive coverage; the English starters need English search terms, which a multilingual chat planner can generate. Citation URLs and `GET /api/v1/passages/{id}` retain the actual edition, source URL, exact quote, source snapshot hash and quote hash.

`GET /api/v1/passages/{id}/context?radius=1` adds actual adjacent verses from the same edition and chapter, retaining the unchanged center quote. The service accepts at most nine seed passages and a radius of zero to two verses. Missing verse slots remain missing; it never fills them from another edition, chapter or generated text. Nonstandard references retain their center without guessed neighbors. Each context citation carries its source use limits plus `is_center` and `context_for` metadata. Adjacent verses help review a quotation but are not a guarantee of whole-book context.

The retrieval service's `external_processing=True` flag admits only sources whose stored `use_limits.external_processing` is the JSON boolean `true`. Missing, false or string values do not authorize cloud processing. Manual imports default to false. Starter copies permit user-requested processing for this personal research workflow while retaining their source-specific rights notes; that setting does not grant publication, commercial redistribution or training rights. The global local-only/model-connection policy still governs provider calls separately.

Run `python -m pytest tests/test_corpus.py` from `app/backend` for focused checks. PostgreSQL integration cases use the existing isolated-schema fixture and require a dedicated `TEST_DATABASE_URL` database ending in `_test`. Unit tests do not replace PostgreSQL with SQLite. No test invokes an inference provider.
