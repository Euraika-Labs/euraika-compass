# Euraika Compass — Functionele specificatie

Status: functionele baseline van 8 november 2026, met een werkende eerste onderzoeks- en chatflow. Naast dossiers, beelden en transcriptierevisies zijn privémodelverbindingen, tekstedities importeren, passagezoeking, relevantieselectie, chat met controleerbare verwijzingen en expliciet bewaarde gesprekken geïmplementeerd. De Mistral Large 4.0-koppeling is daadwerkelijk gebruikt. Webonderzoek, gegenereerde AI-Roundtable, dossierexport en de volledige beoogde ervaring blijven verdere bouwstappen. Historische OCR/HTR-kwaliteit is nog niet beproefd. Zie de [chatgids](docs/development/grounded-chat.md) en [ontwikkelhandleiding](docs/development/README.md).

[vision.md](vision.md) beschrijft het doel, de doelgroep en de richting van het product. Dit document vertaalt die visie naar functioneel gedrag; de technische plannen werken de bouw en verificatie uit.

Dit document is leidend voor functioneel gedrag. Het [implementatieplan R1-R28](docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md), [technology.md](technology.md), de [interactie- en taalspecificatie](docs/design/interaction-and-localization.md), [bewijsmethode en modelarchitectuur](docs/plans/research-method-and-model-architecture.md) en het [manuscriptregister](docs/sources/manuscript-register.md) werken dit uit. Technische keuzes mogen deze functionele regels niet stilzwijgend veranderen. Nieuwe gebruikersbeslissingen worden hier verwerkt en in de relevante uitwerking doorgevoerd.

[architecture.md](architecture.md) concretiseert de systeemonderdelen, gegevensstromen en uitvoeringscontracten; [design.md](design.md) concretiseert de schermen, interacties en vormgeving. Beide volgen dit functionele contract.

## Doel en uitgangspunten

Euraika Compass is een neutrale theologische onderzoekstool voor persoonlijk gebruik. De gebruiker kan de Thora, Bijbel en Koran onderzoeken, teksten en manuscripten inspecteren, interpretaties vergelijken en AI-deelnemers onder eigen regie laten discussiëren. Een gewone Chat biedt daarnaast ruimte voor levensvragen. De app is opensource, draait als lokaal gehoste webapp onder Pinokio en kan expliciet gekozen cloudmodellen gebruiken.

Geen religie krijgt een eigen voorkeurspositie. Onpartijdigheid betekent gelijke bewijsregels, zorgvuldigheid en respect; niet evenveel woorden, geforceerde overeenstemming of evenveel geloofwaardigheid voor elke bewering. Het systeem toont verschillen en onzekerheden en claimt geen absolute afwezigheid van bias.

De app kan religieuze en filosofische reflectie op brede levensvragen bieden, maar leidt actuele feiten of medische, juridische en andere specialistische claims niet uitsluitend uit schriftteksten af. Zij presenteert zich niet als behandelaar, bevoegde adviseur of religieuze autoriteit. Het onderzoeksbereik en ontbrekende expertise blijven herkenbaar.

Thora, Bijbel en Koran behouden hun eigen corpus-, editie- en interpretatiecontext. De gekozen Bijbelcanon is zichtbaar; Thora wordt niet stilzwijgend uitgebreid naar de hele Tanakh. Overlappende tekst in meerdere collecties telt niet als onafhankelijk dubbel bewijs. Een bewering van één boek over een ander is een toegeschreven tekstgegeven, geen toestemming voor het systeem om dat andere boek te overschrijven.

## Functies en waarneembaar gedrag

| Onderdeel | Wat de gebruiker kan en wat de app moet doen | Contract |
| --- | --- | --- |
| Gewone Chat | Levensvragen bespreken met vijf kiesbare persona's; gepaste reactie en vervolgvraag; relevante bronnen uitklappen; geen automatisch debat of verplichte citatendump | R2-R6, R17 |
| Research | Tabbladen en aanpasbare panelen met teksten, vertalingen, bronnen, woordonderzoek, bewijs, context, interpretaties en notities; vanuit Chat openen en terugkeren zonder context/conceptbericht te verliezen | R1, R7-R9, R17 |
| Tekstbibliotheek | Exacte editie, taal en corpus-/canonbereik kiezen; vers en omliggende passage openen; oorspronkelijke tekst, gepubliceerde vertaling en modelvertaling onderscheiden; ontbrekende dekking zichtbaar houden | R1, R7-R10 |
| Manuscripten | Echte, herleidbare scans uit authentieke onlinebronnen, ook Koranhandschriften, met zoom/folio/herkomst; afzonderlijke transcriptie/vertaling; oorspronkelijke viewerlink bij beperkingen | R21 |
| Foto's en scans lezen | Eigen foto's of bronbeelden openen, pagina/gebied selecteren, tekstherkenning of handschriftlezing laten voorstellen, onzekere tekens controleren en corrigeren; daarna vergelijken, vertalen, zoeken en bewaren | R21, R24, R27-R28 |
| Onderzoeksmethode | Voor iedere collectie dezelfde tekstuele/historische/taalkundige bewijsregels; passagecontext, verwante passages en tegenbewijs; E1/E2/E3 met bron, methode, onzekerheid en onderscheid tussen observatie, hypothese en conclusie | R4-R5, R8-R9, R22 |
| Interpretaties | Lezingen vergelijken via woordgebruik, vertaling, tekstvarianten, genre, tijd/context en aannames; steun- en tegenbewijs uitleggen; beter onderbouwde lezing waar mogelijk, met behouden onzekerheid en werkelijke verschillen | R23 |
| Secundaire bronnen | Commentaar en overlevering krijgen geen automatische interpretatieve autoriteit; hadith standaard uitgesloten, geen pakket toegelaten; beperkte mogelijke uitzondering uitsluitend individueel aantoonbare directe herkomst als context; geen omweg via webcitaten | R10, R22-R23 |
| Webonderzoek | Alleen indien ingeschakeld: zelfstandig zoekvragen maken, pagina's lezen en aanvullende bronnen vergelijken; inspecteerbare query/herkomst/datum/toegang; mislukte of ongelezen pagina niet als geverifieerd bewijs opvoeren | R9, R12-R13, R19 |
| Hybride modellen | Gekozen cloudmodel voor gesprek/onderzoek; eventueel tweede familie als criticus; lokale zoek-/taalworkers en offline algemene modeloptie; dezelfde bewijsregels voor iedere route | R13, R15, R24 |
| Orchestrator | Persona-/perspectiefrollen automatisch verdelen uitsluitend over geconfigureerde, ingeschakelde en geschikte modellen; rekening houden met mogelijkheden, evaluaties, taal, gegevensbeleid en budget; gebruiker kan inspecteren, wijzigen en vastzetten | R24-R25 en aanvullende allocatorregels |
| Roundtable | Expliciet meerdere AI-deelnemers in één chat; gedeeld bewijsdossier; gebruiker bepaalt sprekers, rondes, pauze, bronvragen en samenvatting; geen winnaar op basis van stemmen of modelaantal | R25 |
| Meertaligheid | Engels bij eerste start, EN/NL/AR/FR/DE als eerste UI-talen en uitbreidbare catalogi; UI-, gesprek- en brontaal onafhankelijk; Arabische UI RTL, tekstblokken met eigen richting | R18 |
| Dossiers | Tijdelijke gesprekken alleen bewust opslaan; antwoord, bewijs, notities, bron/model/policyversies en discussie kunnen heropenen; heranalyse bewaart oude versie; export volgt bronrechten | R13-R14 |
| Onderzoeksbewaring en delen | Gestarte onderzoeksdossiers automatisch bewaren en herstellen; gekozen revisies als dossierpakket exporteren/importeren; een latere optionele deeldienst publiceert alleen gekozen momentopnamen | R14, R26 |
| Herbruikbare bronbeelden | Toegelaten geraadpleegde beelden automatisch duurzaam bewaren en eenmaal opslaan; citaties verwijzen naar dezelfde bytes/revisie; duurzame bronkopieën blijven buiten tijdelijke cacheopruiming | R10, R21, R27 |
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

Alle authentieke, herleidbare en toegankelijke onlinebronnen kunnen voor persoonlijk onderzoek worden opgenomen. Dit omvat primaire teksten en scans, wetenschappelijke publicaties, oorspronkelijke auteurspagina's, projectrepositories en gedocumenteerde interpretaties. Institutionele of wetenschappelijke publicatie is een waardevolle aanwijzing voor herkomst en methode, geen exclusieve toelatingseis. Een niet-institutionele bron wordt op haar eigen herkomst en inhoud beoordeeld.

Een bronvermelding toont bronsoort, exacte editie/versie, taal, auteur/vertaler indien bekend en een inspecteerbare locatie. Authenticiteit gaat over de identiteit en herkomst van het materiaal, niet over de waarheid van al zijn uitspraken. Originele tekst, tekstkritische reconstructie, wetenschappelijke transcriptie, gepubliceerde vertaling, modelvertaling en annotatie zijn aparte lagen. Letterlijke citaten worden uit de opgehaalde bron ingevoegd en gecontroleerd. Een geldig citaat bewijst nog niet dat een interpretatie er inhoudelijk door ondersteund wordt.

Voor manuscripten houdt de app een uitbreidbaar bronregister bij, inclusief islamitische Koranhandschriften. Bibliotheken, universiteiten, musea, archieven en wetenschappelijke projecten zijn de eerste referenties; authentieke scans via andere onlinepublicaties kunnen worden toegevoegd wanneer zij naar het echte object en een controleerbare herkomst terugleiden. Bewaar oorspronkelijke publicatie of catalogusrecord, signatuur/objectidentiteit waar beschikbaar, verantwoordelijke maker/collectie en beeldherkomst. Een institutioneel logo of willekeurige mirror alleen bewijst die herkomst niet. Van gedelegeerde beeldhosts wordt de relatie met de oorspronkelijke bron vastgelegd.

De viewer biedt zoom, folio-/paginanavigatie en recto/verso waar relevant, met beschikbare transcriptie/vertaling naast de scan. Datering heeft een bron, methode en onzekerheid; datum van materiaal, afschrift en veronderstelde compositie worden niet gelijkgesteld. Een handschrift is niet automatisch het auteursexemplaar. Ontbrekende bladen, onzekere letters en reconstructies blijven zichtbaar. Geen verzonnen vers-folio-/woordkoppelingen en geen gegenereerde manuscriptbeelden als historische bron.

De app gebruikt bronnen voor persoonlijk lezen en onderzoek en registreert praktische beperkingen voor bekijken, lokaal bewaren, indexeren, extern modelgebruik, export en training afzonderlijk. Ontbrekende herpublicatierechten blokkeren niet automatisch het persoonlijk raadplegen van een toegankelijke bron. Online beschikbaarheid geeft op zichzelf geen algemene toestemming om materiaal opnieuw te publiceren, toegangscontroles te omzeilen of het voor training te gebruiken. Bij beperkte integratie blijft de oorspronkelijke publicatie-/viewerlink beschikbaar. Manuscripten zijn niet automatisch offline beschikbaar omdat de tekstbibliotheek lokaal staat.

Een daadwerkelijk geraadpleegd en toegelaten bronbeeld wordt tijdens onderzoek automatisch lokaal bewaard voor hergebruik, wanneer duurzame lokale bewaring is toegestaan en voldoende opslag beschikbaar is. Een zoekhit veroorzaakt geen volledige manuscriptdownload. Bron, folio/canvas, kwaliteit/resolutie, raadpleegtijd, attributie, rechten en inhoudshash blijven gekoppeld. Dossiers verwijzen naar hetzelfde opgeslagen object; gewijzigde bytes krijgen een nieuwe revisie. Thumbnails, crops en bekeken tegels worden niet als volledig origineel beschreven.

Een geciteerd duurzaam bronobject wordt vastgehouden zolang dat is toegestaan; tijdelijke cacheopruiming verwijdert het niet. Onbekende/restrictieve rechten, een volle schijf of een mislukte download leveren een concrete bewaartoestand op. De UI onderscheidt een blijvende lokale kopie, tijdelijke cache en uitsluitend remote verwijzing. Geen claim dat offline raadplegen mogelijk is op basis van alleen een URL of hash. Een bewaarkopie krijgt niet automatisch toestemming om mee te worden gedeeld.

Voor inhoudelijke uitleg volgt het systeem dezelfde methode bij alle collecties:

1. Formuleer vraag, scope en het soort conclusie dat onderzocht wordt.
2. Inspecteer de primaire passage en omliggende literaire context in een benoemde editie.
3. Zoek relevante passages én tegenbewijs elders in de gekozen collectie; registreer zoekbereik en gaten. Claim geen volledige inspectie van een heel boek wanneer die niet is uitgevoerd.
4. Maak bewijsitems E1/E2/E3 met bewering/waarneming, bron en locatie, tijd/context, methode en onzekerheid. Onderscheid observatie, toegeschreven hypothese en gevolgtrekking.
5. Onderzoek historische, taalkundige en materiële context met herleidbare bronnen en geef wetenschappelijk onderbouwde gegevens passend gewicht. Schrijf andere standpunten aan hun maker toe; vermijd anachronisme en ongefundeerde daterings- of auteursclaims.
6. Vergelijk relevante lezingen met woordgebruik, grammatica, vertaling, tekstvarianten, genre, aannames, steun- en tegenbewijs.
7. Geef een onderbouwde beoordeling voor de gestelde vraag en benoem onzekerheden, alternatieven en wat de conclusie zou kunnen veranderen.

De app kan uitleggen waarom een lezing sterker wordt ondersteund, maar doet niet alsof wetenschap voor iedere passage één definitief antwoord oplevert of bovennatuurlijke waarheid kan vaststellen. Zij toont een beknopte controleerbare argumentatie, geen verzonnen intern redeneertranscript of ongemeten zekerheidspercentage.

Commentaren en latere overleveringen krijgen geen automatische uitlegautoriteit. Een gedocumenteerde interpretatie mag als onderwerp van vergelijking worden beschreven zonder haar als waarheid over te nemen. Dit onderscheid geldt voor alle drie collecties.

Hadith blijft uitgesloten van de standaardcorpusbank en interpretatieve rechtvaardiging. Geen hadithpakket is toegelaten. De enige mogelijke uitzondering is afzonderlijk materiaal waarvan rechtstreekse herkomst volgens expliciet vastgestelde bewijseisen aantoonbaar is, en dan uitsluitend als historische context. Een traditionele classificatie zoals sahih voldoet niet automatisch; bij ontbrekend bewijs blijft het materiaal uitgesloten. Een webpagina of andere deelnemer kan deze regel niet omzeilen. De app belooft niet automatisch historische directe herkomst te kunnen bewijzen.

## Foto's en scans lezen

Beeld-naar-tekst is een kernfunctie voor persoonlijk onderzoek. De gebruiker kan een eigen foto van bijvoorbeeld een manuscript, boekpagina of inscriptie importeren, of een geraadpleegde online-afbeelding kiezen. Een eigen opname krijgt de beschikbare herkomstgegevens en een duidelijke melding wanneer object, datering of authenticiteit nog onbekend zijn; dat verhindert persoonlijk lezen niet. Het lezen van letters bevestigt die herkomst niet.

De gebruiker kiest de pagina of beeldregio en, waar nodig, taal/schrift en leesrichting. De app kan een geschikte lokale OCR-/handschriftworker of een door de gebruiker ingestelde beeldgeschikte modelroute gebruiken. Er is geen vaste leverancier of universele dekking beloofd. Hebreeuws, Aramees, Grieks en Koranisch Arabisch zijn relevante onderzoeksdoelen; historische schriftvormen, ligaturen en beschadigd materiaal vragen eigen praktische voorbeelden. Zonder uitvoerbare beeldlezer blijven het beeld en handmatige transcriptie bruikbaar.

De uitvoer begint als **automatische, nog niet gecontroleerde transcriptie**. Onzekere letters, alternatieve lezingen en onleesbare delen blijven herkenbaar. De app vult gaten niet stilzwijgend aan uit een bekende Bijbel- of Koranpassage en geeft een vertaling niet als letterlijke uitlezing weer. Eventuele reconstructie wordt alleen als afzonderlijk voorstel getoond. Tekst in een beeld is broninhoud en kan geen tools, beleid of modelroutes wijzigen.

Beeld en transcriptie staan naast elkaar. De gebruiker kan inzoomen, tekst corrigeren en beschikbare wetenschappelijke of gepubliceerde transcripties vergelijken. Een regel of woord verwijst alleen naar een precieze beeldregio als die koppeling werkelijk beschikbaar is; anders blijft de verwijzing op pagina-/selectieniveau. De oorspronkelijke bytes, hash en beeldherkomst blijven behouden; rotatie/crop, automatische transcriptie en gebruikerscorrectie zijn afzonderlijke afleidingen met hun eigen revisie en gebruikte worker/model. Een expliciete controle geldt alleen voor het nagekeken tekstbereik en bewijst geen authenticiteit of juiste interpretatie van het object.

Daarna kan de gebruiker de gekozen transcriptierevisie vertalen, woorden onderzoeken en naar mogelijke tekstparallellen zoeken. Een gevonden vers is een vergelijking, geen toestemming om de uitlezing van het beeld te vervangen. Een automatische lezing krijgt geen ongemerkt geverifieerd citaat- of editie-label. Citeren blijft herleidbaar tot beeld, tekstlaag, revisie en controlestatus; een uitspraak over een benoemde teksteditie wordt ook aan die editie getoetst. De bestaande bron- en hadithafspraken gelden ook voor herkende tekst.

Eigen foto's blijven privé. Een upload in tijdelijke Chat maakt niet vanzelf een blijvend dossier of gedeelde bronbank. Begrensde private tijdelijke bestanden kunnen voor de verwerking nodig zijn en worden met de betrokken sessie/taak opgeruimd; zij zijn geen openbare cache of bron voor later hergebruik. Bij bewust bewaren of import in een onderzoeksdossier worden het gekozen origineel en de bijbehorende transcriptierevisies bewaard. Beeldverwerking via een cloudroute vraagt een gekozen beeldgeschikte koppeling en toestemming voor die verwerking; de app toont welke foto/regio wordt verzonden. Een ingestelde tekstchatroute activeert dit niet automatisch. Lokale modus blokkeert cloudbeeldverwerking en kent geen stille externe fallback.

## Webonderzoek

De gebruiker configureert en activeert webonderzoek afzonderlijk. Dan kan de app binnen een begrensde run zelfstandig zoektermen maken, pagina's lezen en aanvullende bronnen beoordelen. Alleen een snippet is geen gecontroleerde bron. Zoektermen, URL, titel, auteur/uitgever indien bekend, opgegeven publicatie-/wijzigingsdatum, raadpleegtijd en beperkingen zijn inspecteerbaar. Onbekende gegevens blijven onbekend.

Persoonlijke vragen gebruiken geminimaliseerde onderwerptermen in plaats van volledige gesprekken of onnodige identificerende details. De app toont werkelijke uitgaande queries; zij belooft geen onfeilbare automatische anonimisering. Broninstructies zijn gegevens, geen opdrachten aan het systeem. Webbewijs blijft gescheiden van toegelaten tekstedities en voldoet aan hetzelfde bronbeleid. Mislukte toegang of ontbrekende dekking levert een zichtbare beperking op. Web-uit veroorzaakt nul zoek-/fetchaanroepen.

## Modellen, verbindingen en rolverdeling

Het algemene LLM kan de orchestrator zijn voor gesprek, onderzoek en rolverdeling. Cloudkandidaten omvatten de door de gebruiker genoemde providers Mistral, Alibaba Cloud voor onder meer Qwen/GLM, OpenAI, Anthropic en MiniMax; OpenRouter is een optionele gateway naar een concrete upstream-provider. De gebruiker kan beschikbare routes instellen en uitproberen. Lokale embeddings, reranking, citaatcontrole en kandidaat-vertaalworkers blijven afzonderlijke hulpmiddelen. Een lokale algemene modelroute blijft mogelijk voor offline/private gebruik met getoonde beperkingen.

**Alleen gekoppelde en ingeschakelde modellen zijn selecteerbaar.** De backend geeft de orchestrator een gefilterde lijst en controleert iedere gekozen route opnieuw. Verbinding, modelbeschikbaarheid binnen account/regio, vereiste mogelijkheden, gegevensbeleid, toepasselijke bronbeperkingen en budget bepalen of de route uitvoerbaar is. Een formele benchmark of deskundigenbeoordeling is geen voorwaarde om een werkende route persoonlijk te gebruiken. Een model uit een algemene catalogus of een suggestie van een deelnemer is geen geldige verbinding. De orchestrator zelf gebruikt eveneens een geschikte ingestelde route.

Bij automatische rolverdeling kiest de orchestrator uit die lijst op basis van taak, persona/perspectief, taal, beschikbare mogelijkheden, eerdere proefresultaten en kosten-/latencyvoorkeuren. Zonder eigen proefresultaten blijft de match voorlopig; de app claimt geen bewezen beste model. De gebruiker kan de toewijzing inspecteren, wijzigen of vastzetten. Meerdere rollen mogen hetzelfde model gebruiken; dat levert geen onafhankelijke experts op.

Provider/model/versie, opdracht, bewijsversie, toewijzingswijzigingen en beknopte selectiegrond zijn zichtbaar. Keys blijven buiten prompts, frontendbundels, logs, exports en Git. Onbekende endpoints of door modellen verzonnen route-IDs worden geweigerd. Een ongeconfigureerde service wordt nooit automatisch aangesloten.

Bij uitval pauzeert de rol. Alleen voor een niet-vastgezette rol mag vooraf toegestane fallback een andere geschikte ingeschakelde route kiezen; die wijziging wordt zichtbaar. Een vastgezette rol blijft bij uitval gepauzeerd totdat de gebruiker haar expliciet vrijgeeft of opnieuw toewijst, ook als fallbackbeleid een geschikte alternatieve route toestaat. Er volgt geen automatische vervanging of modelcall naar die vervanger. Een handmatige hertoewijzing doorloopt dezelfde toelatingscontroles. Zonder geschikte route volgt geen verzonnen antwoord. Uitschakelen verhindert volgende calls; annuleren kan reeds verzonden gegevens niet terughalen.

Cloudgebruik is expliciet ingesteld; geselecteerde gesprekscontext en toegestaan bewijs gaan dan naar de gekozen provider. Lokale modus blokkeert cloudmodelcalls. Webzoeken en remote manuscriptbeelden hebben eigen instellingen; lokale verwerking betekent niet automatisch dat deze andere verbindingen ook uitstaan. De gebruiker ziet dit onderscheid. Budgetten begrenzen tokens, uitgaande opdrachten en kosten; schattingen en werkelijk gerapporteerd verbruik blijven onderscheiden.

Lokale vertalers worden per oude taal en richting met enkele gevarieerde passages vergeleken met de brontekst en benoemde gepubliceerde vertalingen. Let op ontkenning, namen, meerduidigheid en interpretatieve toevoegingen; vraag waar nodig bronkundige hulp. Ondersteuning van een taalcode of modern Arabisch bewijst geen kwaliteit op Bijbels Hebreeuws, Oudgrieks of Koranisch Arabisch. Modelvertalingen blijven herkenbare voorstellen die de gebruiker kan controleren. Ontbrekende specialistische ondersteuning of onvoldoende gecontroleerde kwaliteit wordt gemeld; een verplicht beoordelingspanel is geen gebruiksvoorwaarde.

## Roundtable en menselijke moderatie

De gebruiker bepaalt onderwerp, scope, deelnemers, perspectieven, beschikbare modellen en budget. Een instelbare eerste configuratie is maximaal vier deelnemers met één beurt per aangevraagde ronde. De gebruiker geeft één deelnemer het woord of vraagt een ronde aan, pauzeert, stelt bronvragen, laat reageren, vraagt een synthese of beëindigt het gesprek. De orchestrator verdeelt rollen; hij neemt het modereren niet over.

Alle deelnemers zien hetzelfde gedeelde dossier met vaste bewijsversies. Nieuwe bronnen worden gecontroleerd, vastgelegd en gedeeld voordat afhankelijke reacties volgen. Per deelnemer zijn persona, perspectief, model/provider, spreekstatus en bronkoppelingen herkenbaar. Het zijn gelabelde AI-deelnemers, geen echte wetenschappers, geestelijken of historische personen.

Een synthese bewaart overeenkomsten, verschillen, tegenbewijs en open vragen met hun redenen. Geen meerderheid-als-waarheid, automatisch uitgeroepen winnaar of eindeloze autonome discussie. Meerdere providers of persona's vervangen geen bronbewijs en garanderen geen onafhankelijkheid of onpartijdigheid. De gewone chat wordt niet zonder gebruikerskeuze een debat.

## Talen, dossiers en beheer

De UI start in het Engels. Eerste lokalisatiedoelen zijn Engels, Nederlands, Arabisch, Frans en Duits, met uitbreidbare berichtcatalogi. De gekozen UI-taal wordt bewaard, onafhankelijk van gesprekstaal en brontaal/vertaling. Taalkeuze vertaalt of overschrijft oudere berichten niet automatisch. Persona-omschrijvingen, foutmeldingen, lege toestanden en toegankelijkheidsnamen worden mee gelokaliseerd.

Arabische UI gebruikt RTL. Arabische/Hebreeuwse passages en LTR-vertalingen behouden hun eigen richting in ieder scherm. Gemengde referenties, cijfers, URL's, diakritiek, selectie en kopiëren worden getest. Een vertaald menu is geen bewijs van antwoord- of vertaalkwaliteit in die taal; mogelijkheden, eigen proefresultaten en bekende beperkingen blijven zichtbaar.

Gewone gesprekken zijn tijdelijk. Bewust bewaren maakt een dossier met antwoord/discussie, eigen notities, bewijsitems, bronverwijzingen en relevante bron-, model-, policy- en zoekversies. Wie `New research` start of een chat bewust omzet, maakt expliciet een onderzoeksdossier; vanaf dat moment bewaart de app drafts, afgeronde resultaten en herstelstatus automatisch, met zichtbare bevestiging of fout. Heranalyse maakt een nieuwe gekoppelde versie. Geschiedenis toont bewust bewaarde gesprekken en aangemaakte onderzoeksdossiers. Geen impliciet achtergrondgeheugen tussen gesprekken en geen automatische inzet van persoonlijke vragen als trainings- of testdata.

De eerste deelroute is export/import van een gekozen dossierrevisie: leesbaar rapport, versieerbaar manifest, relevante argumenten, notities, bron-/modelverwijzingen, hashes en uitsluitend toegelaten bestanden. De gebruiker selecteert persoonlijke notities/discussie bewust en ziet vooraf wat wordt opgenomen of weggelaten. Geen API-keys, ruwe appdatabase of ongevraagd volledige persoonlijke geschiedenis. Import controleert inhoud en maakt een afzonderlijk dossier/revisie zonder lokaal werk te overschrijven. Ontbrekende of niet-deelbare scans behouden een toegestane officiële verwijzing en beschikbaarheidsmelding.

Een latere optionele deeldienst biedt leestoegang tot expliciet gepubliceerde momentopnamen met eigen authenticatie/toegangsbeheer. Intrekken blokkeert toekomstig ophalen via die route, niet reeds gedownloade kopieën. De lokale database wordt niet als bestand op een netwerkshare of via bestandssynchronisatie gedeeld. Realtime gezamenlijk bewerken en meerdere menselijke accounts vragen afzonderlijke uitwerking; een dossier als bestand delen vereist dit niet.

Back-ups omvatten een consistente DB-snapshot en de bijbehorende niet-herbouwbare bestanden. Herstel controleert integriteit, objecthashes en dossierheropening. Een zoekindex kan opnieuw worden gemaakt; een gebruikte scan of eigen notitie kan niet worden hersteld uit alleen een hash. Databases, tijdelijke cache en duurzame bronobjecten hebben afzonderlijke bewaarbeheerregels volgens [technology.md](technology.md).

De gekozen technische basis is PostgreSQL voor lokaal en centraal gebruik, met grote bronobjecten buiten de database. De Pinokio-flow moet het databaseproces en de modelworkers gezamenlijk kunnen installeren, starten, op gereedheid controleren en stoppen; bestaande data blijft bij herstel/update behouden. Dossierexport is afzonderlijk van databaseback-up en bevat geen databasecredentials.

Pinokio verzorgt installeren, starten, stoppen en Open Web UI. De gebruiker beheert bronnen/modellen/providerkoppelingen met zichtbare voorwaarden, omvang en status. Geen stilzwijgende omvangrijke downloads. Stop en annulering beëindigen betrokken taken; update/herstel bewaren bronnen, modellen, dossiers en instellingen. Lezen van reeds aanwezige toegelaten teksten vereist geen cloudkey.

De server luistert standaard alleen lokaal. Geen ongevraagde LAN-toegang, prompttelemetrie of overdracht van volledige gesprekken aan zoekproviders. Het gekozen cloudmodel ontvangt wel de voor die verwerking geselecteerde context; de UI presenteert dat niet als volledig lokale verwerking.

## Kernroutes

1. **Levensvraag:** Chat → persona → gesprek → optioneel bronnen openen → eventueel verder in Research → alleen op verzoek bewaren.
2. **Theologische kwestie:** onderzoeksdossier starten → automatische draftbewaring → vraag en scope → passages/context en verwante passages/tegenbewijs → historische/taalkundige bewijsitems → alternatieve interpretaties → nieuwe resultaatrevisie.
3. **Manuscript:** herleidbaar bron-/catalogusrecord → scan/folio met herkomst en gebruiksinformatie → beschikbare transcriptie/vertaling → alleen onderbouwde passagekoppeling; beperkingen geven een expliciete melding of oorspronkelijke viewerlink.
4. **Roundtable:** deelnemers/perspectieven kiezen → orchestrator filtert geschikte ingeschakelde koppelingen → toewijzingen inspecteren/pinnen → moderator vraagt beurt/ronde → bronnen en bezwaren delen → moderator vraagt synthese of stopt.
5. **Beheer:** bron/model/provider en taal instellen → rechten, mogelijkheden en omvang controleren → expliciet downloaden/activeren → gewone start; geen key nodig om beschikbare lokale teksten te lezen.
6. **Delen:** dossierrevisie kiezen → persoonlijke inhoud en toegelaten bestanden selecteren → exportoverzicht controleren → pakket maken → op andere installatie importeren met behoud van herkomst en zichtbare ontbrekende bronnen.
7. **Foto lezen:** foto/scan kiezen → pagina of regio selecteren → automatische transcriptie → onzekere tekst naast het beeld controleren/corrigeren → optioneel vergelijken, vertalen of zoeken → gekozen beeld-/tekstversies bewust bewaren in een dossier.

## Fouten en beperkingen zijn functioneel gedrag

- Geen geschikt gekoppeld model: rol blijft niet-toegewezen; geen verborgen externe oproep.
- Uitgeschakelde/gefaalde koppeling: betrokken rol pauzeert. Alleen een niet-vastgezette rol kan vooraf toegestane, zichtbare fallback naar een geschikte ingeschakelde koppeling gebruiken. Een vastgezette rol blijft gepauzeerd totdat de gebruiker haar expliciet vrijgeeft of opnieuw toewijst; geen automatische vervanging of modelcall naar een vervanger.
- Model heeft geen vereiste mogelijkheden, regio-/accounttoegang of gegevensrechten: kandidaat uitsluiten vóór toewijzing.
- Ontbrekend corpus, manuscriptbeeld, transcriptie, vertaling of historische bron: concrete dekkingsmelding; geen verzonnen vervanging.
- Onscherp, beschadigd of niet-ondersteund beeld/schrift: onzekerheid of onleesbaarheid tonen; gebruiker kan het beeld/gebied aanpassen of handmatig transcriberen. Geen verzonnen letters, versmatch of ongeconfigureerde beeldprovider.
- Tegenstrijdig of onvoldoende bewijs: verschillen tonen, zekerheid begrenzen en geen consensus fabriceren.
- Tijdslimiet, kostenlimiet, annulering of providerfout: beëindigde/gedeeltelijke toestand met bruikbare afgeronde resultaten; geen eindeloze herhaling.
- Gewijzigd model, bron, policy of route: eerdere proefresultaten blijven aan hun oude versie gekoppeld; relevante controles worden gericht herhaald en oude resultaten gelden niet automatisch voor de wijziging.
- Schijf vol of onvolledige bronbewaring: geen vals opgeslagen/offline-label; concrete fout en herstelactie, zonder geciteerd materiaal stilzwijgend op te ruimen.
- Niet-deelbaar object of ontbrekend bestand: export meldt de beperking en gebruikt waar toegestaan een verwijzing; import claimt geen volledige offline reproduceerbaarheid.

## Praktische kwaliteitscontroles

De persoonlijke app wordt bruikbaar gemaakt met gerichte controles op echte bronnen en gebruikersflows. Er is geen verplicht grootschalig evaluatieprogramma, vast minimumaantal beoordelingen, gecertificeerde neutraliteit of deskundigenpanel als voorwaarde om onderzoek te doen. De controles uit V1-V9 van het hoofdplan zijn praktische hulpmiddelen om concrete fouten te vinden en te herstellen.

- **Bron en citaat:** open de verwijzing, controleer editie/locatie en vergelijk letterlijke citaten met het opgehaalde materiaal. Registreer waar een bron vandaan komt en wat er onzeker blijft.
- **Beeld naar tekst:** lees een eigen foto en een echte online-scan, vergelijk de transcriptie naast het beeld en probeer een onleesbaar fragment. Controleer dat correcties als nieuwe revisie blijven bewaard, geen tekst wordt aangevuld en een ongeteste uitlezing geen geverifieerd bronlabel krijgt. Probeer ook lokale modus zonder beeldworker en een tijdelijke Chat-upload zonder dossierbewaring.
- **Context en interpretatie:** probeer vragen die omliggende context, verwante passages en tegenbewijs vereisen. Controleer dat een eigen lezing, toegeschreven standpunt en vastgesteld tekstgegeven herkenbaar blijven.
- **Neutrale werkwijze:** probeer dezelfde soorten kritische vragen bij alle drie collecties en wissel persona of bronvolgorde. Behoud legitieme verschillen; zoek ongefundeerde voorkeur, weggelaten bezwaren en valse consensus.
- **Model en taal:** gebruik een kleine, gevarieerde verzameling eigen proefvragen per gebruikte taak/taal. Vergelijk waar nuttig een andere route of gepubliceerde vertaling en noteer beperkingen zonder ongemeten kwaliteitsscores.
- **Bediening en bewaring:** doorloop vraag → bron → passage/folio → notitie → dossier → heropenen. Controleer ook uitval, annuleren, vastgezette rollen, export/import, backup/herstel en offlinebeschikbaarheid.

De gebruiker kan een fout markeren, een bron of argument corrigeren en het onderzoek opnieuw uitvoeren met behoud van de oude revisie. Deskundige hulp is nuttig voor moeilijke taal- of historische vragen, zonder iedere uitkomst van de tool vooraf te hoeven certificeren.

De functionele baseline is beschreven en de eerste skeleton implementeert dossier-/beeldbewaring, handmatige revisies, routeconfiguratie en jobafhandeling. De werkende API heeft OpenAPI-documentatie; overige contracten groeien per bouwstap mee. Beschikbare account-/regioroutes, bronbestanden, passage-foliomappings, modellezing, vertaalgedrag, prestaties en kosten moeten nog met echte gegevens worden geprobeerd. De ontwerpbeelden bewijzen geen werkende interface of onderzoeksresultaat. Bekende beperkingen blijven zichtbaar terwijl de persoonlijke tool stapsgewijs bruikbaar wordt.

## Ontwerpbeelden

De [ontwerpcatalogus](docs/design/README.md) bevat gewone Chat, Research, theologische interpretatievergelijking, Roundtable en voorbeeldrolverdeling. De v5-voorbeelden gebruiken het onderwerp *Faith and good deeds*. Lezingen, toewijzingen en verbindingsstatussen zijn illustratief en geen uitgevoerde onderzoeksresultaten of echte API-configuratie. Een uitgewerkte manuscriptafbeeldingsviewer is nog niet afgebeeld.
