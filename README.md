# Euraika Compass

**Explore texts. Understand perspectives. Find direction.**

Euraika Compass is an open-source project for a locally hosted research and life-wisdom companion grounded in the Torah, Bible, and Quran. It combines a text workbench with source-linked conversations about meaning, choices, grief, forgiveness, and other questions of life. Its proposed hybrid architecture pairs optional cloud reasoning models with local source, retrieval, and translation services.

**Project stage: planning and UI concepts. There is no runnable application or Pinokio installer yet.** The screenshots below are AI-generated design mockups, not captures of working software. Their example content and analysis labels are illustrative, not validated research results.

## Project documents

| Document | Purpose |
| --- | --- |
| [vision.md](vision.md) | Product purpose, intended users, principles, priorities, and long-term direction |
| [functional.md](functional.md) | Central functional specification: features, user flows, source rules, orchestration, and failure behavior |
| [technology.md](technology.md) | Recommended stack, local/server database choices, durable source assets, autosave, sharing, maintenance, and backup |
| [architecture.md](architecture.md) | Component boundaries, data model, research execution, model routing, jobs/events, API contracts, trust boundaries, and deployment |
| [design.md](design.md) | Interface structure, Euraika design tokens, Chat/Research/Roundtable interactions, source states, localization, and accessibility |
| [Implementation plan](docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md) | Technical approach, implementation units, evaluation, and release gates |
| [Design concepts](docs/design/README.md) | UI explorations, saved images, prompts, and their limitations |
| [Full-plan review — 8 November 2026](docs/reviews/2026-11-08-full-plan-review.md) | Review coverage, one corrected inconsistency, one proposed routing clarification, and outstanding admission work |

## Planned experience

- Read named original-language editions alongside published translations.
- Use a focused **Chat** view for life questions and a flexible **Research** workspace with tabs, resizable panels, sources, and notes. Switch views without losing the conversation or evidence.
- Ask focused passage questions or broader questions across the three collections.
- Let the assistant search and read additional web sources when web research is enabled, with visible queries, provenance, and citations.
- Open the exact edition and passage behind an answer's citation.
- Inspect translation alternatives and available linguistic annotations.
- View genuine historical manuscript scans from admitted institutional and scholarly collections, including Quran manuscripts, with catalog provenance and separate transcription/translation layers.
- Compare interpretations through primary-text context, historical/linguistic evidence, counterevidence, and explicit limits, using the same method for all three collections.
- Moderate a **Roundtable** of AI personas and analytical perspectives, with a shared evidence dossier and control over speaking turns and synthesis.
- Save research dossiers with source, model, and policy versions.
- Autosave explicitly started research dossiers; retain consulted source images locally when permitted, with deduplication and provenance. Export/import selected dossier revisions with rights-aware inclusion of source files.
- Install and run locally through Pinokio once the application is implemented.

English is the default interface language. The initial localization target includes English, Dutch, Arabic, French, and German, with an extensible language catalog. Interface language, conversation language, and source/translation language are independent settings. Arabic includes right-to-left interface behavior; original Hebrew and Arabic passages retain their own reading direction in every interface language. Language support and model quality require separate validation.

Local-only operation remains available. Cloud reasoning is explicitly configured and sends the selected conversation context and permitted evidence to the selected provider. Web research and remote manuscript viewing have separate controls. Search uses minimized topic terms rather than forwarding whole personal conversations; this differs from context sent to a configured conversation model. Search results supplement admitted editions. See the [interaction/language specification](docs/design/interaction-and-localization.md) and [evidence method, hybrid models, and moderated discussion](docs/plans/research-method-and-model-architecture.md).

Hadith is excluded from default Quran retrieval and interpretive authority. No hadith pack is admitted; the narrow possible exception requires individually established direct provenance and permits context only. Later commentary does not automatically override primary text in any collection. Explaining an attributed interpretation differs from adopting its authority. Genuine manuscript candidates and image-rights limitations are documented in the [source register](docs/sources/manuscript-register.md).

## Five personas, one impartiality policy

| Persona | Purpose |
| --- | --- |
| Supportive conversation partner | Listening and reflection around personal experiences |
| Wisdom guide | Exploring choices, responsibility, forgiveness, and meaning |
| Text researcher | Investigating language, context, and translation |
| Comparative scholar | Comparing sources and attributed interpretations |
| Critical interlocutor | Examining assumptions and arguments respectfully |

Personas change the style and method of a conversation. They do not adopt a preferred religion. The application will distinguish a textual observation, a published translation, a tradition-specific interpretation, and its own suggested reflection.

Impartiality means consistent standards of evidence and respectful treatment. It does not require equal answer lengths, fabricated parallels, or agreement between traditions. We do not claim that any model is entirely free of bias.

## Design concepts

The current direction uses the Euraika brand palette: navy `#001C3A`, secondary blue `#003369`, and gold `#F4A616`, with light reading surfaces. These colors were checked against the [Euraika website](https://www.euraika.net/) on 8 November 2026. Collections receive equal visual prominence. The English concepts below replace the earlier petrol/turquoise direction.

### Conversations and life questions

![English Chat design concept in Euraika blue and gold](docs/design/compass-chat-v4.png)

### Research, original texts, and translations

![English Research design concept in Euraika blue and gold](docs/design/compass-research-v4.png)

### Theological research and interpretation

![Theological interpretation comparison with evidence and open questions](docs/design/compass-theology-research-v5.png)

### User-moderated Roundtable

![Theological Roundtable with shared evidence and moderator controls](docs/design/compass-theology-roundtable-v5.png)

See also the [orchestrator role-allocation concept](docs/design/compass-orchestrator-routing-v5.png). It shows demo connections and provisional assignments only, not actual account access or evaluated model rankings.

See [design notes and generation prompts](docs/design/README.md) for the concepts' scope and limitations.

## Implementation plan

Start with [functional.md](functional.md), the central functional specification for the agreed product scope, user flows, source and interpretation rules, failure behavior, and remaining admission decisions. The orchestrator allocates roles only among user-configured, enabled and eligible models; evaluated role fit, capabilities, data policy and budget guide automatic assignments, while manual overrides and pinned roles remain available.

The [detailed implementation plan](docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md) is written in Dutch. It defines product requirements, candidate models, source packs, eight implementation units, evaluation datasets, and proposed release gates.

The planned stack is React/TypeScript with Vite, Python/FastAPI, SQLAlchemy/Alembic, PostgreSQL full-text search and pgvector, managed local model workers, and backend cloud-provider adapters. PostgreSQL is the primary database for both local and future server deployments. The candidate model pool includes Mistral, Alibaba Cloud/Qwen/GLM, OpenAI, Anthropic, MiniMax, and optionally OpenRouter as a gateway. Local Qwen3.5 remains a coordinator option; embedding, reranking, and historical-language translation candidates are evaluated separately. No provider/model has been selected as a validated winner. API keys belong in backend-only local configuration, never this repository.

The [storage architecture](technology.md) keeps large source objects outside the PostgreSQL database and retains permitted cited objects across cache cleanup. A later opt-in sharing service reuses the PostgreSQL data layer with private object storage. Dossier export/import is the first sharing path, with no public service or cloud upload required. PostgreSQL and pgvector installation/lifecycle on Windows must be proven as part of Pinokio admission; there is no working installation yet. Neither cache permission nor private-study access automatically permits redistribution.

## Sources and licensing boundaries

The repository initially contains documentation and generated UI concepts. It does not include model weights, scripture corpora, third-party translations, or linguistic datasets.

Those materials retain their own licenses and conditions. Future source packs must record the edition, origin, attribution, coverage, integrity hash, and separate permissions for display, indexing, export, and training. An open-source application license does not grant rights to third-party data or models.

The plan excludes HY-MT1.5 from the standard Belgian/EU deployment because its published community license excludes the EU. Other models and sources are also subject to admission checks before use.

## Evaluation approach

- Test retrieval separately from interpretation and full application behavior.
- Use fixed evidence bundles to test persona, source-order, and irrelevant identity effects.
- Measure factual and citation quality as well as consistent treatment across traditions.
- Include missing sources, contested interpretations, fabricated citations, and attempts to induce religious preference.
- Test web-source provenance, search bias, unavailable pages, source injection, query minimization, and the disabled-network path.
- Verify localized flows and mixed-direction text in a real browser; assess answer quality separately for each supported conversation language.
- Verify historical evidence arguments, manuscript provenance, alternative readings and counterevidence, source-policy enforcement, moderator control, and bounded cloud routing/costs.
- Use blinded human assessment alongside deterministic checks and model-assisted triage.
- Report sample sizes, uncertainty, and outstanding failures; never advertise a proof of perfect neutrality.

See the plan's Verification Contract for dataset sizes, human-review workload, and provisional thresholds.

## Contributing

Contributions to the design, implementation plan, source provenance, linguistic evaluation, and impartiality tests are welcome. Start with a focused issue describing the problem and the relevant plan requirement. Do not contribute private conversations, credentials, model weights, or texts without documented redistribution rights.

Please keep discussion respectful toward people of every religion and none. Preserve meaningful disagreements and support factual corrections with sources.

## License

Project-owned materials are licensed under [Apache License 2.0](LICENSE), except where an individual file explicitly states otherwise. Third-party models, datasets, translations, and source texts are not relicensed by this repository.

Copyright 2026 Euraika Labs.
