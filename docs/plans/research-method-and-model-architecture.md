# Evidence method, hybrid models, and moderated discussion

Status: product requirements and architecture proposals, 8 November 2026. No models or API integrations have been run for this project. This document extends the main plan and supersedes its original local-only coordinator assumption and deferral of manuscript viewing. Provider selection remains subject to evaluation and account/region admission.

## One evidence method for all three collections

Apply the same standards to the selected Torah, Bible, and Quran collections. State the exact edition, manuscript witness, translation, and canon/scope. Torah means the selected Torah corpus; do not silently expand it to the entire Tanakh. A Bible collection must state its canon. An ancient manuscript is a textual witness, not automatically an author's original or proof that a statement came directly from a prophet.

For a substantive interpretive answer, produce an inspectable evidence argument:

1. **Question and scope:** what is being asked, which texts and historical period are relevant, and what the proposed answer would actually establish.
2. **Primary text:** retrieve the passage and surrounding literary unit from the named edition. Keep manuscript readings, editorial reconstructions, published translations, and generated translations distinct.
3. **Context within the collection:** seek related passages and counterevidence across the selected collection, not only verses supporting a preferred conclusion. Show relevant changes of speaker, genre, addressee, and textual setting. Whole-collection context is a research obligation, not a claim that every verse was exhaustively inspected on every turn. Record search scope and gaps.
4. **Evidence items:** list E1, E2, E3, etc. Each item records the observation/claim, source and location, date or period where relevant, method, uncertainty, and whether independent corroboration exists. Distinguish directly observed text, a catalog attribution, a scholarly hypothesis, and an inference. Calling something a fact does not establish it.
5. **Historical and linguistic context:** use admitted academic evidence for contemporary word usage, material culture, social setting, genre, and transmission. Separate the date of a physical witness, the proposed date of composition, and the period a narrative describes. Do not infer an ink or composition date from a parchment date alone.
6. **Alternative readings:** explain how plausible readings depend on vocabulary, syntax, translation, textual variant, literary context, historical reconstruction, or theological assumptions. Attribute a position narrowly to its named source, school, or author; do not claim an entire religion speaks with one voice.
7. **Argument and limits:** show which evidence supports or weakens each reading, the assumptions connecting it to the conclusion, and what would change that assessment. Offer the best-supported reading for the stated historical/textual question when warranted, without inventing certainty or a consensus. Historical analysis does not experimentally establish supernatural truth claims.

The UI displays a concise evidence argument, not a fabricated transcript of hidden model reasoning. Use **Evidence / Context / Interpretations / Assessment / Open questions** in Research, with an expandable equivalent in Chat. A comparison table includes reading, supporting evidence, counterevidence, assumptions, source, and uncertainty. Do not assign pseudo-precise confidence percentages without a defined measurement method. A well-established observation and an unsupported assertion need not receive equal credibility merely to appear balanced.

## Primary texts and secondary material

Primary scripture is the starting evidence for textual interpretation. Commentaries and later traditions are not automatically authoritative explanations. Academic scholarship supplies separately attributed linguistic, material, historical, and interpretive evidence. When the user asks why interpretations differ, a documented interpretation can be described as an object of comparison without adopting its religious authority.

For Quran analysis, hadith is excluded from the default corpus, retrieval, and interpretive justification. Tafsir is not a default explanatory authority. The user's only possible hadith exception is individually admitted material with demonstrable direct provenance under an explicit evidence criterion, and then solely as historical context, never as authority interpreting or overriding the Quran. A traditional label such as sahih does not automatically satisfy that admission criterion. No hadith pack is approved by this plan; if the required provenance cannot be established, exclude it. Do not imply that the system can automatically prove exact attribution to Muhammad. A webpage quoting excluded material cannot bypass this policy by laundering it into supposedly primary evidence.

Apply the same distinction between primary text and later interpretive authority to Torah and Bible analysis, including later commentary and tradition. Historical claims about any tradition receive the same evidentiary scrutiny. The app can explain documented interpretive differences without silently changing the configured source policy.

When comparing earlier prophets or revelations, examine relevant passages in each collection and report their own claims, agreements, and differences. A Quran passage about earlier prophets is evidence of the Quran's position, not permission for the app to overwrite a Jewish or Christian text's own context. Do not force the conclusion that every later doctrine or formulation is identical. Do not encode a preferred theological harmonization as religious impartiality.

Design references checked as primary passages on 8 November 2026 include [Quran 2:136](https://quran.com/2/136), [3:3](https://quran.com/3/3), [4:82](https://quran.com/4/82), and [5:48](https://quran.com/5/48). These are research leads about prophets, prior revelation, reflection, and differences. The product's holistic research protocol is an explicit method choice, not a claim that one verse literally specifies this software algorithm. The linked pages' embedded tafsir is not admitted by linking the primary passage, and no translation reuse rights follow from these references.

## Manuscripts in the research workspace

Manuscript viewing is now part of the core Research experience. Provide a **Manuscripts** tab with zoom/pan, folio and recto/verso navigation, image type, institution and shelfmark, dating attribution, attribution/rights notice, and a direct institutional link. Show scholarly transcription and a named translation alongside an image when available and permitted. Mark absent transcription, missing leaves, uncertain readings, corrections, and editorial reconstructions rather than inventing content. Passage-to-folio/region mapping must be evidenced; do not invent an exact image highlight from a modern verse number.

Use a curated institutional/scholarly source register with per-collection admission, not general web-result admission. Hosting alone does not establish scholarly reliability: require accountable provenance, catalog identity, editorial responsibility, and documented methods where relevant. Officially delegated image hosts are acceptable only through a verified institutional link. See the [candidate register and rights checks](../sources/manuscript-register.md).

Prefer IIIF-compatible manifests and image services where supported and permitted; [IIIF Presentation API](https://iiif.io/api/presentation/3.0/) describes structured presentation of digital objects. Access to a manifest does not grant unrestricted reuse rights. Inspect provider metadata, CORS/access behavior, and usage conditions before selecting an implementation. Use authorized remote viewing rather than bundling scans. When integration is restricted, show the catalog record and open the official viewer; do not bypass restrictions. Images must be genuine institutional scans, never AI-generated manuscripts passed off as evidence. OCR/HTR experimentation remains deferred; supplied scholarly transcriptions are a separate layer.

## Hybrid model responsibilities

The proposed product supports local execution and configured cloud coordination. A powerful API model handles conversation, synthesis, tool planning, and weighing interpretations. Local source services own retrieval, editions, citation validation, metadata, and dossiers. Local embedding/reranking and candidate translation workers support the coordinator. A compact local general model remains an offline/private alternative with separately reported capability limits.

| Role | Proposed location | Evidence/quality boundary |
| --- | --- | --- |
| Main conversation/research coordinator | Selected cloud API, or admitted local fallback | No religious truth authority; output must meet the same evidence contract |
| Critical review of a difficult analysis | Optional second model family/provider | Same evidence bundle; disagreement and sources remain visible; agreement is not proof |
| Scripture and manuscript catalog, dossiers | Local metadata/storage; authorized remote scans as needed | Named editions, image provenance, rights-aware storage/export |
| Exact search, embeddings, reranking | Local | Measure retrieval by collection/language; do not substitute ranking for truth |
| Candidate translation workers | Local | Admit each historical-language/direction separately; retain published translation baselines |
| Exact quotations and reference checks | Deterministic local services | Quote bytes/ranges from admitted sources; semantic support is assessed separately |

Candidate local translators already in the main plan include Helsinki-NLP OPUS-MT Bible models for Semitic and Indo-European language groups. The [Semitic model card](https://huggingface.co/Helsinki-NLP/opus-mt-tc-bible-big-sem-deu_eng_nld) lists Biblical Hebrew/Aramaic among its source tags and DE/EN/NL targets; the [Indo-European model card](https://huggingface.co/Helsinki-NLP/opus-mt-tc-bible-big-ine-deu_eng_nld) lists Ancient Greek and Latin. These language tags and Bible training do not establish translation accuracy, superiority over frontier models, or suitability for Quranic Arabic. Compare local candidates against admitted published translations and a cloud-model baseline using the expert-reviewed translation gate. No validated Quranic-Arabic specialist has been established by this planning work. Local workers may use CPU/GPU according to measured runtime; cloud reasoning does not make all translation workers cloud services.

## Provider pool and initial evaluation

The user has API keys; do not request them in chat or commit them. Configure keys through backend-only local settings/secret storage. No credentials have been inspected or configured in this work. Support a provider adapter pool rather than hardcoding one model into every persona. Model identity, provider endpoint, region, API version, decoding settings, and routing policy are part of the evaluated configuration.

The following official catalogs were checked on 8 November 2026. Availability in a catalog is not confirmation of access under the user's account or region, nor a performance endorsement:

| Candidate route | Verified catalog examples / scope |
| --- | --- |
| [Mistral API](https://docs.mistral.ai/models) | Mistral Large 4; also lists hosted Z.ai GLM 5.3. Model developer and serving provider are separate facts. |
| [Alibaba Cloud Model Studio](https://help.aliyun.com/en/model-studio/models) | qwen3.8-max and GLM-5.3 listings; exact regional endpoint/model identifier must be admitted separately. |
| [OpenAI API](https://developers.openai.com/api/docs/models) | Select and pin an available general reasoning model at admission; benchmark with the same evidence and tasks. |
| [Anthropic API](https://platform.claude.com/docs/en/models/overview) | Claude Opus 5.5 / Sonnet 5.5 appear in the current catalog; select by measured task quality, cost, and latency. |
| [MiniMax API](https://platform.minimax.io/docs/guides/text-generation) | MiniMax-M3.1-Flash and MiniMax-M3; task-specific evaluation still required. |
| [OpenRouter](https://openrouter.ai/docs/guides/routing/provider-selection) | Optional gateway, not another model family. Pin/allowlist actual upstream providers, enforce selected data policies, and disable unapproved fallback. |

Start the bakeoff with a small representative development set covering source fidelity, factual grounding, alternative readings, counterevidence, life-question empathy, tool compliance, languages, and cost. Expand finalists to the locked release evaluation; never tune on that locked set. Choose a default coordinator and a reviewer by those results. Do not claim a winner based on vendor benchmarks, model nationality, or fluent theological prose. Do not invoke all providers on every ordinary chat turn.

Cloud coordination is explicitly enabled by the user and visibly identified. Selected conversation context and evidence leave the machine for that run; web-search query minimization does not mean a remote conversation model never sees personal messages. Source licensing must permit the actual external processing. Manuscript images are not sent for vision processing without applicable rights and a selected vision-enabled route. Local-only mode blocks cloud model calls; web and remote manuscript access have separate controls and can also be disabled. Display these independent connection states accurately.

Use separate authorized primary/reviewer routes, context/output limits, token and monetary budgets, timeout/cancel behavior, and usage accounting. Per-run costs must identify estimates versus provider-reported usage. No silent provider changes, cloud fallback, or escalating multi-model loop after failure. Aliases such as latest require resolution/version recording and cannot silently inherit a previous model's evaluation claims. A provider update or routing-policy change invalidates affected claims under R15. A reviewer is a fallible critic, not a second source of historical evidence.

## User-moderated Roundtable

Within Chat, offer **One-to-one** and **Roundtable** as explicit interaction choices. Research can remain open beside either. Do not automatically turn a personal grief conversation into a debate. The human user is moderator; models are labeled AI participants, not actual scholars, clergy, prophets, or representatives of an entire faith.

Configure each participant along three independent axes: **persona** (method/tone), **perspective** (a stated analytical or attributed interpretive lens), and **provider/model** (execution engine). All share the same source policy and impartiality constraints. A textual researcher, historical-context analyst, linguist, comparative scholar, and critical interlocutor are useful roles. Religious perspectives may be examined with explicit attribution, without granting them an override of the primary-text and hadith admission rules.

The moderator can select participants, set the question/scope, ask one or all to respond, approve the next turn, pause/stop, request evidence, challenge a claim, introduce a source through admission checks, or request a synthesis. Start with a bounded proposal of up to four participants and one response each per moderator-requested round, with explicit limits adjustable before the run. No endless autonomous discussion, hidden paid calls, or automatic declaration of a winner.

All participants receive the same versioned evidence dossier. New sources are logged and shared before dependent rebuttals; identify what changed. Each substantive claim links to evidence items; distinguish a participant's hypothesis from an established observation. Maintain agreement/disagreement and unresolved-question records. A requested synthesis preserves disagreements and their reasons, rather than deciding by majority vote. Different prompts on the same base model are not independent experts; different model families also may share biases.

The UI shows participant name, persona, analytical perspective, provider/model, speaking state, citations, and relevant usage. Model-call outputs are ordinary messages, not authentic historical testimony or disclosed hidden reasoning. Queue one speaker by default so the moderator can follow and control the discussion. Parallel independent opening analyses may be an explicit option within the same authorized budget; rebuttals depend on the shared preceding messages and evidence revision.

## Implementation and acceptance additions

- **U1:** provider adapters, capability/region/version admission, backend-only secrets, local/cloud execution controls, budget and cancellation contract; local translation runtime admission remains separate.
- **U2:** institutional manuscript registry, image/transcription/metadata permissions, shelfmark and revision provenance, passage/folio mapping; default exclusion and context-only admission rules for secondary material.
- **U3:** Manuscripts and Interpretations panels, local/remote connection state, source provenance, historical dating distinctions and evidence argument views; genuine scans only after admission.
- **U4:** collection-wide related/counterevidence retrieval, source-policy enforcement before corpus/web evidence enters a bundle, distinct web/manuscript candidates and duplicate detection.
- **U5:** hybrid coordinator/reviewer orchestration, all persona constraints, inspectable evidence argument, alternative-reading comparison, user-moderated Roundtable and bounded speaking queue.
- **U6:** versioned evidence items, interpretation comparisons, participant messages and explicit dossier saving/export within rights constraints.
- **U7:** evaluate coordinator/reviewer pairs and routing separately from translation workers; include manuscript provenance/folio errors, fact-versus-hypothesis confusion, anachronism, cherry-picking, ignored counterevidence, unsupported consensus, forbidden hadith leakage, commentary promoted to authority, theological flattening, provider drift, local-mode egress, budget overruns, moderator control, and majority-vote errors.
- **U8:** verify actual menu startup and provider settings without requiring a cloud key for offline reading; no model or scan download hidden inside app startup.

Beta claims require genuine admitted manuscript-viewing examples from each requested tradition where available, appropriate attribution, accurate evidence-to-reading links, and real UI verification of moderator controls and provider/local boundaries. Restricted or inaccessible collections remain explicitly unavailable or official-link-only. Additional language, manuscript, cloud-routing and Roundtable evaluation workload must be budgeted before those features are released; the original baseline answer counts do not implicitly cover all new combinations.
