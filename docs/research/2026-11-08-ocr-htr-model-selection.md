# Tekst lezen uit oude Hebreeuwse, Griekse en Arabische beelden

Onderzocht op 8 november 2026 voor Euraika Compass: persoonlijk, neutraal theologisch onderzoek. Dit is een onderbouwde modelshortlist, geen gemeten ranglijst op onze eigen foto's. Er zijn geen modellen geïnstalleerd, gewichten gedownload, API-keys bekeken of betaalde inferentieaanroepen gedaan.

## Aanbevolen start

Begin lokaal met **Kraken 7.1 en het historische PP-OCRv6-medium-model**, plus verwisselbare schrift-/periodeprofielen. Vergelijk moeilijke uitsneden met een lokaal **Qwen3.8-27B-visionmodel**. Houd **Mistral OCR 4.1** beschikbaar als gekozen cloudlezer voor pagina's en één gekoppeld algemeen visionmodel als extra leesmogelijkheid. De beste lezer wordt per materiaal gekozen; lokaal is niet alleen een noodroute.

De hardware is tijdens dit onderzoek daadwerkelijk uitgelezen: NVIDIA GeForce RTX 5090, 32.607 MiB VRAM, driver 610.88. Dat maakt grotere lokale beeldmodellen een reële proefoptie. Bestandsgrootte alleen bewijst niet dat een model met elke beeldresolutie en context in het GPU-geheugen past.

Drie vragen blijven gescheiden: waar staan de tekstregels, welke tekens zijn zichtbaar, en wat betekent de gelezen tekst? Een historische taallabel is geen garantie voor ieder schrift, iedere periode of beschadigde foto. De onderstaande keuze is daarom een startprofiel dat de gebruiker met eigen beelden kan verbeteren.

## Lokale historische herkenning

| Kandidaat | Waarom relevant | Grenzen en praktische rol |
| --- | --- | --- |
| **Kraken 7.1 + PP-OCRv6 medium**, model `10.5281/zenodo.21788410` | Regelherkenner voor historische en moderne hand-/drukschriften; 15,92 miljoen parameters, circa 63,8 MB gewichten, Apache-2.0. De modelkaart noemt werkelijk Grieks, Hebreeuws en Arabisch. | Eerste algemene lokale historische lezer, samen met lijnsegmentatie. Transcriptieconventies zijn gemengd; afkortingen en glyphs kunnen onvoorspelbaar worden uitgewerkt. De voorspelling blijft controleerbaar naast het beeld. [Modelkaart](https://zenodo.org/records/21788410). |
| **BiblIA_01**, `10.5281/zenodo.5468286` | Circa 16,1 MB; gericht op middeleeuwse Ashkenazische, Italiaanse en Sefardische Hebreeuwse boekhanden. | Specialistische vergelijking bij zo'n hand; geen aangetoonde Dode-Zeerollen- of paleo-Hebreeuwse lezer. Modelmetadata vermeldt CC BY-SA 4.0; de bijbehorende dataset heeft een afzonderlijke CC BY-NC-SA 4.0-licentie. [Model](https://zenodo.org/records/5468286), [auteursproject en segmentatie](https://github.com/dstoekl/sofer_mahir), [dataset](https://zenodo.org/records/5167263). |
| **Meleagre-NFD-finetuned**, `10.5281/zenodo.10912724` | Herkenner circa 22,5 MB met circa 5,1 MB segmentatiemodel, CC BY 4.0; gemaakt voor tiende-eeuwse Byzantijnse minuskel in Palatinus graecus 23. | Proberen bij passend Grieks handschrift; geen universeel model voor unciaal, papyri of inscripties. [Auteursmodel](https://zenodo.org/records/10912724), [onderzoeksworkshop](https://dhtr25.anthologiagraeca.org/materials/). |
| **Muharaf-Kraken**, `muharaf_rec_best.mlmodel` | Circa 20,1 MB, CC BY 4.0 volgens recordmetadata; getraind op divers historisch cursief Arabisch uit archivalisch materiaal. | Transparante specialistische vergelijking voor cursieve documenten. Niet aangetoond goed op vroege Hidjazi-/Koefische Koranhandschriften. [Modelrecord](https://zenodo.org/records/14295489), [datasetpaper](https://arxiv.org/abs/2406.09630). |
| **Archatext/HTR_model_Finetued_Arams-28k** | Circa 12 MB, CC BY-NC-SA 4.0; Muharaf-afgeleide voor historische Arabische manuscripten, met een gedocumenteerd Kraken 5.3.0-profiel. | Aanvullend profiel; kaart noemt handschriftverschillen, diakritiek en segmentatie als beperkingen. Niet als algemene gedrukte Arabische lezer bedoeld. [Modelkaart](https://huggingface.co/Archatext/HTR_model_Finetued_Arams-28k). |

De makers rapporteren voor de nieuwe Kraken-medium-basis een tekenfoutpercentage van **5,06% Hebreeuws, 7,21% Ancient Greek en 9,38% Arabisch** op hun eigen verzamelde testmateriaal. Dat motiveert een echte proef, maar is geen prestatiebelofte voor onze foto's. Een lage tekenfout betekent ook niet foutloze woorden: voor die Griekse proef wordt 44,03% woordfout gerapporteerd. De dekking en transcriptieconventies verschillen per corpus. [Kraken 7.1-release](https://github.com/mittagessen/kraken/releases/tag/7.1).

**Kraken is een engine, niet één manuscriptmodel.** Lijnsegmentatie en herkenning zijn afzonderlijke stappen; ALTO/PageXML en echte regio-informatie passen bij onze beeld/transcriptiewerkruimte. eScriptorium is een omgeving rond Kraken en hoeft niet als een tweede volledige UI te worden ingebouwd. Compass kan een headless worker aansturen. [Kraken-documentatie](https://kraken.re/main/), [uitvoerformaten](https://kraken.re/5.0.0/advanced.html).

De huidige officiële installatiehandleiding noemt Linux/macOS en Python 3.10–3.13. Voor Windows is een geïsoleerde WSL/Linux-worker daarom de eerste te onderzoeken route; een native Windows-installatie wordt niet als bewezen gepresenteerd. De Compass-webapp en PostgreSQL hoeven daarvoor niet geheel naar WSL. Oude `.mlmodel`-gewichten moeten met de gebruikte Kraken-versie worden gecontroleerd; een bestaand profiel mag een eigen compatibele workeromgeving krijgen. [Installatiehandleiding](https://kraken.re/main/getting_started.html).

## Lokaal algemeen visionmodel

**Qwen/Qwen3.8-27B** is de eerste zwaardere lokale visionkandidaat voor moeilijke uitsneden, alternatieve letterlezingen en onderzoek over het beeld. Het officiële model heeft beeld-/videoinvoer en Apache-2.0-gewichten. Dat bewijst nog geen bijzondere nauwkeurigheid op oude Hebreeuwse, Griekse of vroege Arabische handen. Gebruik het eerst als zelfstandige tweede lezer van dezelfde pixels. [Officiële modelkaart](https://huggingface.co/Qwen/Qwen3.8-27B).

Voor de RTX 5090 is **Q5_K_M GGUF met de bijbehorende visionprojector** een bruikbare eerste geheugenproef: de onderzochte quantisatie is circa 20,92 GB en de f16-projector circa 0,928 GB. Dat is ongeveer 21,85 GB aan bestanden, exclusief contextcache, beeldtokens en runtimebuffers. Q4_K_M is circa 17,44 GB als extra ruimte nodig is. Deze afgeleide bestanden komen van een herkenbare quantiseerder, niet rechtstreeks van Qwen; herkomst en hash blijven onderdeel van de configuratie. Compatibele llama.cpp-versie en projector zijn vereist. [Quantisatiekaart en bestanden](https://huggingface.co/bartowski/Qwen3.8-27B-GGUF).

Begin met korte context en een geselecteerde regel of uitsnede. Meet werkelijk geheugen en leesgedrag voordat volle pagina's of meerdere taken tegelijk worden geladen. Een hogere quantisatie is niet automatisch een betere lezer dan een kleiner model op hogere precisie. **Qwen3.5-9B met vision** blijft een lichtere vergelijkingsoptie; neem geen tekst-only conversie zonder beeldcomponent aan als visionroute. [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B).

## Andere lokale OCR-kandidaten

| Kandidaat | Nuttige toepassing | Waarom niet de eerste algemene handschriftkeuze |
| --- | --- | --- |
| **Tesseract 5 + tessdata_best** | Eenvoudige lokale vergelijking voor gedrukte edities; echte `grc`, `heb` en `ara`-modellen, hOCR/TSV-uitvoer, Apache-2.0. | De eigen FAQ noemt handschrift een zwak punt. Een Ancient-Greek-drukmodel is geen papyruslezer. [Talen](https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files-in-different-versions.md), [FAQ](https://tesseract-ocr.github.io/tessdoc/FAQ.html). |
| **Surya 2.5**, `datalab-to/surya-ocr-2.5` | Algemene OCR en lay-out, plus een afzonderlijke tekstregeldetector; Grieks, Hebreeuws en Arabisch staan in de taaltabel. Circa 689M parameters. Code Apache-2.0; gewichten hebben een aangepaste AI Pubs Open Rail-M-licentie met persoonlijk/onderzoeksgebruik. | De taaltest bewijst geen historische manuscriptkwaliteit. Blok-/regelcoördinaten zijn geen automatische woordcoördinaten. De huidige volledige route heeft een afzonderlijke inferencebackend; begin niet met extra infrastructuur als Kraken-segmentatie volstaat. [Repository](https://github.com/datalab-to/surya), [taaltabel](https://github.com/datalab-to/surya/blob/master/static/docs/multilingual.md), [model](https://huggingface.co/datalab-to/surya-ocr-2.5). |
| **PaddleOCR-VL-1.6**, 0.9B | Compacte Apache-2.0-documentparser met lay-out en tekstspotting; relevante vergelijkingsoptie voor drukwerk en pagina's. | De gepubliceerde lijst noemt Grieks/Arabisch, geen Hebreeuws. De genoemde verbetering op oude documenten betreft Chinees, geen bewijs voor onze drie schrifttradities. De losse VLM is niet de volledige paginaparser. [Modelkaart](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6), [taaldekking](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL.html). |

Paddle heeft een afzonderlijke RTX-Blackwell-installatieroute; algemene oudere CUDA-voorbeelden zijn geen bewezen 5090-configuratie. Sommige inferencebackends draaien niet native op Windows. Dit is extra reden eerst één gerichte historische worker werkend te maken. [Blackwell-handleiding](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL-NVIDIA-Blackwell.html), [backendmatrix](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html).

**GLM-OCR** komt niet vooraan: de officiële kaart noemt acht talen zonder Hebreeuws, Grieks of Arabisch. **DeepSeek-OCR-2** is een optioneel experiment; de gevonden documentatie geeft geen specifieke historische-doelschriftresultaten en het installatievoorbeeld bewijst geen Windows/Blackwell-route. **LightOnOCR-2** is een interessante compacte documentlezer, maar algemene documentbenchmarks onderbouwen deze oude-schriftkeuze niet; de bbox-variant noemt kaders voor afbeeldingen, niet automatisch tekstwoorden. [GLM-kaart](https://huggingface.co/zai-org/GLM-OCR/raw/main/README.md), [DeepSeek-repo](https://github.com/deepseek-ai/DeepSeek-OCR-2), [LightOn-kaart](https://huggingface.co/lightonai/LightOnOCR-2-1B).

## Gekoppelde OCR- en visionroutes

Dit zijn actuele cataloguskandidaten. De app is nog niet gebouwd en account-/regiotoegang is niet gecontroleerd. Alleen door de gebruiker geconfigureerde, ingeschakelde en beeldgeschikte routes zijn selecteerbaar.

| Route | Geschikte rol in Compass | Wat niet uit de documentatie volgt |
| --- | --- | --- |
| **Mistral OCR 4.1**, `mistral-ocr-4-1` | Dedicated cloudlezer voor pagina's en lay-out. Native alinea-/blokcoördinaten, labels en confidencevelden; de OCR-taallijst noemt Hebreeuws, Grieks en Arabisch. | Geen bewezen specialist voor de oude handschriftstijlen. Een alineabox is geen exacte woordbox. [Model](https://docs.mistral.ai/models/ocr-4-1), [blokuitvoer](https://docs.mistral.ai/studio/document-processing/basic_ocr), [talen](https://docs.mistral.ai/resources/languages). |
| **Alibaba Qwen-OCR**, `qwen3.5-ocr` | Vergelijkingsroute voor Arabische documenten en echte tekstlokalisatie; OCR met regelcoördinaten. | De expliciete multilingual-tasklijst noemt Arabisch, maar geen Grieks/Hebreeuws. Geen voldoende basis voor één universele historische OCR-route. [Officiële OCR-handleiding](https://www.alibabacloud.com/help/en/model-studio/qwen-vl-ocr). |
| **Alibaba Qwen3.8-Max**, `qwen3.8-max` | Algemeen visionmodel voor een gekozen moeilijke uitsnede, als de route binnen het account beschikbaar is. | Geen gegarandeerde OCR-geometrie of aangetoonde historische-schriftranglijst. [Modelpagina](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-max). |
| **Claude Sonnet 5.5 / Opus 5.5** | Een extra lezing van een geselecteerde regel of lettergroep. De actuele model-IDs zijn `claude-sonnet-5-5` en `claude-opus-5-5`. | Grote beelden worden verkleind en coördinaten zijn benaderingen; geen basis voor precieze woordoverlays. [Modellen](https://platform.claude.com/docs/en/models/overview), [vision](https://platform.claude.com/docs/en/build-with-claude/vision). |
| **OpenAI GPT-6 Astra**, `gpt-6-astra` | Extra lezer voor kleine tekstuitsneden; `detail: original` is expliciet gedocumenteerd voor deze route. | Beeldinvoer is geen bewijs van specialistische manuscriptkwaliteit; kleine/niet-Latijnse tekst en beeldrotatie blijven foutbronnen. [Model](https://developers.openai.com/api/docs/models/gpt-6-astra), [beeldhandleiding](https://developers.openai.com/api/docs/guides/images-vision). |

Een bruikbare eerste cloudintegratie is Mistral voor pagina-structuur, naast één gekozen algemeen visionmodel voor lastige uitsneden. Er is geen reden iedere foto door alle providers te sturen. De Mistral-modelkaart vermeldt bij deze controle $4 per 1.000 OCR-pagina's en $5 per 1.000 geannoteerde pagina's; andere routes rekenen beeld-/teksttokens en instellingen anders af. Dat is geen gelijkwaardige prijsvergelijking. [Mistral-prijskaart](https://docs.mistral.ai/models/ocr-4-1).

OpenRouter is een gateway naar een werkelijke model-/providerroute en voegt geen nieuwe leeskwaliteit toe. Pin die upstream-route wanneer hij wordt gebruikt. MiniMax biedt beeldtools, maar de onderzochte documentatie geeft geen reden die boven de genoemde historische/OCR-kandidaten te plaatsen. [OpenRouter-providerkeuze](https://openrouter.ai/docs/guides/routing/provider-selection), [MiniMax-beeldtool](https://platform.minimax.io/docs/guides/token-plan-mcp-guide).

## Keuze per materiaal

| Materiaal | Eerste lokale proef | Tweede proef of vergelijking |
| --- | --- | --- |
| Onbekende historische hand | Kraken-medium met echte lijnsegmentatie | Qwen3.8-27B op geselecteerde uitsneden |
| Passend middeleeuws Hebreeuws | BiblIA naast Kraken-medium | Zelfstandige lokale of gekozen cloudvisionlezing |
| Byzantijnse Griekse minuskel | Meleagre naast Kraken-medium | Zelfde uitsnede vergelijken, diakritiek apart bekijken |
| Historisch cursief Arabisch | Muharaf en eventueel AraMS-profiel naast Kraken-medium | Qwen-vision; Qwen-OCR of Mistral voor een gekozen pagina |
| Paleo-Hebreeuws, vroeg Hidjazi/Koefisch, unciaal of beschadigde papyrus | Geen model automatisch als passende specialist bestempelen | Enkele onafhankelijke leesvoorstellen naast het beeld, bestaande transcriptie pas als gelabelde vergelijking |

Deze routering is een ontwerpafleiding uit de trainingsdomeinen en interfaces. Zij blijft wijzigbaar op basis van eigen foto's. Een grotere API of een lokaal domeinmodel krijgt geen automatische voorkeur door modelnaam of omvang.

## Praktische proef en weergave

Begin met enkele werkelijk relevante pagina's en uitsneden: duidelijk en moeilijk materiaal, verschillende handen, ontbrekende tekens, RTL/diakritiek en een gedraaide opname. Er is geen vaste benchmarkomvang of panel vereist. Vergelijk per voorbeeld:

- zichtbare tekens, diakritiek en afkortingen; geen stilzwijgende modernisering;
- gemiste/dubbele regels en echte regio-/leesvolgorde;
- onterecht aangevulde letters of woorden en expliciet behouden onzekerheid;
- benodigde eigen correcties en bruikbaarheid naast de foto;
- werkelijke wachttijd, geheugen en eventuele kosten.

Laat een tweede beeldmodel eerst zelfstandig lezen, zonder de eerste transcriptie of een vermoed vers als correct antwoord mee te geven. Toon daarna verschillen naast de pixels. De Kraken-basis bevat deels dezelfde datasets als specialistische modellen; onderlinge overeenstemming is dus ook geen onafhankelijk historisch getuigenis. Bewaar ruwe uitvoer en bewerkingen, en normaliseer alleen afgeleide zoektekst. NFD-/NFC-verschil mag niet ongemerkt betekenisvolle diakritiek verwijderen.

Beeldlezen volgt de bestaande R28-regels: origineel, automatische lezing, eigen correctie, reconstructie en vertaling blijven gescheiden. Een OCR-score is geen kans dat een historische uitspraak waar is. Cloudgebruik is een ingestelde beeldverwerkingskeuze; lokale modus heeft geen stille cloudfallback. Bewaar bij iedere poging route, versie, inputhash, regio en werkelijk gebruikte afmetingen. Een cloud- of modelcatalogus zegt niets over feitelijke toegang onder onze accounts.

## Eerstvolgende bouwstap

Maak één lokale Kraken-worker met medium en één passend specialistisch profiel toegankelijk vanuit de Compass-transcriptieadapter. Onderzoek op Windows eerst de geïsoleerde Linux/WSL-route. Voeg vervolgens de lokale Qwen-visionroute toe met projector en beperkte context. Mistral en één andere bestaande visionverbinding blijven expliciete vergelijkingsopties. Pas na die echte proef worden modelbestanden, runtimeversies en een handige standaard vastgezet.
