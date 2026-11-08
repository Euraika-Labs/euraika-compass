# Euraika Compass — Interface- en interactieontwerp

Status: ontwerpbaseline, 8 november 2026. Dit document beschrijft de beoogde ervaring. De bestaande beelden zijn gegenereerde concepten; er is nog geen werkende interface, toegankelijke componentbibliotheek of geteste modelconfiguratie.

[vision.md](vision.md) geeft de richting; [functional.md](functional.md) bepaalt het gedrag. [architecture.md](architecture.md) beschrijft de systeemgrenzen en [technology.md](technology.md) de stack. Dit ontwerp concretiseert die afspraken zonder nieuwe bronrechten of bewezen modelkwaliteit te veronderstellen.

## 1. Ontwerpdoel

Compass is een persoonlijke, neutrale theologische onderzoekswerkbank met een rustige gespreksomgeving. De gebruiker onderzoekt teksten en argumenten, kan een levensvraag bespreken en meerdere AI-perspectieven onder eigen moderatie laten reageren. De interface maakt steeds duidelijk wat tekst, vertaling, historisch gegeven, hypothese en interpretatie is. Praktische broncontrole en gebruikersregie staan centraal; de UI deelt geen geloofswaarheden of gecertificeerde theologische oordelen uit.

De belangrijkste ontwerpprincipes zijn leesbaarheid, inspecteerbare onderbouwing, menselijke regie en dezelfde visuele behandeling van Thora, Bijbel en Koran. Verschillen in dekking of argumentsterkte blijven zichtbaar; een symmetrische vormgeving betekent geen geforceerde inhoudelijke gelijkheid.

## 2. Navigatie en gedeelde workspace

| Niveau | Onderdelen | Gedrag |
| --- | --- | --- |
| Appbalk | Merk, Chat/Research, connectiestatus, taal en dossieractie | Compact en voorspelbaar; geen grote welkomstkop boven een actieve werkruimte |
| Icoonrail | Snelkoppelingen naar gesprek, onderzoek, dossiers, bronnen en instellingen | Ieder icoon heeft een toegankelijke naam en zichtbare geselecteerde toestand |
| Contextzijbalk | Bewaarde gesprekken/dossiers of bronbibliotheek | Inklapbaar; tijdelijke chats worden niet als duurzaam bewaarde geschiedenis voorgesteld |
| Actieve werkruimte | Chat, Research, of Roundtable binnen Chat | Dezelfde gesprek-/broncontext kan in een andere layout worden geopend |
| Bron-/bewijsinspectie | Exacte passage, editie, bronrechten en argumentrelaties | Bereikbaar vanuit iedere inhoudelijke verwijzing, zonder de oorspronkelijke vraag te verliezen |

Chat/Research is een layoutkeuze. `Open in Research` verandert geen persona, opslagtoestemming of modelbudget en start geen nieuwe analyse. Bewaar conceptbericht, bronselectie, geopende passages en passende scrollpositie. Een geopend bronnenpaneel mag de getypte gebruikersinvoer niet vervangen.

De opslagstatus is expliciet: `Temporary conversation` met `Save as dossier`, of een dossiernaam met `Saving…`, `Saved` of `Save failed`. `New research` maakt bewust een dossier aan en begint automatische draftbewaring. Alleen een passage in de Research-layout bekijken maakt een tijdelijke chat niet automatisch duurzaam.

## 3. Visuele taal

### Kleur

| Token | Waarde | Gebruik |
| --- | --- | --- |
| `brand.blue` | `#001C3A` | Appbalk, icoonrail en primaire structuur |
| `brand.blueSecondary` | `#003369` | Acties en ondersteunende geselecteerde toestanden |
| `brand.gold` | `#F4A616` | Spaarzame actie-/focusaccenten en tekstmarkering |
| `text.primary` | `#1E2D39` | Hoofdtekst, ook op goud |
| `text.secondary` | `#51545A` | Secundaire tekst op wit |
| `surface.primary` | `#FFFFFF` | Leesvlakken |
| `surface.subtle` | `#F3F6FA` | Werkruimteachtergrond en rustige groepen |
| `border.default` | `#D9E2EE` | Niet-interactieve scheidingen; geen vervanging voor een zichtbare focusrand |

De vijf merkkleuren volgen de in het project vastgelegde Euraika-identiteit; aanvullende oppervlaktetokens zijn ontwerpvoorstellen. Geen religiespecifieke kleurhiërarchie, neutraliteitsscore of certificeringsbadge. Status gebruikt altijd tekst/iconen naast eventuele kleur. Goud is geen algemene achtergrond voor grote leesgebieden.

Berekening voor vlakke, ondoorzichtige sRGB-kleuren op 8 november 2026: navy/wit **17,11:1**, charcoal/wit **14,10:1**, charcoal/goud **6,92:1**, secundaire tekst/wit **7,59:1** en wit/goud **2,04:1**. Dit ondersteunt donkere tekst/iconen op goud. Het is geen verificatie van een screenshot of uiteindelijke UI: transparantie, hover, focus, disabled-states en werkelijk gerenderde tekst moeten opnieuw worden gemeten.

### Typografie, ruimte en componenten

Start met een rustige sans-serif voor bediening en lopende UI-tekst, circa 16 px voor gewone leesinhoud en 14 px voor compacte metadata. Koppen structureren de taak en blijven bescheiden. Bronteksten kunnen een geschikte afzonderlijke leesletter krijgen. Arabische/Hebreeuwse/Griekse fonts en diakritiek worden met echte passages getest; eventuele meegeleverde fonts krijgen een licentiecontrole. Geen verplichte externe fontrequest.

Gebruik een consistente 4/8-px-ruimteschaal, dunne scheidingen, beperkte schaduw en herkenbare kleine lijniconen. Geneste kaarten worden beperkt waar doorlopende tekst of een eenvoudige tabel duidelijker is. Belangrijke acties hebben een tekstlabel; destructieve of onomkeerbare acties krijgen een passende bevestiging, gewone paneel-/persona-/taalwissels niet.

Gedeelde componenten: AppShell, ModeSwitch, ConnectionSummary, LanguagePicker, DossierStatus, PersonaSelector, ChatComposer, ConversationMessage, SourceReference, SourceInspector, EvidenceTable, InterpretationComparison, ManuscriptViewer, ParticipantList, ModeratorConsole, RoleAssignmentTable en ExportReview. Naamgeving is een bouwvoorstel, geen reeds aanwezige code.

## 4. Chat voor levensvragen

De gewone Chat heeft een leesbare conversatiekolom met beperkte breedte, een zichtbaar persona-/dieptekeuzepunt en een vaste composer. Een bronnenpaneel is optioneel. De eerste reactie op verlies of twijfel maakt ruimte voor de gebruiker; geen gedwongen enquête, preek, drie religieuze kolommen of debat.

Een inhoudelijk antwoord kan compacte passageverwijzingen bevatten. `Explore sources` opent onderbouwing; `Open in Research` opent dezelfde context in de werkruimte. Algemene menselijke erkenning krijgt geen fictief aantal bronnen. Een tekstueel of historisch argument houdt zijn werkelijke verwijzingen.

De persona is zichtbaar met een korte omschrijving. Diepte, perspectief en model zijn afzonderlijke instellingen; een warme persona bepaalt geen religieuze voorkeur. De gebruiker kan gericht verdiepen zonder opnieuw te beginnen. Gewone Chat wordt alleen op expliciete keuze Roundtable.

De composer bewaart niet-verzonden tekst bij modewissels en fouten. Verzenden toont dat de opdracht ontvangen is; annuleren en opnieuw verbinden maken de uitvoeringsstatus duidelijk. Een mislukte netwerkverbinding stuurt dezelfde vraag niet ongemerkt opnieuw als betaalde opdracht.

## 5. Research-werkruimte

Brede schermen tonen een bron-/dossiernavigator, een centrale lees-/onderzoeksruimte en een assistentpaneel. Binnen de werkruimte kunnen notities/woordonderzoek als onderste paneel worden geopend. Panelen zijn aanpasbaar en inklapbaar; tabbladen hebben herkenbare titels, sluitacties en behoud van context. De laatste bruikbare layout kan worden hersteld.

| Onderzoeksdeel | Kerninhoud en acties |
| --- | --- |
| Overview | Vraag, gekozen scope, edities, dekking, resultaatrevisie en open vragen |
| Text reader | Benoemde brontekst en gekozen vertalingen, omliggende context, selectie en woordonderzoek |
| Manuscripts | Werkelijke scan, folio/canvas, zoom, herkomst en beschikbare transcriptie/vertaling |
| Evidence | E1/E2/E3, bronlocatie, bewijssoort, methode, onzekerheid en koppelingen naar claims |
| Context | Literaire, historische, taalkundige en materiële gegevens met onderscheid in dateringen |
| Interpretations | Voorgestelde/toegeschreven lezingen, steun, tegenbewijs, aannames en open geschillen |
| Assessment | Begrensde conclusie voor de vraag, onderbouwing, onzekerheden en ontbrekende dekking |
| Notes / Research log | Eigen notities en een compacte feitelijke trace van gebruikte tools, bronnen en versies |

Deze onderdelen kunnen als tabbladen of subtabbladen worden gegroepeerd om dubbele navigatie te vermijden. Hun informatiebetekenis blijft gelijk. De conceptbeelden zijn verkenningen, geen verplichting om ieder getekend tabblad tegelijk zichtbaar te maken.

Broncollecties krijgen dezelfde behandeling. Toon daadwerkelijk bereik: aanwezig, niet geïnstalleerd, niet onderzocht of onvoldoende dekking. Een aangekruiste collectie is geen bewijs dat het antwoord juist of onpartijdig is. Een expliciete smalle onderzoeksvraag wordt niet stilzwijgend uitgebreid naar alle collecties.

## 6. Bewijs en interpretatievergelijking

Een bewijsitem toont een benoemde waarneming of claim met bronlocatie, versie, bewijssoort, context en onzekerheid. `Reference checked` kan alleen slaan op een uitgevoerde referentiecontrole; het mag niet suggereren dat de interpretatie bewezen is. Een onbewezen historische contextvraag krijgt bijvoorbeeld `Source needed` in plaats van een feitlabel.

De vergelijkingstabel bevat per lezing: omschrijving, auteur/school indien gedocumenteerd, primaire passages, woord-/vertaalkeuzes, relevante context, steunbewijs, tegenbewijs, aannames en onzekerheid. Een eigen modelvoorstel heet `Proposed reading`; het wordt niet aan een gehele religie toegeschreven.

De gebruiker kan de gegevens achter een conclusie inspecteren en vervolgens terugkeren naar de vergelijking. Exact citaat, gepubliceerde vertaling, modelvertaling, historische hypothese en interpretatieve gevolgtrekking krijgen leesbare labels. Geen ongemeten zekerheidspercentage of winnaar op basis van modelstemmen. Werkelijke onenigheid blijft zichtbaar in een synthese.

Voor alle collecties gelden de primaire-tekstgerichte bronregels uit [functional.md](functional.md). Hadith is geen standaard bron of uitlegautoriteit. Een interpretatie uit later commentaar kan als gedocumenteerde lezing worden beschreven zonder daarmee de primaire tekst te overrulen. De interface toont de ingestelde bronpolicy compact; zij gebruikt die niet als keurmerk voor een geloofspositie.

## 7. Manuscriptviewer en broninspectie

De viewer toont authentieke, herleidbare beelden. De kop bevat verantwoordelijke bron/eigenaar, manuscriptnaam/signatuur en folio/canvas waar bekend. Bibliotheek- en wetenschappelijke catalogi zijn voorkeursreferenties; verifieerbare auteurs-/eigenaars-/projectsites en kopieën met een duidelijke herkomstketen zijn eveneens bruikbaar. De gebruiker kan zoomen, pannen, navigeren en een beschikbare beeldrepresentatie kiezen. Transcriptie en vertaling staan in afzonderlijk benoemde panelen; ontbrekende gegevens worden niet door ongemarkeerde AI-invulling vervangen. Een echt document maakt de daarin gedane claims niet automatisch waar.

Overlays verbinden een passage/woord alleen met een regio als de mapping is onderbouwd. Anders opent de app het juiste beschikbare folio zonder een verzonnen precieze highlight. Vermeld of de weergave een origineel bronbestand, thumbnail, crop, tegelweergave of andere afgeleide is. Datering toont methode/toeschrijving en bereik; perkamentdatum en compositiedatum worden niet als hetzelfde gegeven gepresenteerd.

De SourceInspector bevat bron-/cataloguslink, editie/bronrevisie, taal, auteur/vertaler waar bekend, raadpleegtijd, herkomstonderbouwing, attributie, gevonden gebruiksinformatie en beschikbaarheid. De oorspronkelijke bron en eventuele kopieketen blijven bereikbaar. Een bron hoeft geen publieke herdistributielicentie te hebben om persoonlijk te worden geraadpleegd; bekende beperkingen op bewaren, extern verwerken of delen blijven zichtbaar. Waar embedded weergave niet werkt of beperkt is, biedt `Open source` een werkelijke alternatiefroute; bij een institutionele viewer kan het label `Open official viewer` blijven.

| Bewaarlabel | Betekenis voor de gebruiker |
| --- | --- |
| `Local copy retained` | Toegelaten bevestigde bytes zijn duurzaam aanwezig en gekoppeld aan herkomst |
| `Temporary cache` | Tijdelijk beschikbaar; geen garantie voor later offline onderzoek |
| `Remote reference only` | Alleen verwijzing/metadata; online bron blijft nodig |
| `Retention blocked` | Duurzame bewaring is voor deze bron beperkt of niet mogelijk; raadplegen via de bronlink kan beschikbaar blijven |
| `Download failed` / `Storage full` | Bytes zijn niet volledig bevestigd; herstelactie beschikbaar |

Bewaarstatus, deelrecht en inhoudelijke kwaliteit zijn afzonderlijke eigenschappen. Een dossier kan `Saved` zijn terwijl een bronbeeld nog ontbreekt; toon dan bijvoorbeeld `Dossier saved · 1 source unavailable offline`. Dossierpinnen voorkomen stilzwijgende verwijdering door gewone tijdelijke cacheopruiming.

## 8. Roundtable en moderatorbediening

Het scherm toont een deelnemerslijst, chronologische discussie, gedeeld bewijs en ModeratorConsole. Iedere deelnemer heeft een AI-label, persona, perspectief, uitvoerend model/provider en spreekstatus. Een religieus perspectief krijgt een precieze toeschrijving; geen portret of naam die de indruk wekt dat een echte geleerde, geestelijke of profeet meepraat.

Moderatoracties: `Give the floor`, `Ask a round`, `Request evidence`, `Ask to clarify`, `Pause`, `Compare interpretations`, `Summarize differences` en `End round`. Een ronde toont het ingestelde aantal beurten en het budget. Alleen een expliciete opdracht start de betrokken beurten. Een gevraagde volledige ronde mag de afgesproken eindige reeks uitvoeren; zij autoriseert geen eindeloze vervolgrondes.

De gedeelde bewijsversie is zichtbaar. Een nieuw toegelaten bronitem krijgt een veranderingsoverzicht voordat een afhankelijk weerwoord wordt gevraagd. Discussiepunten onderscheiden overeenstemming, verschillende aannames, werkelijk tegenstrijdige claims en ontbrekend bewijs. Samenvatten bewaart deze verschillen.

Nieuwe berichten stelen geen focus of scrollpositie wanneer de gebruiker eerdere inhoud leest. Toon dan een actie om naar nieuwe bijdragen te gaan. Statuswijzigingen worden voor hulptechnologie beheerst aangekondigd, niet iedere gegenereerde token afzonderlijk.

## 9. Roltoewijzing en verbindingen

Het roltoewijzingsscherm scheidt **persona**, **perspectief** en **modelroute**. De tabel toont rol, toewijzing, selectiegrond, automatische/handmatige modus en pin. Een afzonderlijke verbindingenlijst onderscheidt `Not connected`, `Disabled`, `Checking`, `Available` en `Unavailable`.

De orchestrator verdeelt rollen uitsluitend over gekoppelde en ingeschakelde modellen die de benodigde mogelijkheden hebben en passen binnen gegevenskeuze, concrete bronbeperkingen en budget. Niet-beschikbare routes zijn niet selecteerbaar; de reden is inspecteerbaar. Een providerkoppeling maakt niet ieder catalogusmodel beschikbaar. De gebruiker kan een geschikt gekoppeld model proberen zonder voorafgaande expert- of benchmarktoelating. Zonder relevante gebruiksproef heet een voorgestelde match `Provisional`, niet `Best model`; kwaliteitsnotities zijn observaties met datum/configuratie, geen keurmerk.

De gebruiker kan inspecteren, wijzigen en vastzetten. Een uitgevallen vastgezette rol blijft herkenbaar gepauzeerd, ook als een toegestane alternatieve route beschikbaar is. De UI biedt expliciet vrijgeven of opnieuw toewijzen; zolang de pin geldt volgt geen automatische vervanging of modelcall naar een vervanger. Alleen voor niet-vastgezette rollen kan vooraf toegestaan fallbackbeleid een andere toegelaten route kiezen; de verandering wordt getoond. Handmatige hertoewijzing blijft onderworpen aan dezelfde toelatingscontroles. `No eligible model` levert een concrete herstelroute via de eigen instellingen en start geen nieuwe service.

De model-, web- en remote-scanstatus is afzonderlijk zichtbaar in de connection summary of een compacte uitklapbare inspectie. Een cloudgesprek krijgt geen `Fully local`-label. Credentials worden bij setup afgeschermd ingevoerd en niet teruggetoond of in browserstorage bewaard; een statuscontrole toont alleen veilige metadata.

## 10. Dossiers, autosave en delen

Een dossier toont titel, huidige draft/resultaatrevisie, wijzigingstijd, bronbeschikbaarheid en bewaartoestand. Autosave gebeurt gedebounced; `Saved` verschijnt na backendbevestiging. Heranalyse bewaart eerdere resultaten en opent een nieuwe gekoppelde revisie. Een revisieconflict behoudt de lokale invoer en biedt een expliciete keuze voor opnieuw laden of apart bewaren.

De exportflow is: revisie kiezen → persoonlijke inhoud selecteren → opgenomen en uitgesloten bronbestanden bekijken → pakket maken. Persoonlijke notities/discussie worden bewust geselecteerd. Toon per weggelaten object de reden en de bronverwijzing waar beschikbaar. Persoonlijke raadpleging is geen automatische toestemming om een bronbestand verder te verspreiden. Een export bevat geen secrets, ruwe database of ongevraagd volledige geschiedenis. Import toont herkomst en maakt een afzonderlijk dossier.

Een latere deelservice krijgt een aparte publicatieflow met momentopname en leestoegang. Die route wordt niet als werkende knop aangeboden vóór zij bestaat. Intrekken wordt eerlijk uitgelegd als het stoppen van toekomstig ophalen; gedownloade kopieën verdwijnen daardoor niet.

## 11. Systeemtoestanden en foutgedrag

| Toestand | Presentatie | Beschikbare actie |
| --- | --- | --- |
| Geen bronnen/model | Lezen of analyseren alleen voor aanwezige mogelijkheden; concrete beperking | Bron-/modelbeheer openen |
| Running / Verifying | Beknopte fase, afgeronde bronnen, geldend budget en stopactie | Inspecteren, annuleren; geen nep-percentage |
| Awaiting moderator | Volgende deelnemer/ronde met huidige bewijsversie | Menselijke opdracht geven of stoppen |
| Partial / Interrupted | Afgerond werk behouden, exacte ontbrekende stap | Onderbouwd hervatten of nieuwe poging kiezen |
| Provider-/budgetfout | Betrokken rol en reden, status van eerdere poging | Route/budget inspecteren; geen stille herhaling |
| Save failed / Storage full | Lokale conceptinvoer behouden, geen opgeslagenclaim | Opnieuw bewaren, opslag beheren of export indien mogelijk |
| Bron niet bewaarbaar/deelbaar | Concrete beperking bij betrokken object | Oorspronkelijke bron openen of verwijzingen exporteren |

Een bevestigingsdialoog wordt gebruikt bij relevante onomkeerbare gevolgen, bijvoorbeeld definitief verwijderen of publiceren van persoonlijke inhoud. Er komt geen herhaalde toestemming voor al ingestelde modeltoewijzing, gewone autosave of een layoutwissel. Nieuwe gegevensdeling blijft een expliciete gebruikersactie.

## 12. Meertaligheid en responsief gedrag

Engels is de eerste UI-taal, met English, Nederlands, العربية, Français en Deutsch als eerste keuzelijst en uitbreidbare catalogi. Gebruik endoniemen zonder vlaggen. UI-taal, gesprekstaal en bron-/vertaaltaal zijn onafhankelijk. Taalwissel behoudt context en verandert oudere berichten niet ongemerkt.

Arabische UI gebruikt RTL en logische start/eind-layout. Tekstblokken hebben hun eigen taal/richting: Arabische/Hebreeuwse bronpassages blijven RTL in Engelse UI, Engelse vertalingen LTR in Arabische UI. Gemengde referenties, URL's en cijfers worden geïsoleerd. Alleen betekenisvolle richtingiconen worden gespiegeld. Lettervorming, diakritiek, selectie, kopiëren, regelafbreking en fonts worden met echte inhoud getoetst.

Startwaarden voor layoutproeven: vanaf circa 1440 px drie onderzoekszones; circa 960-1439 px twee zones met navigator/dock inklapbaar; kleinere schermen één hoofdzone met bereikbare panelwissel. Chat houdt een comfortabele leesbreedte van ongeveer 680-820 px waar ruimte beschikbaar is. Dit zijn prototypespecificaties om met echte tekst/zoom te toetsen, geen vaste productminima. Context verdwijnt niet wanneer een paneel naar een drawer of tab verhuist.

## 13. Toegankelijkheid en verificatie

WCAG 2.2 AA is het ontwerpdoel, geen al behaalde certificering. Toets onder meer tekstcontrast, reflow/zoom, keyboardbediening, focus, namen/rollen/toestanden, fouten en statusmeldingen in de echte UI. De gekozen vlakke kleuren bewijzen geen conformiteit van componenten. [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

Tabbladen, menu's, dialogen, bronnenlinks en paneelbediening werken zonder muis. Een resizable splitter heeft een toegankelijke naam, bereik/waarde en keyboardbediening; de APG-beschrijving is een ontwerpreferentie die nog met een werkende implementatie moet worden getoetst. [WAI-ARIA splitterpatroon](https://www.w3.org/WAI/ARIA/apg/patterns/windowsplitter/). Dragging is geen enige manier om een panelayout te wijzigen.

Voer echte gebruikersflows uit met gesimuleerde én werkelijke fouttoestanden: tijdelijke Chat naar Research en terug; New research met autosave/herstart; interpretatie naar exacte bron; manuscript met ontbrekende mapping; vastgezet model bij uitval terwijl toegestane fallback beschikbaar is, zonder automatische vervanging en met expliciete herstelactie; moderator die pauzeert; export met geblokkeerd beeld; Arabic RTL met English referenties; toetsenbord en kleine schermen. Registreer observaties en onafgehandelde problemen. Screenshotinspectie en uitsluitend regex-/mocktests vervangen deze verificatie niet.

## 14. Bestaande concepten en implementatieoverdracht

| Concept | Wat het laat zien |
| --- | --- |
| [Chat v4](docs/design/compass-chat-v4.png) | Gewone levensvraag, persona en bronnen op verzoek |
| [Research v4](docs/design/compass-research-v4.png) | Parallelle teksten, bronpaneel, assistent en notities |
| [Theologisch onderzoek v5](docs/design/compass-theology-research-v5.png) | Voorgestelde lezingen, bewijssoorten en open vragen |
| [Roundtable v5](docs/design/compass-theology-roundtable-v5.png) | Deelnemers, gedeeld bewijs en moderatorregie |
| [Routering v5](docs/design/compass-orchestrator-routing-v5.png) | Voorbeeldrolverdeling, demo-koppelingen en pin |

De [ontwerpcatalogus en prompts](docs/design/README.md) bewaren herkomst en beperkingen. Concepten verschillen op details in spacing, knopstijl, tabgroepering en voorbeeldconnectiestatus. Gedeelde componenten en de functionele regels bepalen de consistente implementatie. Demo-verbindingen zijn geen echte accountstatus, voorbeeldlezingen geen uitgevoerde wetenschap en gegenereerde glyphs geen definitieve merkassets. De manuscriptviewer wordt als werkend ontwerp uitgewerkt met echte, herleidbare onlinebronnen.

Bouw eerst een werkende persoonlijke flow: vraag → vergelijking → exacte passage of scan → eigen notitie → bewaren → heropenen. Werk daarbij de benodigde normale, lege, fout- en hersteltoestanden en Engelse/gelokaliseerde teksten uit. Component-/OpenAPI-contracten en bronselectoren groeien mee met die interacties. Behoud de eenvoudige TypeScript- en beperkte lintaanpak. Controleer de flow met enkele representatieve eigen vragen en echte bronnen, inclusief context, tegenbewijs, toetsenbord en RTL. De praktische controles uit V1-V9 helpen fouten vinden; zij vereisen geen groot benchmarkprogramma of externe beoordelingscommissie.
