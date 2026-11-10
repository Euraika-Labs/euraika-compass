import type { Locale } from './types';

const catalog = {
  introduction: ['Enter a topic to start with the team below. You decide who speaks once the roundtable opens.', 'Vul een onderwerp in om met het onderstaande team te starten. Jij bepaalt wie het woord krijgt zodra de rondetafel open is.', 'أدخل موضوعًا للبدء بالفريق أدناه. أنت تختار من يتحدث بعد فتح حلقة النقاش.', 'Saisissez un sujet pour démarrer avec l’équipe ci-dessous. Une fois la table ronde ouverte, vous décidez qui prend la parole.', 'Geben Sie ein Thema ein, um mit dem unten gezeigten Team zu starten. Sobald die Runde eröffnet ist, bestimmen Sie, wer spricht.'],
  topic: ['Roundtable topic', 'Onderwerp van de rondetafel', 'موضوع حلقة النقاش', 'Sujet de la table ronde', 'Thema der Gesprächsrunde'],
  participantName: ['Participant label', 'Naam van de deelnemer', 'اسم المشارك', 'Nom du participant', 'Name des Teilnehmenden'],
  participant: ['AI participant', 'AI-deelnemer', 'مشارك بالذكاء الاصطناعي', 'Participant IA', 'KI-Teilnehmende Person'],
  duplicateNames: ['Give each participant a distinct label.', 'Geef elke deelnemer een eigen naam.', 'أعطِ كل مشارك اسمًا مميزًا.', 'Donnez à chaque participant un nom distinct.', 'Geben Sie jeder teilnehmenden Person einen eindeutigen Namen.'],
  teams: ['Starter teams', 'Vooraf ingestelde teams', 'فرق جاهزة', 'Équipes prédéfinies', 'Vorgeschlagene Teams'],
  teamsHint: ['Optionally switch to a ready-made team for your topic.', 'Kies desgewenst een kant-en-klaar team voor je onderwerp.', 'يمكنك اختيار فريق جاهز يناسب موضوعك.', 'Si vous le souhaitez, choisissez une équipe prête pour votre sujet.', 'Bei Bedarf können Sie ein vorbereitetes Team für Ihr Thema wählen.'],
  customizeParticipants: ['Customize participants', 'Deelnemers aanpassen', 'تخصيص المشاركين', 'Personnaliser les participants', 'Teilnehmende anpassen'],
  quickStartHint: ['Profiles, labels and perspectives are already set. Compass assigns models for automatic roles when you start.', 'Profielen, namen en perspectieven zijn al ingesteld. Compass wijst bij de start modellen toe aan de automatische rollen.', 'الملفات والأسماء والمنظورات معدّة مسبقًا. عند البدء، يعيّن Compass النماذج للأدوار ذات التعيين التلقائي.', 'Les profils, les noms et les perspectives sont déjà définis. Compass affecte les modèles aux rôles automatiques au démarrage.', 'Profile, Namen und Perspektiven sind bereits festgelegt. Beim Start weist Compass den automatischen Rollen Modelle zu.'],
  automaticModelOnStart: ['Automatic model at start', 'Automatisch model bij start', 'اختيار النموذج تلقائيًا عند البدء', 'Modèle choisi au démarrage', 'Automatische Modellwahl beim Start'],
  textContext: ['Text & context', 'Tekst en context', 'النص والسياق', 'Texte et contexte', 'Text und Kontext'],
  compareInterpretations: ['Compare interpretations', 'Interpretaties vergelijken', 'مقارنة التأويلات', 'Comparer les interprétations', 'Auslegungen vergleichen'],
  manuscriptStudy: ['Manuscript study', 'Handschriftonderzoek', 'دراسة المخطوطات', 'Étude des manuscrits', 'Handschriftenstudium'],
  lifeQuestion: ['Life question', 'Levensvraag', 'سؤال حياتي', 'Question de vie', 'Lebensfrage'],
  replaceRoster: ['Replace participants', 'Deelnemers vervangen', 'استبدال المشاركين', 'Remplacer les participants', 'Teilnehmende ersetzen'],
  replaceRosterHint: ['Replace the current participants and their model assignments with this team?', 'Wil je de huidige deelnemers en hun modeltoewijzingen door dit team vervangen?', 'هل تريد استبدال المشاركين الحاليين وتعيينات نماذجهم بهذا الفريق؟', 'Remplacer les participants actuels et leurs modèles assignés par cette équipe ?', 'Die aktuellen Teilnehmenden und ihre Modellzuweisungen durch dieses Team ersetzen?'],
  start: ['Start roundtable', 'Rondetafel starten', 'بدء حلقة النقاش', 'Démarrer la table ronde', 'Gesprächsrunde starten'],
  unavailable: ['Roundtable generation is unavailable in this Compass installation.', 'Rondetafelgesprekken zijn niet beschikbaar in deze Compass-installatie.', 'توليد النقاش غير متاح في تثبيت Compass الحالي.', 'La génération de la table ronde est indisponible dans cette installation de Compass.', 'Die Gesprächsrunden sind in dieser Compass-Installation nicht verfügbar.'],
  chooseSources: ['Choose a collection or a permitted manuscript reading.', 'Kies een collectie of een toegestane handschriftlezing.', 'اختر مجموعة أو قراءة مخطوط مسموحًا بها.', 'Choisissez une collection ou une lecture de manuscrit autorisée.', 'Wählen Sie eine Sammlung oder eine zulässige Handschriftenlesung.'],
  sharedRights: ['Shared evidence must be permitted for every assigned model. Cloud participants limit which sources the room can use.', 'Gedeelde bronnen moeten voor elk toegewezen model zijn toegestaan. Deelnemers met een cloudmodel beperken welke bronnen de rondetafel kan gebruiken.', 'يجب أن تكون الأدلة المشتركة مسموحة لكل نموذج مُعيّن. تحد نماذج السحابة من المصادر المتاحة للحلقة.', 'Les sources partagées doivent être autorisées pour chaque modèle affecté. Les participants cloud limitent les sources utilisables.', 'Gemeinsame Belege müssen für jedes zugewiesene Modell zulässig sein. Cloudmodelle begrenzen die verwendbaren Quellen.'],
  removeRestrictedSources: ['Deselect sources restricted to local processing or assign local models to all participants.', 'Deselecteer bronnen die lokaal moeten blijven of wijs alle deelnemers een lokaal model toe.', 'ألغِ اختيار المصادر المقيّدة بالمعالجة المحلية أو عيّن نماذج محلية لجميع المشاركين.', 'Désélectionnez les sources réservées au traitement local ou attribuez des modèles locaux à tous les participants.', 'Wählen Sie Quellen mit lokaler Verarbeitungsbeschränkung ab oder weisen Sie allen Teilnehmenden lokale Modelle zu.'],
  fixedScope: ['Fixed source scope', 'Vast bronbereik', 'نطاق المصادر الثابت', 'Périmètre de sources fixe', 'Fester Quellenumfang'],
  scopeOnFirstTurn: ['Compass gathers the shared evidence when you ask for the first reply.', 'Compass verzamelt de gedeelde bronnen wanneer je om het eerste antwoord vraagt.', 'يجمع Compass الأدلة المشتركة عندما تطلب الرد الأول.', 'Compass rassemble les sources partagées lorsque vous demandez la première réponse.', 'Compass sammelt die gemeinsamen Belege, sobald Sie um den ersten Beitrag bitten.'],
  moderator: ['Moderator controls', 'Moderatorbediening', 'أدوات إدارة النقاش', 'Commandes de modération', 'Moderationssteuerung'],
  moderatorNote: ['Message to the roundtable', 'Bericht aan de rondetafel', 'رسالة إلى حلقة النقاش', 'Message à la table ronde', 'Nachricht an die Gesprächsrunde'],
  yourMessage: ['You · moderator', 'Jij · moderator', 'أنت · مدير النقاش', 'Vous · modération', 'Sie · Moderation'],
  sendTo: ['Send to', 'Stuur naar', 'إرسال إلى', 'Envoyer à', 'Senden an'],
  everyone: ['Everyone', 'Iedereen', 'الجميع', 'Tout le monde', 'Alle'],
  sendMessage: ['Send message', 'Verstuur bericht', 'إرسال الرسالة', 'Envoyer le message', 'Nachricht senden'],
  giveFloor: ['Give the floor', 'Geef het woord', 'أعطِ الكلمة', 'Donner la parole', 'Das Wort erteilen'],
  roundHint: ['A round gives each available participant one turn in the listed order.', 'In een ronde krijgt elke beschikbare deelnemer één beurt, in de getoonde volgorde.', 'تمنح الجولة كل مشارك متاح مداخلة واحدة بالترتيب المعروض.', 'Un tour donne une intervention à chaque participant disponible dans l’ordre affiché.', 'In einer Runde erhält jede verfügbare Person einen Beitrag in der angezeigten Reihenfolge.'],
  transcript: ['Roundtable transcript', 'Rondetafelgesprek', 'سجل حلقة النقاش', 'Transcription de la table ronde', 'Gesprächsprotokoll'],
  discussion: ['Discussion', 'Gesprek', 'النقاش', 'Discussion', 'Gespräch'],
  noTurns: ['No replies yet. Choose Give the floor for one participant, or Ask a round to hear the team.', 'Er zijn nog geen antwoorden. Geef één deelnemer het woord of vraag een ronde aan om het team te horen.', 'لا توجد ردود بعد. أعطِ الكلمة لمشارك واحد أو اطلب جولة لسماع الفريق.', 'Aucune réponse pour le moment. Donnez la parole à une personne ou demandez un tour pour entendre l’équipe.', 'Es gibt noch keine Beiträge. Erteilen Sie einer Person das Wort oder bitten Sie das Team um eine Runde.'],
  preparingFirstReply: ['Preparing sources and writing the first reply…', 'Bronnen verzamelen en het eerste antwoord schrijven…', 'جارٍ إعداد المصادر وكتابة الرد الأول…', 'Préparation des sources et rédaction de la première réponse…', 'Quellen werden zusammengestellt und der erste Beitrag wird verfasst…'],
  writingFirstReply: ['Writing the first reply…', 'Het eerste antwoord wordt geschreven…', 'جارٍ كتابة الرد الأول…', 'Rédaction de la première réponse…', 'Der erste Beitrag wird verfasst…'],
  writingReply: ['Writing the next reply…', 'Het volgende antwoord wordt geschreven…', 'جارٍ كتابة الرد التالي…', 'Rédaction de la réponse suivante…', 'Der nächste Beitrag wird verfasst…'],
  evidence: ['Shared evidence', 'Gedeelde bronnen', 'الأدلة المشتركة', 'Sources partagées', 'Gemeinsame Belege'],
  evidenceVersion: ['Evidence version', 'Bronversie', 'إصدار الأدلة', 'Version des sources', 'Belegversion'],
  waiting: ['Awaiting moderator', 'Wacht op de moderator', 'بانتظار مدير النقاش', 'En attente de la modération', 'Wartet auf Moderation'],
  running: ['Generating a turn…', 'Beurt wordt opgesteld…', 'جارٍ إعداد المداخلة…', 'Génération d’une intervention…', 'Beitrag wird erstellt…'],
  paused: ['Assignment paused', 'Toewijzing gepauzeerd', 'التعيين متوقف مؤقتًا', 'Affectation suspendue', 'Zuweisung pausiert'],
  stopped: ['Roundtable ended', 'Rondetafel beëindigd', 'انتهت حلقة النقاش', 'Table ronde terminée', 'Gesprächsrunde beendet'],
  pinned: ['Pinned', 'Vastgezet', 'مثبّت', 'Fixé', 'Fixiert'],
  chooseAutomatically: ['Choose automatically', 'Automatisch kiezen', 'اختيار تلقائي', 'Choisir automatiquement', 'Automatisch wählen'],
  automaticHint: ['Compass matches each automatic persona to an eligible connected model. Review the assignments before giving the floor.', 'Compass koppelt elke automatisch toegewezen persona aan een geschikt verbonden model. Bekijk de toewijzingen voordat je iemand het woord geeft.', 'يطابق Compass كل شخصية معيّنة تلقائيًا مع نموذج متصل مؤهل. راجع التعيينات قبل إعطاء الكلمة.', 'Compass associe chaque persona en mode automatique à un modèle connecté admissible. Vérifiez les affectations avant de donner la parole.', 'Compass weist jeder automatisch zugewiesenen Rolle ein geeignetes verbundenes Modell zu. Prüfen Sie die Zuweisungen, bevor Sie das Wort erteilen.'],
  automaticAssignment: ['Automatic assignment', 'Automatisch toegewezen', 'تعيين تلقائي', 'Affectation automatique', 'Automatisch zugewiesen'],
  manualAssignment: ['Manual assignment', 'Handmatig toegewezen', 'تعيين يدوي', 'Affectation manuelle', 'Manuell zugewiesen'],
  basisOrchestrator: ['Provisional fit for this persona', 'Voorlopige inschatting voor deze persona', 'تقدير أولي لملاءمة النموذج لهذه الشخصية', 'Adéquation provisoire pour ce persona', 'Vorläufige Eignung für diese Rolle'],
  basisSingle: ['Only eligible model', 'Enige geschikte model', 'النموذج المؤهل الوحيد', 'Seul modèle admissible', 'Einziges geeignetes Modell'],
  basisConfigured: ['Provisional choice from eligible connections', 'Voorlopige keuze uit geschikte verbindingen', 'اختيار أولي من الاتصالات المؤهلة', 'Choix provisoire parmi les connexions admissibles', 'Vorläufige Wahl aus geeigneten Verbindungen'],
  noEligibleConnection: ['No connected model is eligible for this roundtable. Review your models and source scope.', 'Er is geen geschikt verbonden model voor deze rondetafel. Controleer je modellen en je bronbereik.', 'لا يوجد نموذج متصل مؤهل لهذه الحلقة. راجع النماذج ونطاق المصادر.', 'Aucun modèle connecté ne convient à cette table ronde. Vérifiez les modèles et le périmètre des sources.', 'Für diese Runde ist kein verbundenes Modell geeignet. Prüfen Sie die Modelle und den Quellenumfang.'],
  sourceRestricted: ['This source scope requires local models. Choose a local model or set up a different roundtable.', 'Voor deze bronnen zijn lokale modellen nodig. Kies een lokaal model of stel een andere rondetafel in.', 'يتطلب نطاق المصادر هذا نماذج محلية. اختر نموذجًا محليًا أو أنشئ حلقة نقاش أخرى.', 'Ces sources nécessitent des modèles locaux. Choisissez un modèle local ou configurez une autre table ronde.', 'Dieser Quellenumfang erfordert lokale Modelle. Wählen Sie ein lokales Modell oder richten Sie eine andere Gesprächsrunde ein.'],
  releaseToReassign: ['Unpin and save before changing the model.', 'Hef het vastzetten op en sla op om het model te wijzigen.', 'ألغِ التثبيت واحفظ قبل تغيير النموذج.', 'Libérez le modèle et enregistrez avant de le modifier.', 'Lösen Sie die Fixierung und speichern Sie, bevor Sie das Modell ändern.'],
  changeAssignment: ['Change assignment', 'Toewijzing wijzigen', 'تغيير التعيين', 'Modifier l’affectation', 'Zuweisung ändern'],
  saveAssignment: ['Save assignment', 'Toewijzing bewaren', 'حفظ التعيين', 'Enregistrer l’affectation', 'Zuweisung speichern'],
  synthesis: ['Request synthesis from the next speaker', 'Vraag de volgende spreker om een synthese', 'اطلب توليفًا من المتحدث التالي', 'Demander une synthèse au prochain intervenant', 'Den nächsten Beitrag als Synthese anfordern'],
  synthesisTurn: ['Synthesis', 'Synthese', 'توليف', 'Synthèse', 'Synthese'],
  manuscriptConsent: ['Allow cloud speakers in this turn or round to receive permitted reading excerpts', 'Sta cloudsprekers in deze beurt of ronde toe om toegestane leesfragmenten te ontvangen', 'اسمح لمتحدثي السحابة في هذه المداخلة أو الجولة بتلقي مقتطفات القراءة المسموح بها', 'Autoriser les intervenants cloud de ce tour à recevoir les extraits de lecture permis', 'Erlaubten Lesungsauszügen für Cloudbeiträge in diesem Zug oder dieser Runde zustimmen'],
  cloudTopic: ['Cloud participants receive the topic, moderator instructions and permitted evidence.', 'Clouddeelnemers ontvangen het onderwerp, moderatorinstructies en toegestane bronnen.', 'يتلقى المشاركون السحابيون الموضوع وتعليمات المدير والأدلة المسموح بها.', 'Les participants cloud reçoivent le sujet, les consignes et les sources autorisées.', 'Cloudteilnehmende erhalten Thema, Moderationsanweisungen und erlaubte Belege.'],
  localRoute: ['Local model', 'Lokaal model', 'نموذج محلي', 'Modèle local', 'Lokales Modell'],
  cloudRoute: ['Cloud model', 'Cloudmodel', 'نموذج سحابي', 'Modèle cloud', 'Cloudmodell'],
  webScope: ['Research online when preparing shared evidence', 'Online zoeken bij het samenstellen van de gedeelde bronnen', 'البحث على الإنترنت عند إعداد الأدلة المشتركة', 'Rechercher en ligne lors de la préparation des sources partagées', 'Bei der Vorbereitung gemeinsamer Belege online recherchieren'],
  manuscriptsScope: ['Selected manuscript revisions', 'Gekozen handschriftrevisies', 'مراجعات المخطوطات المختارة', 'Révisions de manuscrits choisies', 'Ausgewählte Handschriftenfassungen'],
  cancelTurn: ['Cancel generation', 'Genereren annuleren', 'إلغاء التوليد', 'Annuler la génération', 'Erstellung abbrechen'],
  end: ['End roundtable', 'Rondetafel beëindigen', 'إنهاء حلقة النقاش', 'Terminer la table ronde', 'Gesprächsrunde beenden'],
  newRoom: ['Set up a new roundtable', 'Nieuwe rondetafel instellen', 'إعداد حلقة نقاش جديدة', 'Configurer une nouvelle table ronde', 'Neue Gesprächsrunde einrichten'],
  refresh: ['Refresh roundtable', 'Rondetafel vernieuwen', 'تحديث حلقة النقاش', 'Actualiser la table ronde', 'Gesprächsrunde aktualisieren'],
  temporary: ['Temporary roundtable', 'Tijdelijke rondetafel', 'حلقة نقاش مؤقتة', 'Table ronde temporaire', 'Temporäre Gesprächsrunde'],
  requestFailed: ['The roundtable action failed. Check the room status or try again.', 'De rondetafelactie is mislukt. Controleer de status of probeer opnieuw.', 'فشل إجراء حلقة النقاش. تحقّق من حالتها أو أعد المحاولة.', 'L’action a échoué. Vérifiez l’état de la table ronde ou réessayez.', 'Die Aktion ist fehlgeschlagen. Prüfen Sie den Status der Runde oder versuchen Sie es erneut.'],
  scopeEdits: ['Start another roundtable to choose a different topic or source scope.', 'Start een nieuwe rondetafel om een ander onderwerp of andere bronnen te kiezen.', 'ابدأ حلقة نقاش أخرى لاختيار موضوع أو نطاق مصادر مختلف.', 'Démarrez une autre table ronde pour changer de sujet ou de périmètre de sources.', 'Starten Sie eine weitere Gesprächsrunde, um Thema oder Quellenumfang zu ändern.'],
} satisfies Record<string, readonly [string, string, string, string, string]>;

export type RoundtableKey = keyof typeof catalog;
const indexes: Record<Locale, number> = { en: 0, nl: 1, ar: 2, fr: 3, de: 4 };
export const roundtableTranslate = (locale: Locale, key: RoundtableKey) => catalog[key][indexes[locale]];

type Localized = readonly [string, string, string, string, string];
const profiles: Record<string, { name?: Localized; method: Localized; perspective: Localized }> = {
  supportive: {
    method: ['Listens with care and offers gentle reflection on loss and uncertainty.', 'Luistert met aandacht en biedt ruimte voor reflectie bij verlies en onzekerheid.', 'يصغي بتعاطف ويفسح مجالًا للتأمل في الفقد وعدم اليقين.', 'Écoute avec attention et invite à réfléchir avec douceur à la perte et à l’incertitude.', 'Hört aufmerksam zu und lädt zur behutsamen Reflexion über Verlust und Unsicherheit ein.'],
    perspective: ['What might offer comfort or room to reflect?', 'Wat kan troost of ruimte voor reflectie bieden?', 'ما الذي قد يمنح بعض العزاء أو يتيح مجالًا للتأمل؟', 'Qu’est-ce qui pourrait apporter du réconfort ou aider à prendre du recul ?', 'Was könnte Trost spenden oder Raum zum Nachdenken geben?'],
  },
  wisdom: {
    method: ['Explores life choices and practical ethical questions through the sources.', 'Verkent levenskeuzes en praktische ethische vragen aan de hand van de bronnen.', 'يستكشف خيارات الحياة والأسئلة الأخلاقية العملية في ضوء المصادر.', 'Explore les choix de vie et les questions éthiques concrètes à partir des sources.', 'Erkundet Lebensentscheidungen und praktische ethische Fragen anhand der Quellen.'],
    perspective: ['What values and practical choices are at stake?', 'Welke waarden en praktische keuzes staan hier op het spel?', 'ما القيم والخيارات العملية المطروحة هنا؟', 'Quels choix concrets et quelles valeurs sont en jeu ?', 'Welche Werte und praktischen Entscheidungen stehen hier auf dem Spiel?'],
  },
  textual: {
    method: ['Examines the wording, edition and immediate context of a passage.', 'Onderzoekt de bewoording, de editie en de directe context van een passage.', 'يفحص صياغة المقطع وطبعته وسياقه المباشر.', 'Examine la formulation, l’édition et le contexte immédiat d’un passage.', 'Untersucht Wortlaut, Ausgabe und unmittelbaren Kontext einer Passage.'],
    perspective: ['What does the passage say in its immediate context?', 'Wat zegt de passage in haar directe context?', 'ماذا يقول المقطع في سياقه المباشر؟', 'Que dit le passage dans son contexte immédiat ?', 'Was sagt die Passage in ihrem unmittelbaren Zusammenhang?'],
  },
  comparative: {
    method: ['Compares readings across traditions and identifies meaningful differences.', 'Vergelijkt lezingen uit verschillende tradities en benoemt betekenisvolle verschillen.', 'يقارن القراءات بين التقاليد ويبيّن الفروق المهمة بينها.', 'Compare les lectures de différentes traditions et relève les différences significatives.', 'Vergleicht Lesarten verschiedener Traditionen und benennt wesentliche Unterschiede.'],
    perspective: ['Where do the traditions converge, and what differences matter?', 'Waar komen de tradities overeen en welke verschillen zijn van belang?', 'أين تتلاقى التقاليد، وما الفروق التي تؤثر في الفهم؟', 'Où les traditions se rejoignent-elles, et quelles différences comptent ?', 'Wo stimmen die Traditionen überein, und welche Unterschiede sind wesentlich?'],
  },
  critical: {
    method: ['Tests assumptions, considers counterarguments and identifies gaps in the evidence.', 'Toetst aannames, bekijkt tegenargumenten en benoemt hiaten in het bronmateriaal.', 'يختبر الافتراضات وينظر في الحجج المضادة ويبيّن الثغرات في الأدلة.', 'Met les hypothèses à l’épreuve, examine les objections et relève les lacunes des sources.', 'Prüft Annahmen, wägt Gegenargumente ab und benennt Lücken in den Belegen.'],
    perspective: ['Which assumptions or counterarguments could change the conclusion?', 'Welke aannames of tegenargumenten kunnen de conclusie veranderen?', 'ما الافتراضات أو الحجج المضادة التي قد تغيّر الاستنتاج؟', 'Quelles hypothèses ou objections pourraient modifier la conclusion ?', 'Welche Annahmen oder Gegenargumente könnten die Schlussfolgerung ändern?'],
  },
  historical: {
    name: ['Historical context researcher', 'Historisch contextonderzoeker', 'باحث في السياق التاريخي', 'Spécialiste du contexte historique', 'Forscher zum historischen Kontext'],
    method: ['Places passages in their historical setting and marks uncertain dates or claims.', 'Plaatst passages in hun historische context en benoemt onzekerheid over dateringen of beweringen.', 'يضع المقاطع في سياقها التاريخي ويبيّن مواضع الشك في التواريخ أو الادعاءات.', 'Replace les passages dans leur contexte historique et signale les datations ou affirmations incertaines.', 'Ordnet Passagen historisch ein und kennzeichnet unsichere Datierungen oder Aussagen.'],
    perspective: ['What can the evidence establish about time, place and audience?', 'Wat tonen de bronnen aan over tijd, plaats en publiek?', 'ما الذي تثبته الأدلة عن الزمان والمكان والجمهور؟', 'Que permettent d’établir les sources sur l’époque, le lieu et le public ?', 'Was belegen die Quellen über Zeit, Ort und Publikum?'],
  },
  philology: {
    name: ['Language and translation analyst', 'Taal- en vertaalanalist', 'محلل اللغة والترجمة', 'Analyste des langues et des traductions', 'Analyst für Sprache und Übersetzung'],
    method: ['Uses available originals to assess word meanings and translation choices.', 'Onderzoekt woordbetekenissen en vertaalkeuzes aan de hand van beschikbare bronteksten.', 'يستعين بالنصوص الأصلية المتاحة لفحص معاني الكلمات وخيارات الترجمة.', 'S’appuie sur les textes originaux disponibles pour étudier le sens des mots et les choix de traduction.', 'Untersucht Wortbedeutungen und Übersetzungsentscheidungen anhand verfügbarer Originaltexte.'],
    perspective: ['Which wording or translation choices could affect the reading?', 'Welke bewoordingen of vertaalkeuzes kunnen de lezing beïnvloeden?', 'ما الألفاظ أو خيارات الترجمة التي قد تؤثر في القراءة؟', 'Quels choix de formulation ou de traduction pourraient influer sur la lecture ?', 'Welche Formulierungen oder Übersetzungsentscheidungen könnten die Lesart beeinflussen?'],
  },
  manuscripts: {
    name: ['Manuscript and transmission analyst', 'Analist van handschriften en tekstoverlevering', 'محلل المخطوطات ونقل النصوص', 'Analyste des manuscrits et de la transmission', 'Analyst für Handschriften und Textüberlieferung'],
    method: ['Distinguishes manuscript witnesses, transcriptions and editions when assessing variants.', 'Maakt bij tekstvarianten onderscheid tussen handschriften, transcripties en edities.', 'يميّز بين شواهد المخطوطات والتفريغات والطبعات عند تقييم اختلافات النص.', 'Distingue les témoins manuscrits, les transcriptions et les éditions pour étudier les variantes.', 'Unterscheidet Handschriften, Transkriptionen und Ausgaben bei der Prüfung von Textvarianten.'],
    perspective: ['What can the surviving witnesses tell us about the history of this reading?', 'Wat vertellen de bewaarde tekstgetuigen over de geschiedenis van deze lezing?', 'ماذا تخبرنا الشواهد الباقية عن تاريخ هذه القراءة؟', 'Que révèlent les témoins conservés sur l’histoire de cette leçon ?', 'Was verraten die erhaltenen Textzeugen über die Geschichte dieser Lesart?'],
  },
  literary: {
    name: ['Literary context analyst', 'Analist van literaire context', 'محلل السياق الأدبي', 'Analyste du contexte littéraire', 'Analyst für literarischen Kontext'],
    method: ['Reads genre, structure and recurring themes in the available wider text.', 'Bekijkt genre, opbouw en terugkerende thema’s in de beschikbare ruimere tekst.', 'يدرس النوع الأدبي والبنية والموضوعات المتكررة في السياق النصي الأوسع المتاح.', 'Étudie le genre, la structure et les thèmes récurrents dans le contexte textuel disponible.', 'Untersucht Gattung, Aufbau und wiederkehrende Themen im verfügbaren größeren Textzusammenhang.'],
    perspective: ['How do genre, structure and recurring themes shape the passage?', 'Hoe geven genre, opbouw en terugkerende thema’s vorm aan de passage?', 'كيف يؤثر النوع الأدبي والبنية والموضوعات المتكررة في فهم المقطع؟', 'Comment le genre, la structure et les thèmes récurrents éclairent-ils le passage ?', 'Wie prägen Gattung, Aufbau und wiederkehrende Themen die Passage?'],
  },
  reception: {
    name: ['History of interpretation researcher', 'Onderzoeker van interpretatiegeschiedenis', 'باحث في تاريخ التأويل', 'Spécialiste de l’histoire des interprétations', 'Forscher zur Auslegungsgeschichte'],
    method: ['Traces how named authors and communities have interpreted a text over time.', 'Volgt hoe benoemde auteurs en gemeenschappen een tekst door de tijd heen hebben uitgelegd.', 'يتتبع كيف فهم النص مؤلفون وجماعات محددة عبر الزمن.', 'Retrace l’évolution des interprétations chez des auteurs et communautés identifiés.', 'Verfolgt die Auslegungen eines Textes durch benannte Autoren und Gemeinschaften im Lauf der Zeit.'],
    perspective: ['Who interpreted this passage in different ways, and what reasons did they give?', 'Wie legde deze passage anders uit en welke redenen gaven zij?', 'من فسّر هذا المقطع بطرق مختلفة، وما الأسباب التي ذكرها؟', 'Qui a interprété ce passage autrement, et quelles raisons ont été avancées ?', 'Wer hat diese Passage unterschiedlich ausgelegt, und welche Gründe wurden dafür genannt?'],
  },
  source_verification: {
    name: ['Source verifier', 'Broncontroleur', 'مدقق المصادر', 'Vérificateur de sources', 'Quellenprüfer'],
    method: ['Checks provenance and how directly each source supports a claim.', 'Controleert de herkomst en hoe direct elke bron een bewering onderbouwt.', 'يتحقق من منشأ المصادر ومدى دعم كل مصدر للادعاء مباشرةً.', 'Vérifie la provenance des sources et dans quelle mesure chacune étaye directement une affirmation.', 'Prüft die Herkunft von Quellen und wie unmittelbar sie eine Aussage stützen.'],
    perspective: ['Which sources support each claim, and what still needs verification?', 'Welke bronnen onderbouwen elke bewering en wat moet nog worden gecontroleerd?', 'ما المصادر التي تدعم كل ادعاء، وما الذي لا يزال يحتاج إلى تحقق؟', 'Quelles sources étayent chaque affirmation, et que reste-t-il à vérifier ?', 'Welche Quellen stützen die einzelnen Aussagen, und was bleibt zu prüfen?'],
  },
};

export function roundtableProfile(locale: Locale, id: string) {
  if (!Object.hasOwn(profiles, id)) return undefined;
  const profile = profiles[id];
  const index = indexes[locale];
  return { name: profile.name?.[index], method: profile.method[index], perspective: profile.perspective[index] };
}
