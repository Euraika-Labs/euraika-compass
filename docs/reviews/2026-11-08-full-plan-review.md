# Euraika Compass — Review van het volledige plan

Datum: 8 november 2026. Beoordeelde baseline: commit [`1e73cf08f5e73333a5cd0c2ac16d191e48e2c0a6`](https://github.com/Euraika-Labs/euraika-compass/tree/1e73cf08f5e73333a5cd0c2ac16d191e48e2c0a6).

**Historisch reviewverslag.** Later op 8 november 2026 heeft de gebruiker de scope verduidelijkt: persoonlijk, neutraal theologisch onderzoek met praktische kwaliteitscontroles en authentieke, herleidbare internetbronnen. Het zware evaluatieprogramma en de uitsluitend institutionele bronselectie zijn vervallen. De actuele regels staan in [functional.md](../../functional.md) en V1-V9 van het [implementatieplan](../plans/2026-11-08-1552-feat-religion-research-app-plan.md). De twee hieronder beschreven documentcorrecties blijven geldig; de oude review geldt niet als beoordeling van alle latere wijzigingen.

## Uitkomst

Deze documentreview bevestigt twee concrete inconsistenties, beide P2. Beide zijn gecorrigeerd in de specificaties: de verouderde persona-definitie en, na expliciete goedkeuring door de gebruiker op 8 november 2026, de regel voor vastgezette rollen bij uitval. Er zijn geen open beslissingen uit deze review over. Er is geen P0/P1-ontwerpblokkade aangetoond. Dat is geen bewijs dat de app uitvoerbaar, veilig, wetenschappelijk juist of onpartijdig is: er bestaat nog geen geïmplementeerde app en de geplande runtime-, bron- en inhoudelijke proeven zijn niet uitgevoerd.

P2 betekent hier een plaatselijke correctie die verkeerde implementatie of tegenstrijdige tests kan voorkomen. Deze review voegde destijds geen productscope toe. PostgreSQL, eenvoudige TypeScript-controles, de primaire-tekstgerichte methode, gekoppelde modelroutes en menselijke moderatie bleven behouden. Het bronbeleid is nadien op gebruikersinstructie verbreed naar authentieke, herleidbare onlinebronnen.

## Omvang en methode

De review beoordeelt deze documenten samen:

- [Visie](../../vision.md), [functionele specificatie](../../functional.md), [technologie](../../technology.md), [architectuur](../../architecture.md), [design](../../design.md) en [README](../../README.md).
- [Hoofdplan met R1-R27 en V1-V9](../plans/2026-11-08-1552-feat-religion-research-app-plan.md).
- [Onderzoeksmethode, hybride modellen en Roundtable](../plans/research-method-and-model-architecture.md).
- [Interactie-, taal- en webspecificatie](../design/interaction-and-localization.md).
- [Manuscriptregister](../sources/manuscript-register.md) en [ontwerpcatalogus](../design/README.md).

Zeven beoordelaars kregen afzonderlijke contexten met dezelfde volledige, genummerde documentbundel en de vastgelegde gebruikerskeuzes. Hun voorstellen zijn gecontroleerd op bewijs, concrete gevolgen, overlap en overeenstemming met de leidende functionele specificatie. Een ontbrekende herhaling of een reeds toegewezen toekomstige toelatingstaak geldt niet als vergeten functionaliteit. De eindbeoordeling is een synthese, geen stemming tussen modellen.

De gegenereerde conceptbeelden en oude generatieprompts zijn illustratief. Zij zijn geen norm voor wetenschappelijke uitkomsten, werkende interacties of actuele providerverbindingen. Deze review omvat geen nieuwe beeld-/pixelcontrole, bronlicentieaudit, prestatiemeting, pentest of runtimevalidatie.

## Bevinding 1 — Persona's waren nog verplicht aan één model gebonden

**Prioriteit:** P2. **Status:** gecorrigeerd. **Beoordeling:** samenhang; bewijssterkte 100 volgens de reviewrubric.

**Gevolg:** een implementer kon de oude persona-definitie volgen en alle persona's verplicht op één model zetten. Dat verhindert de afgesproken roltoewijzing over verschillende gekoppelde modellen.

**Bewijs:** het hoofdplan definieerde een persona als “een begrensd configuratieprofiel op hetzelfde model”. De leidende functionele specificatie scheidt persona, perspectief en uitvoerend model; de aanvullende routeringsspecificatie verbiedt een hardcoded model voor alle persona's. Dit is een oude beperking die is blijven staan na een geaccepteerde uitbreiding.

**Toegepaste correctie:** de definitie zegt nu dat een persona stijl en methode bepaalt, onafhankelijk van de modelroute. Meerdere persona's mogen hetzelfde model gebruiken. De gedeelde bron- en onpartijdigheidsregels blijven van kracht. Dit voert de bestaande gebruikerskeuze uit en verandert geen productbeslissing.

Baselineverwijzingen: [oude definitie, hoofdplan regel 102](https://github.com/Euraika-Labs/euraika-compass/blob/1e73cf08f5e73333a5cd0c2ac16d191e48e2c0a6/docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md#L102), [onafhankelijke instellingen, functional.md regel 46](https://github.com/Euraika-Labs/euraika-compass/blob/1e73cf08f5e73333a5cd0c2ac16d191e48e2c0a6/functional.md#L46).

## Bevinding 2 — Vastgezette rol en automatische fallback waren niet eenduidig

**Prioriteit:** P2. **Status:** gecorrigeerd na expliciete gebruikersgoedkeuring op 8 november 2026. **Beoordeling:** samenhang; bewijssterkte 75 volgens de reviewrubric.

**Goedgekeurde regel:** automatische vooraf toegestane fallback geldt alleen voor niet-vastgezette rollen. Een vastgezette rol blijft bij uitval gepauzeerd totdat de gebruiker haar expliciet vrijgeeft of opnieuw toewijst, ook als een toegestane alternatieve route beschikbaar is. Er volgt geen automatische vervanging of modelcall naar die vervanger. Handmatige hertoewijzing doorloopt dezelfde toelatingscontroles.

**Gevolg van de oude tekst:** als een vastgezet model uitviel, kon één implementer een zichtbare vervanging toestaan, terwijl een ander diezelfde vervanging volgens de acceptatietest moest blokkeren. De UI en tests konden dan verschillend gedrag afdwingen.

**Toegepaste correctie:** de functionele specificatie, architectuur, design en aanvullende routeringsspecificatie leggen dezelfde voorrang van vastzetten vast. De acceptatieproeven bevatten nu expliciet het geval waarin een vastgezette rol uitvalt terwijl een toegestane alternatieve route beschikbaar is: de rol blijft gepauzeerd, de toewijzing en pin blijven intact en er start geen modelcall naar een vervanger. Dezelfde proef zonder pin controleert dat vooraf toegestane fallback wel zichtbaar kan werken. Dit zijn vastgelegde acceptatieproeven voor de toekomstige implementatie; zij zijn nog niet met een werkende app uitgevoerd.

**Bewijs uit de baseline:** de algemene gedragsregel stond zichtbare fallback toe en verbood een vastgezette rol alleen om “stilzwijgend” te verplaatsen. De aanvullende acceptatietekst zei dat wijzigingen aan een vastgezette toewijzing werden geblokkeerd. Het design beschreef een uitgevallen vastgezette rol als geblokkeerd, maar noemde direct daarna toegestaan fallbackbeleid zonder expliciete uitzondering voor pins. Het verschil ging over zichtbaar versus geheel niet automatisch vervangen, niet alleen over een woordkeuze.

Baselineverwijzingen: [fallbackregel, functional.md regel 114](https://github.com/Euraika-Labs/euraika-compass/blob/1e73cf08f5e73333a5cd0c2ac16d191e48e2c0a6/functional.md#L114), [acceptatietest, aanvullende specificatie regel 95](https://github.com/Euraika-Labs/euraika-compass/blob/1e73cf08f5e73333a5cd0c2ac16d191e48e2c0a6/docs/plans/research-method-and-model-architecture.md#L95). Zie ook de routeringsparagrafen in architecture.md en design.md.

De gedragsaanscherping is eerst als voorstel gerapporteerd en pas na goedkeuring in de specificaties toegepast. De routeringslogica zelf is nog niet geïmplementeerd.

## Uitvoeringswerk na de review

Dit zijn praktische bouwtaken die nog niet zijn uitgevoerd. Zij vragen werkende voorbeelden en herstel van concrete fouten; het eerdere formele evaluatieprogramma is geen voorwaarde meer voor persoonlijk gebruik.

| Taak | Waar belegd | Wat nog moet worden aangetoond |
| --- | --- | --- |
| PostgreSQL/pgvector onder Windows en Pinokio | Eerste technische basis en lifecycle-eenheid | Vertrouwde distributie, installatie, opslaglocatie, gereedheid, start/stop, update en backup/restore met echte processen |
| Bronnen daadwerkelijk openen | Bronimport en manuscriptregister | Herleidbare editie/scan, juiste koppeling en bekende gebruiksbeperkingen; de startlijst is geen gesloten institutionele whitelist |
| Modellen en talen uitproberen | Modelinstellingen en praktische controlevoorbeelden | Werkende gekoppelde routes, bruikbaar brongebruik, bekende taalbeperkingen en zichtbare kosten; geen verplichte deskundigenbeoordeling |

De vroegere verplichte testvolumes, panels en statistische vrijgavedrempels zijn op verzoek van de gebruiker vervangen door een kleine groeiende verzameling eigen onderzoeksvragen, bron-/citaatcontroles en werkelijke UI-/bewaarproeven. Hun oorspronkelijke formulering is terug te vinden in de gelinkte Git-baseline en bepaalt het huidige plan niet meer.

## Reviewdekking

| Invalshoek | Uitkomst na synthese |
| --- | --- |
| Samenhang | Twee behouden bevindingen, beide gecorrigeerd; de tweede na expliciete gebruikersgoedkeuring |
| Uitvoerbaarheid | Geen aanvullende materiële bevinding |
| Productkeuzes | Geen aanvullende materiële bevinding |
| Gebruikerservaring | Geen aanvullende materiële bevinding |
| Privacy en beveiliging | Geen aanvullende materiële bevinding |
| Scope en afhankelijkheden | Geen aanvullende materiële bevinding |
| Kritische tegenvoorbeelden | Geen aanvullende materiële bevinding |
| Aanvullende cross-modelcontrole | Niet uitgevoerd: vereiste `jq` ontbreekt in de gebruikte WSL-route |

De extra cross-modelpogingen voor product, beveiliging, kritische tegenvoorbeelden en de volledige documentbundel eindigden vóór een provider/modelaanroep met dezelfde prerequisite-skip. Er is geen onafhankelijke modelfamiliebeoordeling of modelovereenstemming aan de bewijssterkte toegevoegd. Er was geen authenticatiefout vastgesteld en er zijn geen nieuwe API-keys gevraagd of geconfigureerd.

Er zijn geen onzekere vermoedens als fouten opgevoerd en geen generieke wensen voor meer detail aan de scope toegevoegd. De persona-definitie volgt de bestaande gebruikerskeuze; de fallbackregel is na expliciete goedkeuring aangescherpt. De overige inhoudelijke productkeuzes zijn intact gelaten.

## Vervolg

Beide bevindingen uit deze review zijn in de documentatie afgehandeld. De eerste technische proef kan volgens de bestaande bouwvolgorde beginnen. Bouw en toets de routeringslogica met de vastgelegde voorrang van pins en de bijbehorende uitvalproeven. Gebruik de actuele praktische controles bij het bouwen van de persoonlijke onderzoekswerkbank.
