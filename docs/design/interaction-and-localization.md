# Interaction, languages, and web research

The consolidated screen and interaction baseline is [design.md](../../design.md), with system contracts in [architecture.md](../../architecture.md). This document retains detailed language and web-research requirements under [functional.md](../../functional.md).

Status: user-directed product requirements, 8 November 2026. This is a design specification, not implemented functionality. It extends the main implementation plan. The current visual references are `compass-chat-v4.png` and `compass-research-v4.png`.

## Two connected views

Later additions extend both views without changing their purpose. Chat offers an explicit One-to-one / Roundtable choice for user-moderated AI discussion. Research adds Manuscripts and Interpretations panels for genuine admitted scans and evidence-based comparisons of readings. These additions are specified in the [shared evidence and hybrid-model contract](../plans/research-method-and-model-architecture.md). Version 5 concepts now illustrate interpretations, Roundtable and role routing; the manuscript viewer itself is not yet pictured. Ordinary life conversations do not automatically become debates. Local/cloud model processing, web search, and remote image viewing have distinct connection states and settings.

**Chat** is the default entry for life questions. It has a normal readable conversation, a persona selector, a composer, and collapsible history. Sources appear through compact citations or an expandable source area when relevant. Supportive listening does not require a three-column scripture comparison, a citation count, or an internet search on every turn. Textual and factual claims still require their appropriate sources. A broad request for wisdom from the three books follows the requested collection scope even when the evidence is initially collapsed.

**Research** is a workspace with a library/web navigator, document tabs, parallel original texts and translations, a conversation panel, word study, research log, and notes. Panels can be resized and collapsed; useful layouts can be restored. Keyboard users must be able to operate panel and tab controls. Narrow screens stack panels rather than compressing all columns beyond readability.

The top-level **Chat / Research** switch changes the layout, retaining the active temporary conversation, persona, scope, selected editions, evidence, and draft. **Open in Research** opens the referenced evidence and exact passage in that workspace. Returning to Chat retains context and scroll position. Switching layouts never starts a new model run by itself. A temporary chat remains temporary; the UI shows persisted history only for conversations deliberately saved to a dossier. The mockup history is illustrative of saved conversations.

## Euraika visual identity

The palette was read from the public [Euraika site](https://www.euraika.net/) and its shipped CSS on 8 November 2026:

| Token | Value | Intended use |
| --- | --- | --- |
| Euraika Blue | `#001C3A` | App bar, icon rail, primary actions |
| Euraika Blue Light | `#003369` | Supporting blue, selected states |
| Euraika Gold | `#F4A616` | Sparse active accents, highlights, action emphasis |
| Euraika Charcoal | `#1E2D39` | Body text and dark text/icons on gold |
| Secondary text | `#51545A` | Supporting text on white |

White and pale neutral reading surfaces support long sessions. Gold is an accent, not a full-page background or a religion-specific identity. Text and focus contrast must be measured in the implementation; a generated image is not accessibility evidence. The compass mark in the images is an exploratory app mark, not a verified reproduction of the official corporate logo. State must be expressed through text/icons as well as color.

## Independent language settings

- **Interface language:** English (`en`) on first launch. Initial target locales: English, Nederlands (`nl`), العربية (`ar`), Français (`fr`), Deutsch (`de`). The user selects and persists a preference; browser language does not silently override the English default. More locales can be added through translation catalogs.
- **Conversation language:** follows the user's message or explicit conversation preference. An English interface can hold a Dutch conversation. A language change does not silently translate or overwrite prior messages.
- **Source language and translation:** each reader panel has its own edition and language. Original text, published translation, model translation, transliteration, and annotation remain distinct. A localized UI does not imply that a licensed scripture translation or a validated specialist model exists in that language.

All interface text, including persona descriptions, errors, loading/empty states, source metadata labels, keyboard hints, and accessibility names, uses message catalogs. Use locale-aware dates, numbers, and plural rules. Keep English fallback visible and track untranslated keys; never expose raw message keys as normal UI. Store stable IDs independently of translated labels. Use endonyms in the language picker, with no country flags equated to languages.

Arabic changes the interface direction to RTL. Layout uses logical start/end properties; directional navigation icons are mirrored where meaningful. Arabic shaping, vowel marks, line breaking, selection, copy/paste, and appropriate font fallback require live checks. Each source/message block has its own language and direction, with isolated mixed-direction references, URLs, and numbers. An Arabic original stays RTL within an English interface; an English translation stays LTR within an Arabic interface. Hebrew receives the same passage-level direction handling. Source bytes and reference IDs never change through UI localization.

UI localization and model capability are separate release claims. An Arabic menu can be complete while Arabic generation remains a preview; communicate that distinction. Evaluate answers and retrieval in each advertised conversation language, with qualified reviewers and relevant source editions. Do not extrapolate Dutch/English impartiality results to French, German, or Arabic. Keep the original evaluation family splits intact when adding translated variants and report their additional workload.

## Optional autonomous web research

The assistant can plan queries, search, read pages, compare evidence, and cite relevant external material within a bounded read-only workflow when web research is enabled. The interface exposes a global control and a per-run log. Start disabled until the user enables and configures the provider; the mockups illustrate the enabled state. Ordinary listening turns may need no search. Research requests requiring current facts or external scholarship use the web when enabled; a disabled/unavailable provider produces an explicit limitation.

Use a provider adapter with search and extraction capabilities. The concrete default provider, API terms, cost, and dependency versions must be checked at implementation admission. This app uses its own configured provider credentials; it cannot inherit this development chat's connectors or login. Store secrets locally outside Git and browser bundles. A paid provider needs explicit user setup; provider failure must not trigger an undisclosed fallback service.

The workflow has these requirements:

1. Identify the question's collection scope and evidence needs. Search different perspectives with equivalent evidence standards, including relevant scholarship and attributed tradition-specific commentary. Provider ranking is not a truth ranking or proof of balanced coverage. A religious institution's self-description and an academic historical claim have different evidentiary roles.
2. Send minimized topic terms. Avoid personal names, identifying details, and whole chat transcripts for life questions. Show the actual outgoing query in the run log. Test this behavior; do not market an absolute guarantee that free text can never disclose personal information. External search queries and fetched domains are network disclosures even with local inference.
3. Retrieve and read cited pages. A search snippet alone is a lead, not verified evidence. Preserve URL, title, author/publisher where available, publication/update dates where stated, access time, source type, and a content hash for inspected content. Unknown dates stay unknown. Attribute interpretations and separate primary text, commentary, scholarship, and personal reflection.
4. Keep web evidence distinct from admitted scripture editions. A webpage quoting scripture cannot silently replace the named canonical edition. Validate its reference against the local edition when claiming an exact canonical quote. Detect mirrors/duplicate pages so repetition does not masquerade as independent corroboration.
5. Fit search and fetch operations inside R12's shared run budget (initially twelve model/tool steps and at most two query refinements). Bound pages, response size, redirects, timeouts, and content types. Surface partial results, cancellation, inaccessible pages, and stale/changed content; never claim a completed exhaustive internet search.
6. Treat retrieved text as untrusted evidence, never as instructions. Extraction does not execute page scripts. URL fetching blocks loopback, private/link-local networks, file URLs, and disallowed schemes, and rechecks redirects/DNS resolution. Follow applicable access restrictions; no bypass of login/paywalls.
7. Apply per-use rights checks. Reading an accessible page does not grant permission to redistribute it, permanently index it, train on it, or export full snapshots. Store/export allowed metadata, links, and permitted excerpts; otherwise record that the page must be fetched again. A hash alone cannot reproduce unavailable text, so mark that evidence limit. Dossiers retain the provenance and usage status of web material as well as corpus passages.

## Implementation and verification ownership

- **U3:** shared workspace state, accessible panel controls, locale catalogs, English default, all five initial UI languages, live LTR/RTL and mixed-script reader flows.
- **U4:** web provider adapter, read-only search/extract pipeline, provenance and rights records, duplicate grouping, source-scope coverage, query minimization and network constraints. No external provider is selected merely by this document.
- **U5:** ordinary chat, source expansion, persona selection, Chat/Research transitions, optional web orchestration and partial/failure behavior.
- **U6:** preserve language/settings and evidence versions in dossiers, with rights-aware export.
- **U7:** deterministic and human evaluation of the new behaviors. Web fixtures make regression runs reproducible; separately timestamp a live provider smoke test so changing search rankings are not confused with fixed-suite reproducibility.
- **U8:** English first launch, saved locale, disabled-web offline operation, provider setup, and the ordinary Pinokio lifecycle.

Required scenarios include mode switching without losing drafts or changing storage consent; no forced scripture dump in supportive chat; all five locales including translated errors and dialogs; Arabic RTL with English references and Hebrew/Greek passages; stable source IDs after locale changes; keyboard and narrow-screen flows; network-off requests producing no search/fetch calls; search-provider failure; snippets unsupported by fetched pages; changed or inaccessible pages; missing dates; injected source instructions; malicious redirects/private-network targets; private details omitted from outgoing queries; unequal source supply; duplicated publishers; religion-specific interpretations properly attributed; criticism evaluated with the same standard across traditions; and a source-rights restriction blocking snapshot export.

Acceptance evidence must distinguish an implemented feature, a localized UI, an evaluated conversation language, and a provider-tested web capability. Generated screenshots establish none of these by themselves.
