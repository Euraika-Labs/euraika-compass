# Euraika Compass — Productvisie

Status: richtinggevend productdocument, 8 november 2026. De visie beschrijft de ambitie en principes. [functional.md](functional.md) bepaalt het concrete functionele gedrag; het [implementatieplan](docs/plans/2026-11-08-1552-feat-religion-research-app-plan.md) beschrijft bouw en verificatie. Genoemde mogelijkheden zijn voorgenomen, geen verklaring dat de app al werkt.

## Visie

Euraika Compass is een neutrale theologische onderzoekstool voor persoonlijk gebruik. De gebruiker onderzoekt de Thora, Bijbel en Koran, vergelijkt teksten en interpretaties en weegt zelf argumenten af. AI helpt bronnen vinden en analyseren; de gebruiker bepaalt de vraag, onderzoeksrichting en conclusie.

De gebruiker moet kunnen volgen hoe een antwoord ontstaat: vanuit een benoemde tekst, in samenhang met andere passages, met historische en taalkundige onderbouwing en ruimte voor verschillende lezingen. Het uitgangspunt is een bruikbare onderzoekswerkbank met praktische kwaliteitscontroles. Een geloofspositie of een theologische uitkomst wordt niet vooraf ingebouwd.

De werkbank moet ook tekst uit foto's en scans kunnen helpen lezen. De gebruiker kan een eigen opname of een gevonden manuscriptbeeld openen, een gebied selecteren, een voorgestelde transcriptie naast het beeld controleren en corrigeren, en daarna vertalen of verder onderzoeken. Beeldlezen hoort bij de kern; onleesbare tekens en onzekere lezingen blijven zichtbaar.

Diezelfde omgeving biedt plaats aan een persoonlijke vraag over verlies, verantwoordelijkheid, vergeving of zingeving. De gebruiker kiest hoe diep het gesprek gaat en kan vanuit een eenvoudige reflectie doorstappen naar de teksten, manuscripten en argumenten erachter.

## Missie

We verbinden zelfstandig theologisch onderzoek met toegankelijke gesprekken en controleerbare bronnen. AI helpt relevante gegevens te vinden, taal te onderzoeken, perspectieven te vergelijken en argumenten te toetsen. De gebruiker houdt zeggenschap over de vraag, de onderzoeksrichting, de modelverbindingen en de betekenis die hij of zij aan de uitkomst geeft.

Onze bijdrage is geslaagd wanneer mensen beter kunnen begrijpen wat een bron zegt, waarom interpretaties verschillen en waarop hun eigen afweging berust.

## Voor wie we bouwen

De eerste versie is een persoonlijke onderzoeksomgeving. De opensourcecode kan door anderen worden gebruikt, maar een centrale dienst, institutionele certificering en een beoordelingsorganisatie zijn geen voorwaarden voor deze app.

- Mensen die levensvragen willen bespreken en inzichten uit de drie tekstcollecties willen verkennen, met behoud van hun eigen overtuiging en autonomie.
- Nieuwsgierige lezers die oorspronkelijke teksten, vertalingen en historische handschriften willen bekijken zonder eerst een volledig onderzoeksinstrumentarium te moeten beheersen.
- Studenten, onderzoekers en andere kritische gebruikers die bronverwijzingen, tekstvarianten, historische aannames en interpretatieve argumenten willen kunnen controleren.
- Gebruikers die meerdere AI-perspectieven willen bevragen en zelf het gesprek tussen die perspectieven willen modereren.

De eerste ervaring moet uitnodigend zijn voor een gewone vraag. Geavanceerde functies worden bereikbaar wanneer de gebruiker verder wil onderzoeken.

## Het probleem dat we aanpakken

Een overtuigend geformuleerd antwoord kan tekst, vertaling, latere uitleg en modelveronderstellingen door elkaar halen. Een geïsoleerd citaat kan de context verliezen. Digitale tekstcollecties en manuscriptcatalogi bevatten waardevolle gegevens, maar vragen vaak veel voorkennis en handmatig zoekwerk. Een persoonlijke vraag vraagt bovendien om een andere benadering dan een tekstkritisch probleem.

Euraika Compass brengt die behoeften bij elkaar met twee verbonden ervaringen: een leesbare Chat en een inspecteerbare Research-werkruimte. De verbinding tussen beide moet het mogelijk maken eerst een gesprek te voeren en vervolgens zelf de onderbouwing te bekijken.

## Principes die onze keuzes sturen

### 1. Primaire bronnen en hun herkomst blijven zichtbaar

Een gebruiker moet kunnen teruggaan naar de benoemde teksteditie, het echte manuscript of de oorspronkelijke onlinepublicatie. Alle authentieke en herleidbare onlinebronnen kunnen voor persoonlijk onderzoek worden gebruikt: bibliotheekcollecties, wetenschappelijke publicaties, auteurspagina's, projectrepositories en andere identificeerbare publicaties. Institutionele en wetenschappelijke bronnen zijn belangrijke referenties, zonder een exclusieve toegangspoort te vormen.

Scan, transcriptie, reconstructie, vertaling en interpretatie blijven herkenbaar. Authenticiteit betekent dat duidelijk is wat het materiaal is en waar het vandaan komt; zij bewijst niet dat iedere bewering of interpretatie erin waar is. Herkomst, methode en beperkingen bepalen welk gewicht een bron in het argument krijgt.

Een eigen foto kan persoonlijk worden onderzocht wanneer de objectherkomst nog onbekend is. De app bewaart dat onderscheid: tekstherkenning bewijst geen ouderdom, authenticiteit of auteurschap. Het oorspronkelijke beeld, automatische lezing en eigen correctie blijven afzonderlijk terug te vinden; ontbrekende tekst wordt niet stilzwijgend uit een bekende schriftpassage aangevuld.

### 2. Dezelfde zorgvuldigheid voor iedere collectie

Thora, Bijbel en Koran krijgen dezelfde bewijsregels, kritische aandacht en respectvolle behandeling. Hun eigen tekstcontext en werkelijke verschillen blijven behouden. Onpartijdigheid ontstaat door controleerbare werkwijzen en toetsing; zij wordt niet bewezen door gelijke aantallen citaten of door een model dat zichzelf neutraal noemt.

### 3. Context bepaalt wat een argument kan dragen

We onderzoeken de omliggende passage, relevante verbanden binnen de gekozen collectie, taalgebruik en de historische setting. Ondersteunende passages en tegenbewijs horen beide bij het onderzoek. De app maakt duidelijk welke context daadwerkelijk is onderzocht en waar de dekking ophoudt.

### 4. Interpretaties moeten uitlegbaar zijn

Een lezing wordt gekoppeld aan gegevens en aannames: wat is waargenomen, welke historische hypothese speelt mee en welke conclusie volgt daar mogelijk uit? De gebruiker moet begrijpen waarom lezingen uiteenlopen en waarom een argument sterker of zwakker is. Onzekerheid en open vragen zijn waardevolle onderzoeksuitkomsten.

Wetenschappelijke zorgvuldigheid vraagt om toetsbare argumenten en ruimte voor correctie. Zij rechtvaardigt geen belofte dat elke theologische vraag één definitief bewezen antwoord heeft.

### 5. Latere autoriteit wordt niet stilzwijgend ingevoerd

Commentaren en overleveringen worden van primaire teksten onderscheiden. Een interpretatie kan worden beschreven en vergeleken zonder haar als gezaghebbende waarheid over te nemen. De gedeelde primaire-tekstgerichte bronregels gelden voor alle collecties. De specifieke hadithuitsluiting en beperkte contextuele toelatingsvoorwaarden staan in [functional.md](functional.md); geen standaard hadithpakket maakt deel uit van de visie.

### 6. De mens houdt de regie

Een persona helpt bij een bepaalde manier van luisteren of onderzoeken. Een Roundtable maakt verschillende argumenten zichtbaar onder menselijke moderatie. De gebruiker bepaalt wie spreekt, welke bronnen worden bevraagd en wanneer een synthese gewenst is. Een modelmeerderheid geeft een conclusie geen historisch bewijs.

Persoonlijke gesprekken bewaren de ruimte voor verdriet, twijfel en eigen keuzes. De app oefent geen bekeringsdruk uit en claimt geen kennis van Gods bedoelingen of het lot van een overleden persoon.

### 7. Modellen zijn verwisselbare hulpmiddelen

We willen de bruikbaarste mogelijkheden van krachtige cloudmodellen combineren met lokale bron-, zoek- en taalhulpmiddelen. Roltoewijzing volgt de taak, mogelijkheden, voorkeuren en de door de gebruiker ingeschakelde verbindingen. Praktische proefvragen maken sterke en zwakke kanten zichtbaar; een voorafgaand deskundigenpanel is geen voorwaarde om een gekoppeld model te gebruiken.

Meerdere modellen leveren meer onderzoekshoeken, maar kunnen ook dezelfde fouten delen. Bronnen en controleerbare argumenten blijven bepalend. De gebruiker kan uitkomsten controleren en corrigeren; deskundige beoordeling kan helpen wanneer een vraag die expertise vraagt.

### 8. Toegankelijkheid en controle horen bij kwaliteit

De bediening start in het Engels en wordt meertalig, met onder meer Nederlands, Arabisch, Frans en Duits. Brontaal, gesprekstaal en interfacetaal zijn afzonderlijke keuzes. Ondersteuning van Arabisch en Hebreeuws omvat hun leesrichting en tekstkenmerken. Gebruikers moeten ook met toetsenbord en op kleinere schermen kunnen werken.

De gebruiker kiest cloudverwerking, webonderzoek en remote manuscripttoegang bewust en ziet wat lokaal blijft of extern wordt verwerkt. Dossiers worden bewust bewaard. Persoonlijk raadplegen is het uitgangspunt; praktische informatie over lokale bewaring, cloudverwerking en delen blijft aan de bron gekoppeld. Online beschikbaarheid wordt niet als algemene toestemming voor herpublicatie of training opgevat en toegang wordt niet omzeild.

## Hoe we prioriteiten stellen

Wanneer bronbewijs ontbreekt, begrenzen we de conclusie en tonen we de lacune. Wanneer een nieuw model een betere formulering levert, onderzoeken we ook of brongetrouwheid, onpartijdigheid en kosten verbeteren. Wanneer een scherm veel mogelijkheden bevat, bewaren we een eenvoudige route voor de gebruiker die alleen een gesprek wil voeren.

Een uitbreiding verdient voorrang wanneer zij het begrip, de controleerbaarheid of de autonomie van de gebruiker aantoonbaar verbetert. De hoeveelheid modellen, tools of gegenereerde tekst is op zichzelf geen succesmaat.

## Ambitie op langere termijn

We willen groeien naar een meertalige onderzoeksomgeving waarin teksten, manuscripten, taalgegevens en interpretatieve argumenten verbonden zijn. Een gebruiker kan een vraag stellen, de relevante getuigen en context inspecteren, verschillende perspectieven laten reageren en het resultaat met zijn beperkingen opnieuw openen.

Die groei gebeurt door authentieke bronnen toe te voegen en nieuwe model-/taalmogelijkheden praktisch uit te proberen. De app registreert herkomst, geconstateerde beperkingen en relevante gebruiksvoorwaarden. Samenwerking aan opensourcecode, broncorrecties en voorbeelden kan het product beter controleerbaar maken.

Voor de eerste bruikbare persoonlijke versie hebben de bestaande Chat/Research-scope, manuscriptweergave, tekstlezen uit foto's/scans, bewijs- en interpretatieonderzoek en gemodereerde Roundtable prioriteit. We controleren echte bronnen en gebruikersflows met een kleine gevarieerde verzameling proefvragen. Er is geen verplicht grootschalig benchmarkprogramma of minimumaantal deskundigenbeoordelingen. Verdere uitbreidingen zoals audio en meerdere menselijke accounts vragen afzonderlijke beslissingen en tests. De bruikbaarheid van een beeldlezer verschilt per schrift, handschrift en beeldkwaliteit en wordt met echte voorbeelden nagegaan.

## Waaraan we succes herkennen

- Een gebruiker kan de tekst en bron achter een inhoudelijke uitspraak terugvinden en controleren.
- Een gebruiker kan tekst uit een foto naast het oorspronkelijke beeld controleren, corrigeren en verder onderzoeken, met behouden onzekere tekens en bronherkomst.
- Een vergelijking verklaart verschillen met argumenten en houdt relevante onzekerheid zichtbaar.
- Een persoonlijke reflectie wordt als behulpzaam en respectvol beoordeeld, zonder druk of ongegronde zekerheid.
- Een moderator kan een AI-discussie volgen, onderbreken en op bewijs laten terugkomen.
- Dezelfde toetsing vindt fouten en ongelijke behandeling over collecties, persona's en talen heen, met zichtbare correcties en beperkingen.
- Een dossier maakt duidelijk wat destijds is onderzocht, welke bronnen en modellen werden gebruikt en wat bij heranalyse verandert.
- Onderzoek kan met behoud van herkomst en bronrechten worden heropend of bewust gedeeld; een toegelaten gebruikte bronkopie blijft beschikbaar voor latere controle.

Deze uitkomsten worden met praktische broncontroles, gerichte proefvragen en echte gebruikersflows onderzocht. De controles richten zich op terugvindbare citaten, context en tegenbewijs, toegeschreven interpretaties, eerlijke beperkingen en betrouwbaar bewaren. Bevindingen en correcties blijven eenvoudig terug te vinden; vloeiende antwoorden of overeenstemming tussen modellen maken verdere controle niet overbodig.
