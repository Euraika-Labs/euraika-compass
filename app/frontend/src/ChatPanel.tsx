import { useEffect, useId, useRef, useState } from 'react';
import { api, ApiError } from './api';
import { chatTranslate } from './chat-i18n';
import { locales, translate } from './i18n';
import { answerSegments, canUseConnection, chatRequest, collections, RequestError } from './research-chat';
import { ParallelPassageReader } from './ParallelPassageReader';
import { WebEvidenceCard, WebResearchStatus } from './WebEvidenceCard';
import { emptyManuscriptSelection, ManuscriptChatSources } from './ManuscriptChatSources';
import { ManuscriptEvidenceCard, ManuscriptReadingStatus } from './ManuscriptEvidenceCard';
import { manuscriptTranslate } from './manuscript-i18n';
import { RoundtablePanel } from './RoundtablePanel';
import type { ChatResponse, ChatSettings, ChatTurn, Citation, Collection, Connection, ConversationRecord, ConversationSummary, CorpusSource, Dossier, Locale, Persona } from './types';

const personaIds = ['supportive', 'wisdom', 'textual', 'comparative', 'critical'] as const;
function citationClass(kind: Citation['kind']) {
  if (kind === 'web') return ' web-citation';
  if (kind === 'manuscript') return ' manuscript-citation';
  return '';
}

export function ChatPanel({ locale, connections, settings, sources, dossiers, personas, ready, webResearchAvailable, roundtableAvailable, draft, setDraft, openConnections, openSources, openResearch }: {
  locale: Locale; connections: Connection[]; settings: ChatSettings | null; sources: CorpusSource[]; personas: Persona[]; ready: boolean;
  dossiers: Dossier[];
  webResearchAvailable: boolean;
  roundtableAvailable: boolean;
  draft: string; setDraft: (value: string) => void; openConnections: () => void; openSources: () => void; openResearch: () => void;
}) {
  const c = (key: Parameters<typeof chatTranslate>[1]) => chatTranslate(locale, key);
  const t = (key: Parameters<typeof translate>[1]) => translate(locale, key);
  const m = (key: Parameters<typeof manuscriptTranslate>[1]) => manuscriptTranslate(locale, key);
  const [connectionId, setConnectionId] = useState('');
  const [persona, setPersona] = useState('supportive');
  const [answerLanguage, setAnswerLanguage] = useState('auto');
  const [webResearch, setWebResearch] = useState(false);
  const [mode, setMode] = useState<'one' | 'roundtable'>('one');
  const [filter, setFilter] = useState<Collection[]>([...collections]);
  const [restrictSources, setRestrictSources] = useState(false);
  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [manuscripts, setManuscripts] = useState(emptyManuscriptSelection);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState('');
  const [stopped, setStopped] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [conversation, setConversation] = useState<ConversationSummary | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveTitle, setSaveTitle] = useState('');
  const request = useRef<AbortController | null>(null);
  const requestVersion = useRef(0);
  const citationPanel = useRef<HTMLElement>(null);
  const citationTrigger = useRef<HTMLElement | null>(null);
  const webResearchHelp = useId();
  const canResearchWeb = ready && webResearchAvailable && settings?.local_only === false;
  const selected = connections.find(item => item.id === connectionId);
  const allowed = (connection: Connection) => canUseConnection(connection, settings);
  const remote = selected?.local === false;
  const sourceDossiers = conversation?.dossier_id ? dossiers.filter(item => item.id === conversation.dossier_id) : dossiers;
  const manuscriptDossier = manuscripts.enabled && sourceDossiers.find(item => item.id === manuscripts.dossierId);
  const manuscriptReady = !!manuscriptDossier && manuscripts.readings.length > 0 && manuscripts.readings.length <= 6;
  const manuscriptPermitted = manuscriptReady && (!remote || (manuscripts.cloudConsent && manuscripts.readings.every(reading => reading.external_processing === true)));
  const hasCorpus = sources.length > 0;
  const useCorpus = hasCorpus && !(manuscripts.enabled && manuscripts.only);
  const corpusReady = useCorpus && filter.length > 0 && (!restrictSources || sourceIds.length > 0);
  const canSend = ready && !busy && !!draft.trim() && !!selected && allowed(selected)
    && (!useCorpus || corpusReady) && (corpusReady || manuscriptPermitted) && (!manuscripts.enabled || manuscriptPermitted);
  const personaOptions = personas.length ? personas.map(item => item.id) : [...personaIds];
  const name = (id: string) => { const known = personaIds.find(item => item === id); return known ? t(known) : personas.find(item => item.id === id)?.name ?? id; };

  useEffect(() => {
    if (!ready) return;
    let ignore = false;
    void api<{ items: ConversationSummary[] }>('/conversations').then(result => { if (!ignore) setConversations(result.items); }).catch(problem => { if (!ignore) setError(problem); });
    return () => { ignore = true; };
  }, [ready]);
  useEffect(() => () => { request.current?.abort(); }, []);
  useEffect(() => { if (citation) citationPanel.current?.focus(); }, [citation]);
  useEffect(() => { if (!canResearchWeb) setWebResearch(false); }, [canResearchWeb]);

  async function send() {
    if (request.current || !canSend || !selected) return;
    const message = draft.trim();
    setBusy('chat'); setError(null); setStopped(false);
    const controller = new AbortController(); request.current = controller;
    const version = ++requestVersion.current;
    try {
      const answer = await api<ChatResponse>('/chat', { method: 'POST', signal: controller.signal, body: JSON.stringify(chatRequest({
        message, connectionId: selected.id, personaId: persona, answerLanguage, turns,
        conversationId: conversation?.id, sessionId, filter: useCorpus ? filter : [],
        sourceIds: !useCorpus ? [] : restrictSources ? sourceIds : undefined,
        webResearch: canResearchWeb && webResearch,
        manuscriptScope: manuscriptDossier ? { dossierId: manuscriptDossier.id, revisionIds: manuscripts.readings.map(item => item.id), allowCloud: remote && manuscripts.cloudConsent } : undefined,
      })) });
      if (version !== requestVersion.current) return;
      setTurns(items => [...items, { ...answer, question: message, id: answer.turn_id ?? crypto.randomUUID() }]);
      if (answer.session_id) setSessionId(answer.session_id);
      setDraft('');
      setWebResearch(false);
      setManuscripts(value => ({ ...value, cloudConsent: false }));
    } catch (problem) {
      if (version !== requestVersion.current) return;
      if (controller.signal.aborted) setStopped(true); else setError(problem);
    } finally { if (version === requestVersion.current) { setBusy(''); request.current = null; } }
  }
  function cancel() { ++requestVersion.current; request.current?.abort(); request.current = null; setBusy(''); setStopped(true); }
  function newChat() { setTurns([]); setConversation(null); setSessionId(undefined); setCitation(null); setError(null); setStopped(false); setSaveOpen(false); setDraft(''); setWebResearch(false); setManuscripts(emptyManuscriptSelection); }
  async function save() {
    if (!saveTitle.trim()) return;
    if (turns.length && !sessionId) { setError(new ApiError('session_expired', 'The temporary server session is no longer available.', 409)); return; }
    setBusy('save'); setError(null);
    try {
      const record = await api<ConversationSummary>('/conversations', { method: 'POST', body: JSON.stringify({ title: saveTitle.trim(), session_id: sessionId }) });
      setConversation(record); setConversations(items => [record, ...items]); setSaveOpen(false); setSaveTitle('');
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }
  async function openConversation(id: string) {
    if (!id) return;
    setBusy('open'); setError(null);
    try {
      const record = await api<ConversationRecord>(`/conversations/${encodeURIComponent(id)}`);
      setConversation(record); setSessionId(undefined); setCitation(null); setStopped(false); setSaveOpen(false); setDraft(''); setWebResearch(false);
      setManuscripts(emptyManuscriptSelection);
      setTurns(record.turns.map(turn => ({
        ...turn,
        grounding: {
          mode: turn.grounding?.mode ?? 'saved',
          retrieved_count: turn.grounding?.retrieved_count ?? 0,
          collections: turn.grounding?.collections ?? [],
          web_research: turn.grounding?.web_research,
          manuscripts: turn.grounding?.manuscripts,
        },
      })));
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }
  function showCitation(value: Citation) { citationTrigger.current = document.activeElement as HTMLElement; setCitation(value); }

  return <section className="chat-view real-chat">
    <div className="section-heading"><div><p className="eyebrow">{conversation ? conversation.title : c('ephemeral')}</p><h1>{t('chat')}</h1></div><div className="segmented-control"><button className={mode === 'one' ? 'active' : ''} disabled={!!busy} onClick={() => setMode('one')}>{t('oneToOne')}</button><button className={mode === 'roundtable' ? 'active' : ''} disabled={!!busy} onClick={() => setMode('roundtable')}>{t('roundtable')}</button></div></div>
    <div hidden={mode !== 'roundtable'}><RoundtablePanel locale={locale} connections={connections} settings={settings}
      sources={sources} dossiers={dossiers} personas={personas} ready={ready} available={roundtableAvailable}
      webResearchAvailable={webResearchAvailable} openConnections={openConnections} openSources={openSources} /></div>
    {mode === 'one' && <>
    <RequestError error={error} locale={locale} manuscriptSearch={manuscripts.enabled} />{stopped && <div className="notice warning" role="status">{c('cancelled')}</div>}
    <div className="chat-tools"><label>{c('chooseConnection')}<select value={connectionId} disabled={!!busy} onChange={event => { setConnectionId(event.target.value); setManuscripts(value => ({ ...value, cloudConsent: false })); }}><option value="">{c('chooseConnection')}</option>{connections.map(item => <option key={item.id} value={item.id} disabled={!allowed(item)}>{item.title} · {item.model_id}{!allowed(item) ? ` · ${!item.local && settings?.local_only !== false ? c('cloudBlocked') : t('unavailable')}` : ''}</option>)}</select></label><label>{t('persona')}<select value={persona} disabled={!!busy} onChange={event => setPersona(event.target.value)}>{personaOptions.map(id => <option key={id} value={id}>{name(id)}</option>)}</select></label><label>{c('answerLanguage')}<select value={answerLanguage} disabled={!!busy} onChange={event => setAnswerLanguage(event.target.value)}><option value="auto">{c('questionLanguage')}</option>{locales.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><button className="text-button" onClick={openConnections}>{c('connections')}</button></div>
    {!connections.some(allowed) && <div className="notice"><span>{c(connections.length ? 'noReadyConnections' : 'noConnections')}</span><button className="text-button" onClick={openConnections}>{c('connections')}</button></div>}
      <details className="panel grounding-controls" open={!hasCorpus || undefined}>
        <summary>{c('grounding')}</summary>
        {useCorpus && <><fieldset disabled={!!busy}><legend>{c('collections')}</legend><div className="collection-options">{collections.map(id => <label className="checkbox-label" key={id}><input type="checkbox" checked={filter.includes(id)} onChange={event => setFilter(items => event.target.checked ? [...items, id] : items.filter(item => item !== id))} />{c(id)}</label>)}</div></fieldset>{!filter.length && <p className="inline-warning">{c('noCollections')}</p>}
        <label className="checkbox-label"><input type="checkbox" checked={restrictSources} disabled={!!busy} onChange={event => setRestrictSources(event.target.checked)} />{c('selectedSources')}</label>{restrictSources ? <div className="source-options">{sources.map(source => <label className="checkbox-label" key={source.id}><input type="checkbox" checked={sourceIds.includes(source.id)} disabled={!!busy} onChange={event => setSourceIds(items => event.target.checked ? [...items, source.id] : items.filter(id => id !== source.id))} />{source.title}</label>)}</div> : <p className="helper">{c('allSources')}</p>}</>}
        <ManuscriptChatSources locale={locale} dossiers={sourceDossiers} selection={manuscripts} onChange={setManuscripts}
          remote={remote} disabled={!!busy || !ready} hasCorpus={hasCorpus} />
        <button className="text-button" onClick={openSources}>{c('sources')}</button>
      </details>
      {!hasCorpus && !manuscriptReady && <div className="notice"><span>{m('chooseEvidence')}</span><button className="text-button" onClick={openSources}>{c('sources')}</button></div>}
      <div className="chat-reading-layout"><div className="chat-thread" aria-label={t('chat')}>
        {!turns.length && (useCorpus || manuscriptReady) && <p className="chat-intro">{useCorpus ? c('chatIntro') : m('readingChatIntro')}</p>}
        {turns.map(turn => <article className="chat-turn" key={turn.id}>
          <div className="user-message" dir="auto">{turn.question}</div>
          <div className="assistant-message" dir="auto">{answerSegments(turn.answer, turn.citations).map((segment, index) => {
            const source = segment.citation;
            if (!source) return <span key={index}>{segment.text}</span>;
            return <button className={`citation-button${citationClass(source.kind)}`} key={index} onClick={() => showCitation(source)}>{segment.text}</button>;
          })}</div>
          <div className="turn-meta">
            <code>{turn.model_id}</code>
            {turn.grounding.mode !== 'saved' && <span>{c('evidenceCount')}: {turn.grounding.retrieved_count}{turn.grounding.collections.length > 0 && ` · ${turn.grounding.collections.map(id => c(id)).join(' · ')}`}</span>}
          </div>
          {turn.grounding.web_research && <WebResearchStatus research={turn.grounding.web_research} locale={locale} />}
          {turn.grounding.manuscripts && <ManuscriptReadingStatus evidence={turn.grounding.manuscripts} locale={locale} />}
          {turn.citations.length > 0 && <div className="citation-list">
            {turn.citations.map(item => <button className={`citation-chip${citationClass(item.kind)}`} key={item.id} onClick={() => showCitation(item)}>
              [{item.id}] {item.kind === 'web' ? <>{c('webEvidence')} · <bdi>{item.title}</bdi></> : item.kind === 'manuscript' ? <>{m('manuscriptEvidence')} · <bdi>{item.reference}</bdi></> : <bdi>{item.reference}</bdi>}
            </button>)}
          </div>}
          {turn.warnings.length > 0 && <details className="turn-warnings">
            <summary>{c('warnings')} ({turn.warnings.length})</summary>
            <ul>{turn.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
          </details>}
        </article>)}
      </div>{citation && <aside ref={citationPanel} tabIndex={-1} className="panel citation-panel" aria-label={c('citationDetails')}>
        <div className="panel-heading">
          <h2>{c('citationDetails')} [{citation.id}]</h2>
          <button className="text-button" onClick={() => { setCitation(null); citationTrigger.current?.focus(); }}>{c('close')}</button>
        </div>
        {citation.kind === 'web' ? <WebEvidenceCard citation={citation} locale={locale} />
          : citation.kind === 'manuscript' ? <ManuscriptEvidenceCard key={citation.transcription_id} citation={citation} locale={locale} /> : <>
          <ParallelPassageReader key={citation.passage_id} snapshot={citation} locale={locale} cited />
          <p className="helper">{c('citationCaveat')}</p>
        </>}
      </aside>}</div>
      <form className="chat-composer" onSubmit={event => { event.preventDefault(); void send(); }}>
        <label htmlFor="chat-draft" className="sr-only">{t('question')}</label>
        <textarea id="chat-draft" value={draft} onChange={event => setDraft(event.target.value)} disabled={!!busy} placeholder={t('chatPlaceholder')} dir="auto" rows={4} />
        <div className="web-research-controls">
          <label className="checkbox-label">
            <input type="checkbox" checked={canResearchWeb && webResearch} disabled={!canResearchWeb || !!busy}
              aria-describedby={webResearchHelp} onChange={event => setWebResearch(event.target.checked)} />
            {c('webResearch')}
          </label>
          <p id={webResearchHelp} className="helper">
            {c(!webResearchAvailable ? 'webNotConfigured' : settings?.local_only !== false ? 'webLocalOnly' : 'webResearchHint')}
          </p>
        </div>
        <div className="composer-footer">
          <span className="muted">{conversation ? c('savedConversation') : c('ephemeral')}</span>
          <div className="button-row">
            <button type="button" className="button quiet" onClick={openResearch}>{t('openResearch')} ↗</button>
            {busy === 'chat' ? <button type="button" className="button secondary" onClick={cancel}>{c('cancel')}</button>
              : <button className="button primary" disabled={!canSend}>{c('ask')}</button>}
          </div>
        </div>
        {busy === 'chat' && <p role="status" className="helper">{c('asking')}</p>}
      </form>
      <div className="conversation-actions"><button className="button secondary" disabled={!!busy} onClick={newChat}>{c('newChat')}</button>{!conversation && <button className="button secondary" disabled={!ready || !!busy} onClick={() => setSaveOpen(value => !value)}>{c('saveFuture')}</button>}{conversations.length > 0 && <label>{c('conversations')}<select value={conversation?.id ?? ''} disabled={!!busy} onChange={event => void openConversation(event.target.value)}><option value="">—</option>{conversations.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}</div>
      {saveOpen && !conversation && <form className="panel save-conversation" onSubmit={event => { event.preventDefault(); void save(); }}><p className="helper">{c('futureHint')}</p><label>{c('conversationTitle')}<input required maxLength={200} value={saveTitle} onChange={event => setSaveTitle(event.target.value)} /></label><button className="button primary" disabled={!ready || !!busy || !saveTitle.trim()}>{c('saveFuture')}</button></form>}
    </>}
  </section>;
}
