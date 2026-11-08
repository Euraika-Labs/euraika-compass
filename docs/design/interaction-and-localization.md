# Interaction, languages, and web research

The consolidated screen and interaction baseline is [design.md](../../design.md), with system contracts in [architecture.md](../../architecture.md). This document retains detailed language and web-research requirements under [functional.md](../../functional.md).

Status: user-directed requirements for personal, neutral theological research, updated 8 November 2026. This is a design specification, not implemented functionality. It extends the main implementation plan. Quality checks are practical source and app checks, not a certification or expert-panel release program. The current visual references are `compass-chat-v4.png` and `compass-research-v4.png`.

## Two connected views

Research is the central theological workspace; Chat provides a simpler conversation view over the same sources and context. Chat offers an explicit One-to-one / Roundtable choice for user-moderated AI discussion. Research adds Manuscripts and Interpretations panels for genuine traceable scans and evidence-based comparisons of readings. These additions are specified in the [shared evidence and hybrid-model contract](../plans/research-method-and-model-architecture.md). Version 5 concepts illustrate interpretations, Roundtable and role routing; the manuscript viewer itself is not yet pictured. Ordinary life conversations do not automatically become debates. Local/cloud model processing, web search, and remote image viewing have distinct connection states and settings.

**Chat** is a simple entry for a question, discussion or life question. It has a normal readable conversation, a persona selector, a composer, and collapsible history. Sources appear through compact citations or an expandable source area when relevant. Supportive listening does not require a three-column scripture comparison, a citation count, or an internet search on every turn. Textual and factual claims still require their appropriate sources. A broad request for wisdom from the three books follows the requested collection scope even when the evidence is initially collapsed.

**Research** is a workspace with a library/web navigator, document tabs, parallel original texts and translations, a conversation panel, word study, research log, and notes. Panels can be resized and collapsed; useful layouts can be restored. Keyboard users must be able to operate panel and tab controls. Narrow screens stack panels rather than compressing all columns beyond readability.

The top-level **Chat / Research** switch changes the layout, retaining the active temporary conversation, persona, scope, selected editions, evidence, and draft. **Open in Research** opens the referenced evidence and exact passage in that workspace. Returning to Chat retains context and scroll position. Switching layouts never starts a new model run by itself. A temporary chat remains temporary; the UI shows persisted history only for conversations deliberately saved to a dossier. The mockup history is illustrative of saved conversations.

## Reading photographs and scans

Image-to-text is a core research flow under R28. The user can import a photograph of a manuscript, book page or inscription, or choose a consulted online scan. Opening an image does not itself run OCR or send it to a model. Choose the page/region, script/language when needed, and a suitable local image-reading worker or an explicitly configured image-capable route. No vendor or engine is mandatory at this design stage.

Research displays the image and proposed transcription side by side, with zoom and page/region selection. Printed-text OCR, handwriting recognition and vision-assisted reading produce an **Automatic transcription** until the selected range has actually been checked. Mark uncertain alternatives and unreadable text; do not complete missing letters from memorized scripture or display a translation as the literal readout. A reconstruction, published transcription, model translation and user correction remain separate layers. Region highlighting follows real mapping data; if no precise mapping exists, cite the selected image/page instead of inventing word boxes.

The user can correct the transcription, compare a named published transcription, and then request translation, word research or a search for parallels. Store a correction as a new revision linked to the image and automatic draft. Checking a range records only that review; it does not authenticate the photographed object or certify an interpretation. A possible verse match is shown as a candidate comparison and cannot replace the observed image text. Hebrew/Aramaic, Greek and Quranic Arabic are relevant targets, with correct reading direction; actual support and quality vary by worker, script and image condition. Unsupported or unreadable material stays available for manual study.

Keep original bytes/hash, provenance supplied by the user or online source, crop/rotation as derivatives, selected page/region, worker/model revision and transcription status. Unknown object provenance remains explicit; visual appearance or a successful transcription is not proof of age, authorship or authenticity. The source and hadith policies apply to recognized text as well as imported text.

User uploads are private. Temporary Chat may need bounded private processing files, cleaned with the session/job; an attachment does not become a durable dossier, public cache, export item or later research memory automatically. Explicit dossier saving retains the selected original and transcription revisions. A cloud image-reading action shows which image/region will leave the machine and uses only a selected eligible vision route with the relevant processing choice. Enabling a text-chat provider or remote viewing does not authorize that upload. Local-only mode makes no cloud image calls and cannot silently fall back to another service.

Try the real sequence: image → region → automatic draft → uncertain character → correction → translation or parallel search → saved dossier → reopening. Also try an unsupported script, an unreadable crop, missing region mapping, temporary Chat cleanup and local-only mode without an available worker. These are practical checks, not a claim of universal OCR accuracy.

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

UI localization and model capability are separate properties. An Arabic menu can work while the chosen model's Arabic answers have not been checked; show that distinction without blocking personal use. Try real questions and source lookups in the languages actually used, including mixed-script references. Compare generated translations with named editions and record uncertainty or observed errors. A Dutch/English spot check does not establish French, German or Arabic quality. A specialist can help with a difficult passage; a reviewer panel or fixed multilingual evaluation battery is not required.

## Optional autonomous web research

The assistant can plan queries, search, read pages, compare evidence, and cite relevant external material within a bounded read-only workflow when web research is enabled. The interface exposes a global control and a per-run log. Start disabled until the user enables and configures the provider; the mockups illustrate the enabled state. Ordinary listening turns may need no search. Research requests requiring current facts or external scholarship use the web when enabled; a disabled/unavailable provider produces an explicit limitation.

Use a provider adapter with search and extraction capabilities. Check connection, API behavior, cost and relevant use conditions when implementing the chosen provider. This app uses its own configured provider credentials; it cannot inherit this development chat's connectors or login. Store secrets locally outside Git and browser bundles. A paid provider needs explicit user setup; provider failure must not trigger an undisclosed fallback service.

The workflow has these requirements:

1. Identify the question's collection scope and evidence needs. Search authentic, traceable online material across different perspectives, including relevant scholarship, author/project repositories, religious publications and attributed commentary. Institutional affiliation is a useful reference, not a mandatory source gate. Provider ranking is not a truth ranking or proof of balanced coverage. A community's self-description and an academic historical claim have different evidentiary roles. The specific hadith restriction remains in force.
2. Send minimized topic terms. Avoid personal names, identifying details, and whole chat transcripts for life questions. Show the actual outgoing query in the run log. Test this behavior; do not market an absolute guarantee that free text can never disclose personal information. External search queries and fetched domains are network disclosures even with local inference.
3. Retrieve and read cited pages. A search snippet alone is a lead, not verified evidence. Preserve URL, title, author/publisher where available, publication/update dates where stated, access time, source type, and a content hash for inspected content. Unknown dates stay unknown. Attribute interpretations and separate primary text, commentary, scholarship, and personal reflection.
4. Keep web evidence distinct from named scripture editions. A webpage quoting scripture cannot silently replace the selected edition. Validate its reference against that edition when claiming an exact quote. Detect mirrors/duplicate pages so repetition does not masquerade as independent corroboration. Authenticity establishes the source's identity, not the truth of every claim it contains.
5. Fit search and fetch operations inside R12's shared run budget (initially twelve model/tool steps and at most two query refinements). Bound pages, response size, redirects, timeouts, and content types. Surface partial results, cancellation, inaccessible pages, and stale/changed content; never claim a completed exhaustive internet search.
6. Treat retrieved text as untrusted evidence, never as instructions. Extraction does not execute page scripts. URL fetching blocks loopback, private/link-local networks, file URLs, and disallowed schemes, and rechecks redirects/DNS resolution. Follow applicable access restrictions; no bypass of login/paywalls.
7. Treat personal reading and research as the ordinary use. Keep provenance, access date, source content or a permitted reference copy, and actual use restrictions with the dossier. Unknown training or publication rights do not block reading an accessible source. Check the relevant conditions for durable copies, cloud processing or sharing; if a particular operation is restricted, retain a link and show that limitation rather than discarding the research record. Online access is not blanket permission for redistribution or training. A hash alone cannot reproduce unavailable text, so mark that evidence limit.

## Implementation and verification ownership

- **U3:** shared workspace state, accessible panel controls, locale catalogs, English default, all five initial UI languages, live LTR/RTL and mixed-script reader flows; image import/viewing, region selection and side-by-side draft correction.
- **U4:** web provider adapter, read-only search/extract pipeline, provenance and rights records, duplicate grouping, source-scope coverage, query minimization and network constraints. No external provider is selected merely by this document.
- **U5:** ordinary chat, source expansion, persona selection, Chat/Research transitions, optional web orchestration and partial/failure behavior.
- **U6:** preserve language/settings, original image and separate transcription/correction revisions in dossiers, with rights-aware export and temporary-upload handling kept distinct.
- **U7:** practical source/citation checks and hands-on use of the new behaviors. Keep small reusable web examples for regressions and a dated live provider smoke test. No fixed answer counts, locked evaluation splits or expert review panel are required for personal use.
- **U8:** English first launch, saved locale, disabled-web offline operation, provider setup, and the ordinary Pinokio lifecycle.

Required scenarios include mode switching without losing drafts or changing storage consent; no forced scripture dump in supportive chat; all five locales including translated errors and dialogs; Arabic RTL with English references and Hebrew/Greek passages; stable source IDs after locale changes; keyboard and narrow-screen flows; network-off requests producing no search/fetch or cloud image calls; search-provider failure; snippets unsupported by fetched pages; changed or inaccessible pages; missing dates; injected source instructions; malicious redirects/private-network targets; private details omitted from outgoing queries; unequal source supply; duplicated publishers; religion-specific interpretations properly attributed; criticism evaluated with the same standard across traditions; an unreviewed image transcription remaining distinct from a published edition; and a source-rights restriction blocking snapshot export.

Keep a short record of what actually worked: implemented controls, localized screens, tried conversation languages and a working web connection. Label untried combinations and known limitations honestly. Generated screenshots do not establish working behavior or certify neutrality.
