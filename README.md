# Euraika Compass

**Explore texts. Compare interpretations. Follow the evidence.**

Euraika Compass is an open-source, locally hosted tool for **personal, neutral theological research** into the Torah, Bible, and Quran. It helps you inspect original texts and manuscripts, compare translations and interpretations, examine historical context and counterevidence, and keep your own research dossiers. You remain the researcher and moderator; AI helps find sources and test arguments without adopting a religious conclusion.

The Research workspace is central. A connected Chat view also supports conversations about meaning, choices, grief, forgiveness, and other life questions. Optional cloud reasoning models work alongside local source, retrieval, and translation services. Authentic, traceable material available online can be used for personal research; institutional publication is not an exclusive admission rule. Practical source and usability checks guide development.

**Project stage: planning and UI concepts. There is no runnable application or Pinokio installer yet.** The screenshots below are AI-generated design mockups, not captures of working software. Their example content and analysis labels are illustrative, not validated research results.

## Project documents

| Document | Purpose |
| --- | --- |
| [vision.md](vision.md) | Product purpose, intended users, principles, priorities, and long-term direction |
| [functional.md](functional.md) | Central functional specification: features, user flows, source rules, orchestration, and failure behavior |
| [technology.md](technology.md) | Recommended stack, local/server database choices, durable source assets, autosave, sharing, maintenance, and backup |
| [architecture.md](architecture.md) | Component boundaries, data model, research execution, model routing, jobs/events, API contracts, trust boundaries, and deployment |
| [design.md](design.md) | Interface structure, Euraika design tokens, Chat/Research/Roundtable interactions, source states, localization, and accessibility |
| [Implementation plan](docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md) | Technical approach, implementation units, and practical checks for personal use |
| [Design concepts](docs/design/README.md) | UI explorations, saved images, prompts, and their limitations |
| [Full-plan review — 8 November 2026](docs/reviews/2026-11-08-full-plan-review.md) | Historical review and two resolved inconsistencies; its former evaluation assumptions are superseded by the personal-use scope |

## Planned experience

- Read named original-language editions alongside published translations.
- Use a focused **Chat** view for life questions and a flexible **Research** workspace with tabs, resizable panels, sources, and notes. Switch views without losing the conversation or evidence.
- Ask focused passage questions or broader questions across the three collections.
- Let the assistant search and read additional web sources when web research is enabled, with visible queries, provenance, and citations.
- Open the exact edition and passage behind an answer's citation.
- Inspect translation alternatives and available linguistic annotations.
- View genuine historical manuscript scans, including Quran manuscripts, with traceable provenance and separate transcription/translation layers. Original collection catalogs are useful anchors; verified authentic copies from other online hosts are also usable.
- Compare interpretations through primary-text context, historical/linguistic evidence, counterevidence, and explicit limits, using the same method for all three collections.
- Moderate a **Roundtable** of AI personas and analytical perspectives, with a shared evidence dossier and control over speaking turns and synthesis.
- Save research dossiers with source, model, and policy versions.
- Autosave explicitly started research dossiers; retain consulted source images locally when permitted, with deduplication and provenance. Export/import selected dossier revisions with rights-aware inclusion of source files.
- Install and run locally through Pinokio once the application is implemented.

English is the default interface language. The initial localization target includes English, Dutch, Arabic, French, and German, with an extensible language catalog. Interface language, conversation language, and source/translation language are independent settings. Arabic includes right-to-left interface behavior; original Hebrew and Arabic passages retain their own reading direction in every interface language. Practical examples check each used language; untested output and translation limits remain visible.

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

Start with [functional.md](functional.md), the central specification for personal theological research, user flows, source and interpretation rules, and failure behavior. The orchestrator allocates roles only among user-configured, enabled and eligible models. Task capabilities, user choices, data settings and budget guide assignments; small practical comparisons can inform role fit without a mandatory benchmark. Manual overrides and pinned roles remain available. A failed pinned role stays paused until you explicitly unpin or reassign it.

The [detailed implementation plan](docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md) is written in Dutch. It defines product requirements, candidate models, starter sources, eight implementation units, and practical source, interpretation, UI and persistence checks. There is no fixed test volume, required expert panel or statistical certification program for personal use.

The planned stack is React/TypeScript with Vite, Python/FastAPI, SQLAlchemy/Alembic, PostgreSQL full-text search and pgvector, managed local model workers, and backend cloud-provider adapters. PostgreSQL is the primary database for both local and future server deployments. The candidate model pool includes Mistral, Alibaba Cloud/Qwen/GLM, OpenAI, Anthropic, MiniMax, and optionally OpenRouter as a gateway. Local Qwen3.5 remains a coordinator option; embedding, reranking, and historical-language translation candidates are evaluated separately. No provider/model has been selected as a validated winner. API keys belong in backend-only local configuration, never this repository.

The [storage architecture](technology.md) keeps large source objects outside the PostgreSQL database and retains permitted cited objects across cache cleanup. A later opt-in sharing service reuses the PostgreSQL data layer with private object storage. Dossier export/import is the first sharing path, with no public service or cloud upload required. PostgreSQL and pgvector installation/lifecycle on Windows must be proven as part of Pinokio admission; there is no working installation yet. Neither cache permission nor private-study access automatically permits redistribution.

## Sources and licensing boundaries

The repository contains documentation and generated UI concepts. It does not include model weights, scripture corpora, third-party translations, or linguistic datasets. Open-source code and documentation do not make your personal dossiers or downloaded research material public.

Online sources may include primary texts, manuscript scans, articles, author archives, project repositories and documented interpretations. Record identity, origin, edition and source type. Institutional and academic catalogs are preferred provenance references where available, not the only permitted hosts. Authenticity means the material is genuine and traceable; it does not establish the truth of every claim or give an interpretation automatic authority.

Personal consultation is separate from permanent copying, external model processing, redistribution and training. Keep actual access and use constraints with each source; unknown publication or training rights do not automatically block personal reading. Use the source link where a particular operation is restricted, and do not bypass access controls. Files included in a shared dossier or public repository need their own applicable reuse permission. Source packs record edition, attribution, coverage and integrity alongside those constraints. The application license does not relicense third-party material.

The plan excludes HY-MT1.5 from the standard Belgian/EU deployment because its published community license excludes the EU. Other models and sources are also subject to admission checks before use.

## Practical quality checks

- Open citations and compare literal quotes against the named edition.
- Try a small, growing set of your own research questions, including disputed readings and counterevidence.
- Check that observations, hypotheses, attributed interpretations and personal reflections remain distinct.
- Repeat a question with another persona or source order when investigating possible religious preference.
- Try missing or unreachable sources, failed model calls, network-off settings and the pinned-role rule.
- Compare a few model translations with published translations and available language evidence; keep untested quality visible.
- Follow a real question through Research, the source/manuscript viewer, a saved dossier, restart and reopening. Check the used languages, RTL and keyboard controls.
- Record concrete problems and repeat affected examples after a fix. A second model or specialist can help, but no panel approval is required to use the tool.

See the plan's Verification Contract for V1-V9. These checks support your investigation; they do not certify a theological conclusion or prove perfect neutrality.

## Contributing

Contributions to the design, implementation plan, source provenance, linguistic evaluation, and impartiality tests are welcome. Start with a focused issue describing the problem and the relevant plan requirement. Do not contribute private conversations, credentials, model weights, or texts without documented redistribution rights.

Please keep discussion respectful toward people of every religion and none. Preserve meaningful disagreements and support factual corrections with sources.

## License

Project-owned materials are licensed under [Apache License 2.0](LICENSE), except where an individual file explicitly states otherwise. Third-party models, datasets, translations, and source texts are not relicensed by this repository.

Copyright 2026 Euraika Labs.
