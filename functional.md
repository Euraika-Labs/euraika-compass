# Euraika Compass — Functionele specificatie

Status: functionele baseline van 8 november 2026. Dit is het centrale functionele document voor Euraika Compass. Het beschrijft wat gebruikers kunnen doen en welk waarneembaar gedrag de app moet leveren. De software is nog niet gebouwd; providerkoppelingen, modelkwaliteit en wetenschappelijke resultaten zijn niet door dit document bewezen.

[vision.md](vision.md) beschrijft het doel, de doelgroep en de richting van het product. Dit document vertaalt die visie naar functioneel gedrag; de technische plannen werken de bouw en verificatie uit.

Dit document is leidend voor functioneel gedrag. Het [implementatieplan R1-R25](docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md), de [interactie- en taalspecificatie](docs/design/interaction-and-localization.md), [bewijsmethode en modelarchitectuur](docs/plans/research-method-and-model-architecture.md) en het [manuscriptregister](docs/sources/manuscript-register.md) werken dit uit. Technische keuzes mogen deze functionele regels niet stilzwijgend veranderen. Nieuwe gebruikersbeslissingen worden hier verwerkt en in de relevante uitwerking doorgevoerd.

## Doel en uitgangspunten

Euraika Compass verbindt studie van Thora, Bijbel en Koran aan gesprekken over levensvragen. De gebruiker kan zelf teksten en manuscripten inspecteren, interpretaties onderzoeken en AI-deelnemers onder eigen regie laten discussiëren. De app is opensource, draait als lokaal gehoste webapp onder Pinokio en kan expliciet gekozen cloudmodellen gebruiken.

Geen religie krijgt een eigen voorkeurspositie. Onpartijdigheid betekent gelijke bewijsregels, zorgvuldigheid en respect; niet evenveel woorden, geforceerde overeenstemming of evenveel geloofwaardigheid voor elke bewering. Het systeem toont verschillen en onzekerheden en claimt geen absolute afwezigheid van bias.

De app kan religieuze en filosofische reflectie op brede levensvragen bieden, maar leidt actuele feiten of medische, juridische en andere specialistische claims niet uitsluitend uit schriftteksten af. Zij presenteert zich niet als behandelaar, bevoegde adviseur of religieuze autoriteit. Het onderzoeksbereik en ontbrekende expertise blijven herkenbaar.

Thora, Bijbel en Koran behouden hun eigen corpus-, editie- en interpretatiecontext. De gekozen Bijbelcanon is zichtbaar; Thora wordt niet stilzwijgend uitgebreid naar de hele Tanakh. Overlappende tekst in meerdere collecties telt niet als onafhankelijk dubbel bewijs. Een bewering van één boek over een ander is een toegeschreven tekstgegeven, geen toestemming voor het systeem om dat andere boek te overschrijven.

## Functies en waarneembaar gedrag

| Onderdeel | Wat de gebruiker kan en wat de app moet doen | Contract |
| --- | --- | --- |
| Gewone Chat | Levensvragen bespreken met vijf kiesbare persona's; gepaste reactie en vervolgvraag; relevante bronnen uitklappen; geen automatisch debat of verplichte citatendump | R2-R6, R17 |
| Research | Tabbladen en aanpasbare panelen met teksten, vertalingen, bronnen, woordonderzoek, bewijs, context, interpretaties en notities; vanuit Chat openen en terugkeren zonder context/conceptbericht te verliezen | R1, R7-R9, R17 |
| Tekstbibliotheek | Exacte editie, taal en corpus-/canonbereik kiezen; vers en omliggende passage openen; oorspronkelijke tekst, gepubliceerde vertaling en modelvertaling onderscheiden; ontbrekende dekking zichtbaar houden | R1, R7-R10 |
| Manuscripten | Echte scans van toegelaten institutionele/wetenschappelijke collecties, ook Koranhandschriften, met zoom/folio/herkomst; afzonderlijke transcriptie/vertaling; anders officiële viewerlink bij beperkingen | R21 |
| Onderzoeksmethode | Voor iedere collectie dezelfde tekstuele/historische/taalkundige bewijsregels; passagecontext, verwante passages en tegenbewijs; E1/E2/E3 met bron, methode, onzekerheid en onderscheid tussen observatie, hypothese en conclusie | R4-R5, R8-R9, R22 |
| Interpretaties | Lezingen vergelijken via woordgebruik, vertaling, tekstvarianten, genre, tijd/context en aannames; steun- en tegenbewijs uitleggen; beter onderbouwde lezing waar mogelijk, met behouden onzekerheid en werkelijke verschillen | R23 |
| Secundaire bronnen | Commentaar en overlevering krijgen geen automatische interpretatieve autoriteit; hadith standaard uitgesloten, geen pakket toegelaten; beperkte mogelijke uitzondering uitsluitend individueel aantoonbare directe herkomst als context; geen omweg via webcitaten | R10, R22-R23 |
| Webonderzoek | Alleen indien ingeschakeld: zelfstandig zoekvragen maken, pagina's lezen en aanvullende bronnen vergelijken; inspecteerbare query/herkomst/datum/toegang; mislukte of ongelezen pagina niet als geverifieerd bewijs opvoeren | R9, R12-R13, R19 |
| Hybride modellen | Gekozen cloudmodel voor gesprek/onderzoek; eventueel tweede familie als criticus; lokale zoek-/taalworkers en offline algemene modeloptie; dezelfde bewijsregels voor iedere route | R13, R15, R24 |
| Orchestrator | Persona-/perspectiefrollen automatisch verdelen uitsluitend over geconfigureerde, ingeschakelde en geschikte modellen; rekening houden met mogelijkheden, evaluaties, taal, gegevensbeleid en budget; gebruiker kan inspecteren, wijzigen en vastzetten | R24-R25 en aanvullende allocatorregels |
| Roundtable | Expliciet meerdere AI-deelnemers in één chat; gedeeld bewijsdossier; gebruiker bepaalt sprekers, rondes, pauze, bronvragen en samenvatting; geen winnaar op basis van stemmen of modelaantal | R25 |
| Meertaligheid | Engels bij eerste start, EN/NL/AR/FR/DE als eerste UI-talen en uitbreidbare catalogi; UI-, gesprek- en brontaal onafhankelijk; Arabische UI RTL, tekstblokken met eigen richting | R18 |
| Dossiers | Tijdelijke gesprekken alleen bewust opslaan; antwoord, bewijs, notities, bron/model/policyversies en discussie kunnen heropenen; heranalyse bewaart oude versie; export volgt bronrechten | R13-R14 |
| Verbindingen en kosten | Cloudmodellen, web en remote scans afzonderlijk herkenbaar; keys alleen lokaal/backend; geen stille activering of ongeautoriseerde fallback; budgetten, annulering en gedeeltelijke resultaten zichtbaar | R11-R13, R19, R24-R25 |
| Installatie en beheer | Pinokio Install / Start / Stop / Open Web UI, model-/bronbeheer, update/herstel met behoud van data; geen ongevraagde zware downloads | R11-R12, R14-R15 |
| Vormgeving | Euraika-blauw/goudgeel, gelijke visuele behandeling van collecties, toetsenbordbediening, leesbaar contrast en bruikbare smalle schermen | R17-R18, R20 |

## Persona, perspectief en model

Deze instellingen zijn onafhankelijk. Een **persona** bepaalt gespreksstijl en methode. Een **perspectief** bepaalt de benoemde onderzoekshoek. Het **model** is de gekoppelde uitvoerder; het is geen religieuze of wetenschappelijke autoriteit.

| Persona | Gewenst gedrag |
| --- | --- |
| Betrokken gesprekspartner | Luisteren en reflecteren bij verlies, twijfel en andere persoonlijke ervaringen, zonder preek of ongegronde zekerheid |
| Wijsheidsbegeleider | Keuzes, verantwoordelijkheid, vergeving en betekenis verkennen met respect voor autonomie |
| Tekstonderzoeker | Editie, taal, context, vertaling en tekstvarianten zorgvuldig onderzoeken |
| Vergelijkende geleerde | Overeenkomsten, verschillen, interpretaties en corpusdekking zichtbaar vergelijken |
| Kritische gesprekspartner | Aannames en argumenten met dezelfde zorgvuldigheid onderzoeken en respectvol tegenspreken |

Een historische of taalkundige onderzoekshoek kan als perspectief/taakrol worden ingesteld. Een gevraagde religieuze lezing wordt nauwkeurig toegeschreven; geen AI-deelnemer spreekt namens een gehele religie. Persona's kunnen het bronbeleid, de routeringsgrenzen en de gedeelde bewijsregels niet veranderen. Wisselen behoudt context en start geen ander gesprek. De app verandert niet ongevraagd van een betrokken gesprek in een confronterend debat.

## Weergaven en bediening

**Chat** is de gewone leesbare gesprekservaring. Broninformatie blijft compact en uitklapbaar. Bij een persoonlijke vraag begint de assistent passend bij de situatie en kan hij een relevante vervolgvraag stellen. Schriftclaims krijgen hun bron; menselijke erkenning hoeft niet geforceerd met drie citaten te worden gevuld. Geen bewering over Gods bedoelingen of het lot van een overleden persoon als vastgesteld feit.

**Research** biedt bibliotheek-/webnavigatie, documenttabbladen, brontekst en vertalingen, gesprek, woordonderzoek, manuscriptweergave, bewijsitems, context, interpretatievergelijking, notities en onderzoekslog. Panelen zijn aanpasbaar en inklapbaar. Toetsenbordgebruik en smalle schermen blijven bruikbaar. Een bronkoppeling opent de juiste editie/passage, of een duidelijk als onzeker gemarkeerde koppeling.

**Open in Research** en de **Chat / Research**-wissel behouden gesprek, persona, scope, bronselectie, conceptbericht en relevante leespositie. Wisselen veroorzaakt geen nieuwe analyse, stilzwijgende opslag of extra modelkosten. Binnen Chat kiest de gebruiker expliciet **One-to-one** of **Roundtable**.

De vormgeving gebruikt Euraika Blue `#001C3A`, aanvullend blauw `#003369`, Gold `#F4A616` en Charcoal `#1E2D39`, met lichte leesvlakken. Donkere tekst/iconen op goud, zichtbare focus en contrast worden daadwerkelijk getest. Religies krijgen geen waarderingskleur of rangorde.

## Bronnen, manuscripten en onderzoeksargument

Een bronvermelding toont het bronsoort, de exacte editie/versie, taal, auteur/vertaler indien bekend en een inspecteerbare locatie. Originele tekst, tekstkritische reconstructie, wetenschappelijke transcriptie, gepubliceerde vertaling, modelvertaling en annotatie zijn aparte lagen. Letterlijke citaten worden vanuit de toegelaten bron ingevoegd en gecontroleerd. Een geldig citaat bewijst nog niet dat een interpretatie er inhoudelijk door ondersteund wordt.

Voor manuscripten gebruikt de app een gecontroleerd register van officiële bibliotheek-, universiteits-, museum-, archief- of wetenschappelijke projectcollecties, inclusief islamitische Koranhandschriften. Vereist: verantwoordelijke instelling/redactie, catalogusrecord, signatuur, herkomst en passende gebruiksrechten. Alleen een domeinnaam of institutioneel logo is onvoldoende. Toegestane gedelegeerde beeldhosts moeten via de instelling zijn geverifieerd.

De viewer biedt zoom, folio-/paginanavigatie en recto/verso waar relevant, met beschikbare transcriptie/vertaling naast de scan. Datering heeft een bron, methode en onzekerheid; datum van materiaal, afschrift en veronderstelde compositie worden niet gelijkgesteld. Een handschrift is niet automatisch het auteursexemplaar. Ontbrekende bladen, onzekere letters en reconstructies blijven zichtbaar. Geen verzonnen vers-folio-/woordkoppelingen en geen gegenereerde manuscriptbeelden als historische bron.

Beeldtoegang, lokaal bewaren, indexeren, extern modelgebruik, export en training hebben afzonderlijke rechten. Bij beperkte toegang blijft een catalogusrecord met officiële viewerlink beschikbaar. De app omzeilt geen blokkades. Manuscripten zijn niet automatisch offline beschikbaar omdat de tekstbibliotheek lokaal staat.

Voor inhoudelijke uitleg volgt het systeem dezelfde methode bij alle collecties:

1. Formuleer vraag, scope en het soort conclusie dat onderzocht wordt.
2. Inspecteer de primaire passage en omliggende literaire context in een benoemde editie.
3. Zoek relevante passages én tegenbewijs elders in de gekozen collectie; registreer zoekbereik en gaten. Claim geen volledige inspectie van een heel boek wanneer die niet is uitgevoerd.
4. Maak bewijsitems E1/E2/E3 met bewering/waarneming, bron en locatie, tijd/context, methode en onzekerheid. Onderscheid observatie, toegeschreven hypothese en gevolgtrekking.
5. Onderzoek historische, taalkundige en materiële context met toegelaten wetenschappelijke bronnen. Vermijd anachronisme en ongefundeerde daterings- of auteursclaims.
6. Vergelijk relevante lezingen met woordgebruik, grammatica, vertaling, tekstvarianten, genre, aannames, steun- en tegenbewijs.
7. Geef een onderbouwde beoordeling voor de gestelde vraag en benoem onzekerheden, alternatieven en wat de conclusie zou kunnen veranderen.

De app kan uitleggen waarom een lezing sterker wordt ondersteund, maar doet niet alsof wetenschap voor iedere passage één definitief antwoord oplevert of bovennatuurlijke waarheid kan vaststellen. Zij toont een beknopte controleerbare argumentatie, geen verzonnen intern redeneertranscript of ongemeten zekerheidspercentage.

Commentaren en latere overleveringen krijgen geen automatische uitlegautoriteit. Een gedocumenteerde interpretatie mag als onderwerp van vergelijking worden beschreven zonder haar als waarheid over te nemen. Dit onderscheid geldt voor alle drie collecties.

Hadith blijft uitgesloten van de standaardcorpusbank en interpretatieve rechtvaardiging. Geen hadithpakket is toegelaten. De enige mogelijke uitzondering is afzonderlijk materiaal waarvan rechtstreekse herkomst volgens expliciet vastgestelde bewijseisen aantoonbaar is, en dan uitsluitend als historische context. Een traditionele classificatie zoals sahih voldoet niet automatisch; bij ontbrekend bewijs blijft het materiaal uitgesloten. Een webpagina of andere deelnemer kan deze regel niet omzeilen. De app belooft niet automatisch historische directe herkomst te kunnen bewijzen.

## Webonderzoek

De gebruiker configureert en activeert webonderzoek afzonderlijk. Dan kan de app binnen een begrensde run zelfstandig zoektermen maken, pagina's lezen en aanvullende bronnen beoordelen. Alleen een snippet is geen gecontroleerde bron. Zoektermen, URL, titel, auteur/uitgever indien bekend, opgegeven publicatie-/wijzigingsdatum, raadpleegtijd en beperkingen zijn inspecteerbaar. Onbekende gegevens blijven onbekend.

Persoonlijke vragen gebruiken geminimaliseerde onderwerptermen in plaats van volledige gesprekken of onnodige identificerende details. De app toont werkelijke uitgaande queries; zij belooft geen onfeilbare automatische anonimisering. Broninstructies zijn gegevens, geen opdrachten aan het systeem. Webbewijs blijft gescheiden van toegelaten tekstedities en voldoet aan hetzelfde bronbeleid. Mislukte toegang of ontbrekende dekking levert een zichtbare beperking op. Web-uit veroorzaakt nul zoek-/fetchaanroepen.

## Modellen, verbindingen en rolverdeling

Het algemene LLM kan de orchestrator zijn voor gesprek, onderzoek en rolverdeling. Cloudkandidaten omvatten de door de gebruiker genoemde providers Mistral, Alibaba Cloud voor onder meer Qwen/GLM, OpenAI, Anthropic en MiniMax; OpenRouter is een optionele gateway naar een concrete upstream-provider. Welke routes als eerste worden gebouwd en vrijgegeven volgt hun toelating. Lokale embeddings, reranking, citaatcontrole en kandidaat-vertaalworkers blijven afzonderlijke hulpmiddelen. Een lokale algemene modelroute blijft mogelijk voor offline/private gebruik met getoonde beperkingen.

**Alleen gekoppelde en ingeschakelde modellen zijn selecteerbaar.** De backend geeft de orchestrator een gefilterde lijst en controleert iedere gekozen route opnieuw. Verbinding, modelbeschikbaarheid binnen account/regio, mogelijkheden, gegevensbeleid, bronrechten, evaluatiestatus en budget bepalen toelating. Een model uit een algemene catalogus of een suggestie van een deelnemer is geen geldige verbinding. De orchestrator zelf moet eveneens een toegelaten route gebruiken.

Bij automatische rolverdeling kiest de orchestrator uit die lijst op basis van taak, persona/perspectief, taal, beoordeelde geschiktheid en kosten-/latencyvoorkeuren. Zonder tests blijft de match voorlopig; de app claimt geen bewezen beste model. De gebruiker kan de toewijzing inspecteren, wijzigen of vastzetten. Meerdere rollen mogen hetzelfde model gebruiken; dat levert geen onafhankelijke experts op.

Provider/model/versie, opdracht, bewijsversie, toewijzingswijzigingen en beknopte selectiegrond zijn zichtbaar. Keys blijven buiten prompts, frontendbundels, logs, exports en Git. Onbekende endpoints of door modellen verzonnen route-IDs worden geweigerd. Een ongeconfigureerde service wordt nooit automatisch aangesloten.

Bij uitval pauzeert de rol, tenzij vooraf toegestane fallback een andere geschikte ingeschakelde route toestaat. Die wijziging wordt zichtbaar en een vastgezette rol wordt niet stilzwijgend verplaatst. Zonder geschikte route volgt geen verzonnen antwoord. Uitschakelen verhindert volgende calls; annuleren kan reeds verzonden gegevens niet terughalen.

Cloudgebruik is expliciet ingesteld; geselecteerde gesprekscontext en toegestaan bewijs gaan dan naar de gekozen provider. Lokale modus blokkeert cloudmodelcalls. Webzoeken en remote manuscriptbeelden hebben eigen instellingen; lokale verwerking betekent niet automatisch dat deze andere verbindingen ook uitstaan. De gebruiker ziet dit onderscheid. Budgetten begrenzen tokens, uitgaande opdrachten en kosten; schattingen en werkelijk gerapporteerd verbruik blijven onderscheiden.

Lokale vertalers worden per oude taal en richting toegelaten op basis van bronkundige beoordeling. Ondersteuning van een taalcode of modern Arabisch bewijst geen kwaliteit op Bijbels Hebreeuws, Oudgrieks of Koranisch Arabisch. Gepubliceerde toegelaten vertalingen blijven controlebasis. Ontbrekende specialistische ondersteuning wordt gemeld.

## Roundtable en menselijke moderatie

De gebruiker bepaalt onderwerp, scope, deelnemers, perspectieven, beschikbare modellen en budget. Een instelbare eerste configuratie is maximaal vier deelnemers met één beurt per aangevraagde ronde. De gebruiker geeft één deelnemer het woord of vraagt een ronde aan, pauzeert, stelt bronvragen, laat reageren, vraagt een synthese of beëindigt het gesprek. De orchestrator verdeelt rollen; hij neemt het modereren niet over.

Alle deelnemers zien hetzelfde gedeelde dossier met vaste bewijsversies. Nieuwe bronnen worden gecontroleerd, vastgelegd en gedeeld voordat afhankelijke reacties volgen. Per deelnemer zijn persona, perspectief, model/provider, spreekstatus en bronkoppelingen herkenbaar. Het zijn gelabelde AI-deelnemers, geen echte wetenschappers, geestelijken of historische personen.

Een synthese bewaart overeenkomsten, verschillen, tegenbewijs en open vragen met hun redenen. Geen meerderheid-als-waarheid, automatisch uitgeroepen winnaar of eindeloze autonome discussie. Meerdere providers of persona's vervangen geen bronbewijs en garanderen geen onafhankelijkheid of onpartijdigheid. De gewone chat wordt niet zonder gebruikerskeuze een debat.

## Talen, dossiers en beheer

De UI start in het Engels. Eerste lokalisatiedoelen zijn Engels, Nederlands, Arabisch, Frans en Duits, met uitbreidbare berichtcatalogi. De gekozen UI-taal wordt bewaard, onafhankelijk van gesprekstaal en brontaal/vertaling. Taalkeuze vertaalt of overschrijft oudere berichten niet automatisch. Persona-omschrijvingen, foutmeldingen, lege toestanden en toegankelijkheidsnamen worden mee gelokaliseerd.

Arabische UI gebruikt RTL. Arabische/Hebreeuwse passages en LTR-vertalingen behouden hun eigen richting in ieder scherm. Gemengde referenties, cijfers, URL's, diakritiek, selectie en kopiëren worden getest. Een vertaald menu is geen bewijs van antwoord- of vertaalkwaliteit in die taal; capability-/evaluatiebeperkingen blijven zichtbaar.

Gewone gesprekken zijn tijdelijk. Bewust bewaren maakt een dossier met antwoord/discussie, eigen notities, bewijsitems, bronverwijzingen en relevante bron-, model-, policy- en zoekversies. Geschiedenis toont bewust bewaarde gesprekken. Geen impliciet achtergrondgeheugen tussen gesprekken en geen automatische inzet van persoonlijke vragen als trainings- of testdata. Heranalyse maakt een nieuwe gekoppelde versie. Export bewaart bronrechten en kan verwijzingen tonen wanneer volledige tekst/beeld niet geëxporteerd mag worden.

Pinokio verzorgt installeren, starten, stoppen en Open Web UI. De gebruiker beheert bronnen/modellen/providerkoppelingen met zichtbare voorwaarden, omvang en status. Geen stilzwijgende omvangrijke downloads. Stop en annulering beëindigen betrokken taken; update/herstel bewaren bronnen, modellen, dossiers en instellingen. Lezen van reeds aanwezige toegelaten teksten vereist geen cloudkey.

De server luistert standaard alleen lokaal. Geen ongevraagde LAN-toegang, prompttelemetrie of overdracht van volledige gesprekken aan zoekproviders. Het gekozen cloudmodel ontvangt wel de voor die verwerking geselecteerde context; de UI presenteert dat niet als volledig lokale verwerking.

## Kernroutes

1. **Levensvraag:** Chat → persona → gesprek → optioneel bronnen openen → eventueel verder in Research → alleen op verzoek bewaren.
2. **Theologische kwestie:** vraag en scope → passages/context en verwante passages/tegenbewijs → historische/taalkundige bewijsitems → alternatieve interpretaties → argument en beperkingen → dossier.
3. **Manuscript:** toegelaten catalogusrecord → scan/folio met herkomst en rechten → beschikbare transcriptie/vertaling → alleen onderbouwde passagekoppeling; beperkingen geven een expliciete melding of officiële link.
4. **Roundtable:** deelnemers/perspectieven kiezen → orchestrator filtert geschikte ingeschakelde koppelingen → toewijzingen inspecteren/pinnen → moderator vraagt beurt/ronde → bronnen en bezwaren delen → moderator vraagt synthese of stopt.
5. **Beheer:** bron/model/provider en taal instellen → rechten, mogelijkheden en omvang controleren → expliciet downloaden/activeren → gewone start; geen key nodig om beschikbare lokale teksten te lezen.

## Fouten en beperkingen zijn functioneel gedrag

- Geen geschikt gekoppeld model: rol blijft niet-toegewezen; geen verborgen externe oproep.
- Uitgeschakelde/gefaalde koppeling: betrokken rol pauzeert; uitsluitend vooraf toegestane en zichtbare fallback naar een geschikte ingeschakelde koppeling. Een vastgezette rol verhuist niet stilzwijgend.
- Model heeft geen vereiste mogelijkheden, regio-/accounttoegang of gegevensrechten: kandidaat uitsluiten vóór toewijzing.
- Ontbrekend corpus, manuscriptbeeld, transcriptie, vertaling of historische bron: concrete dekkingsmelding; geen verzonnen vervanging.
- Tegenstrijdig of onvoldoende bewijs: verschillen tonen, zekerheid begrenzen en geen consensus fabriceren.
- Tijdslimiet, kostenlimiet, annulering of providerfout: beëindigde/gedeeltelijke toestand met bruikbare afgeronde resultaten; geen eindeloze herhaling.
- Gewijzigd model, bron, policy of route: eerdere relevante evaluatieclaim vervalt totdat opnieuw getoetst is.

## Beschreven versus nog te valideren

De functionele baseline is beschreven. Uitwerking van concrete componenten, API-/datacontracten en foutcodes gebeurt per implementatie-eenheid vóór de betreffende bouwstap. Nog vast te stellen door toelating en tests: beste model per rol/taal, exact beschikbare account-/regioroutes, definitieve bron-/beeldrechten, passage-foliomappings, kwaliteit van lokale historische vertalingen, gemeten prestaties en kosten, en menselijke evaluatiedekking. Dit zijn geen al bewezen eigenschappen van het ontwerp.

De tests en gates van het hoofdplan V1-V8 en de aanvullende specificaties bepalen vrijgave. De ontwerpbeelden bewijzen geen werkende interface, wetenschappelijke juistheid, bronbeschikbaarheid of modelkwaliteit. Lokalisatie is een afzonderlijke claim van antwoordkwaliteit in die taal. Een technische preview kan eerder, met open beperkingen zichtbaar.

## Ontwerpbeelden

De [ontwerpcatalogus](docs/design/README.md) bevat gewone Chat, Research, theologische interpretatievergelijking, Roundtable en voorbeeldrolverdeling. De v5-voorbeelden gebruiken het onderwerp *Faith and good deeds*. Lezingen, toewijzingen en verbindingsstatussen zijn illustratief en geen uitgevoerde onderzoeksresultaten of echte API-configuratie. Een uitgewerkte manuscriptafbeeldingsviewer is nog niet afgebeeld.
