import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from './api';
import { AnswerText, CitationChips, CitationPanel } from './ChatEvidence';
import { chatTranslate } from './chat-i18n';
import { locales, translate } from './i18n';
import { ManuscriptReadingStatus } from './ManuscriptEvidenceCard';
import { canUseConnection } from './research-chat';
import { roundtableTranslate } from './roundtable-i18n';
import type { RoundtableKey } from './roundtable-i18n';
import { roundtablePersonaName, RoundtableRequestError, RoundtableSetup } from './RoundtableSetup';
import type { RoundtableSetupProps } from './RoundtableSetup';
import type { Citation, RoundtableParticipant, RoundtableRoom } from './types';
import { WebResearchStatus } from './WebEvidenceCard';

type SetupProps = Omit<RoundtableSetupProps, 'onCreated'>;
type Assignment = { participantId: string; connectionId: string; pinned: boolean };
const allocationBasisKeys = {
  orchestrator: 'basisOrchestrator', single_candidate: 'basisSingle', configured_order: 'basisConfigured',
} as const;

export function RoundtablePanel(props: SetupProps) {
  const [room, setRoom] = useState<RoundtableRoom | null>(null);
  return <div className="roundtable-workspace">
    <div hidden={!!room}><RoundtableSetup {...props} onCreated={setRoom} /></div>
    {room && <RoundtableSession key={room.id} initialRoom={room} {...props} onNew={() => setRoom(null)} />}
  </div>;
}

function RoundtableSession({ initialRoom, locale, connections, settings, sources, dossiers, personas, openConnections, onNew }: SetupProps & {
  initialRoom: RoundtableRoom; onNew: () => void;
}) {
  const r = (key: RoundtableKey) => roundtableTranslate(locale, key);
  const t = (key: Parameters<typeof translate>[1]) => translate(locale, key);
  const c = (key: Parameters<typeof chatTranslate>[1]) => chatTranslate(locale, key);
  const [room, setRoom] = useState(initialRoom);
  const [note, setNote] = useState('');
  const [synthesis, setSynthesis] = useState(false);
  const [consent, setConsent] = useState(false);
  const [citation, setCitation] = useState<Citation | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [running, setRunning] = useState(false);
  const [requestedSpeaker, setRequestedSpeaker] = useState('');
  const [control, setControl] = useState('');
  const [needsSync, setNeedsSync] = useState(false);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const generation = useRef<AbortController | null>(null);
  const controlling = useRef(false);
  const stopped = room.status === 'stopped';
  const working = running || room.status === 'running';
  const locked = working || !!control || needsSync;
  const base = `/roundtables/${encodeURIComponent(room.id)}`;
  const activeSpeaker = room.active_participant_id || requestedSpeaker;
  const hasManuscripts = room.evidence_version === null ? !!room.scope.manuscript_dossier_id : room.evidence.some(item => item.kind === 'manuscript');
  const dossier = dossiers.find(item => item.id === room.scope.manuscript_dossier_id);
  const currentLanguage = locales.find(item => item.id === room.language);
  const readyConnections = connections.filter(connection => canUseConnection(connection, settings));

  function routeAvailable(participant: RoundtableParticipant) {
    const connection = connections.find(item => item.id === participant.connection_id);
    return !!connection && canUseConnection(connection, settings)
      && connection.provider === participant.provider && connection.model_id === participant.model_id;
  }
  function canSpeak(participant: RoundtableParticipant) {
    return participant.status === 'ready' && routeAvailable(participant);
  }
  const eligible = room.participants.filter(canSpeak);
  const consentNeeded = (speakers: RoundtableParticipant[]) => hasManuscripts
    && (room.evidence_version === null ? room.participants : speakers).some(item => !item.local);
  const cloudConsentNeeded = consentNeeded(eligible);

  useEffect(() => () => { generation.current?.abort(); }, []);
  useEffect(() => {
    const operation = generation.current;
    if (!running || !operation) return;
    let inFlight = false;
    const timer = window.setInterval(async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const snapshot = await api<RoundtableRoom>(base, { signal: operation.signal });
        if (generation.current === operation) setRoom(snapshot);
      } catch { /* The action response is the primary source of room status. */ }
      finally { inFlight = false; }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [base, running]);

  async function speak(participants: RoundtableParticipant[], round = false) {
    if (stopped || locked || generation.current || controlling.current || !participants.length || participants.some(item => !canSpeak(item))) return;
    const needsConsent = consentNeeded(participants);
    if (needsConsent && !consent) return;
    const operation = new AbortController();
    generation.current = operation;
    setError(null);
    setRunning(true);
    setRequestedSpeaker(round ? '' : participants[0].id);
    const payload = {
      ...(round ? { participant_ids: participants.map(item => item.id) } : { participant_id: participants[0].id, synthesis }),
      moderator_note: note.trim() || undefined,
      expected_revision: room.revision,
      allow_manuscript_cloud: needsConsent && consent,
    };
    setConsent(false);
    try {
      const response = await api<{ room: RoundtableRoom }>(`${base}/${round ? 'rounds' : 'turns'}`, {
        method: 'POST', signal: operation.signal, body: JSON.stringify(payload),
      });
      if (generation.current !== operation) return;
      setRoom(response.room);
      setNote('');
      setSynthesis(false);
    } catch (problem) {
      if (generation.current !== operation || operation.signal.aborted) return;
      setError(problem);
      try {
        const snapshot = await api<RoundtableRoom>(base, { signal: operation.signal });
        if (generation.current === operation) setRoom(snapshot);
      } catch { if (generation.current === operation) setNeedsSync(true); }
    } finally {
      if (generation.current === operation) {
        generation.current = null;
        setRunning(false);
        setRequestedSpeaker('');
      }
    }
  }

  async function updateRoom(action: 'cancel' | 'stop' | 'refresh' | 'assignment') {
    if (controlling.current || (action === 'assignment' && (locked || stopped || !assignment))) return;
    controlling.current = true;
    setControl(action);
    setError(null);
    if (action === 'cancel' || action === 'stop') {
      const operation = generation.current;
      generation.current = null;
      operation?.abort();
      setConsent(false);
    }
    try {
      let snapshot: RoundtableRoom;
      if (action === 'assignment' && assignment) {
        snapshot = await api<RoundtableRoom>(`${base}/participants/${encodeURIComponent(assignment.participantId)}`, {
          method: 'PATCH', body: JSON.stringify({ connection_id: assignment.connectionId || null, pinned: assignment.pinned, expected_revision: room.revision }),
        });
        setAssignment(null);
        setConsent(false);
      } else {
        snapshot = await api<RoundtableRoom>(action === 'refresh' ? base : `${base}/${action}`, action === 'refresh' ? {} : { method: 'POST' });
      }
      setRoom(snapshot);
      setNeedsSync(false);
    } catch (problem) {
      setError(problem);
      try {
        setRoom(await api<RoundtableRoom>(base));
        setNeedsSync(false);
      } catch { setNeedsSync(true); }
    } finally {
      controlling.current = false;
      setControl('');
      setRunning(false);
      setRequestedSpeaker('');
    }
  }

  return <section className="roundtable-room">
    <header className="panel roundtable-room-header">
      <div><p className="eyebrow">{r('temporary')}</p><h2 dir="auto">{room.topic}</h2></div>
      <p className="pill" role="status">{r(stopped ? 'stopped' : working ? 'running' : 'waiting')}</p>
    </header>
    <RoundtableRequestError error={error} locale={locale} manuscriptSearch={hasManuscripts} />
    {needsSync && <p className="notice warning" role="alert">{r('requestFailed')}</p>}
    <details className="panel roundtable-scope">
      <summary>{r('fixedScope')}</summary>
      <p className="helper">{r('scopeEdits')}</p>
      <dl>
        <dt>{c('answerLanguage')}</dt><dd>{currentLanguage?.label ?? (room.language === 'auto' ? c('questionLanguage') : room.language)}</dd>
        {room.scope.collection_filter.length > 0 && <><dt>{c('collections')}</dt><dd>{room.scope.collection_filter.map(item => c(item)).join(' · ')}</dd></>}
        {!!room.scope.source_ids?.length && <><dt>{c('sources')}</dt><dd>{room.scope.source_ids.map(id => sources.find(item => item.id === id)?.title ?? id).join(' · ')}</dd></>}
        {room.scope.manuscript_dossier_id && <><dt>{r('manuscriptsScope')}</dt><dd>{dossier?.title ?? room.scope.manuscript_dossier_id} · {room.scope.manuscript_revision_ids?.length ?? 0}</dd></>}
        <dt>{r('webScope')}</dt><dd>{c(room.scope.web_research ? 'webUsed' : 'webOff')}</dd>
      </dl>
      <p className="helper">{r('sharedRights')}</p>
    </details>
    <div className="roundtable-moderator panel">
      <div className="panel-heading"><h2>{r('moderator')}</h2><div className="button-row">
        <button type="button" className="button secondary" disabled={!!control || running} onClick={() => void updateRoom('refresh')}>{r('refresh')}</button>
        {working && !stopped && <button type="button" className="button secondary" disabled={!!control} onClick={() => void updateRoom('cancel')}>{r('cancelTurn')}</button>}
        {!stopped && <button type="button" className="button secondary" disabled={!!control} onClick={() => void updateRoom('stop')}>{r('end')}</button>}
        {stopped && <button type="button" className="button primary" onClick={onNew}>{r('newRoom')}</button>}
      </div></div>
      {!stopped && <>
        {room.participants.some(participant => !participant.local) && <p className="helper">{r('cloudTopic')}</p>}
        <label>{r('moderatorNote')}<textarea dir="auto" rows={2} value={note} maxLength={2000} disabled={locked} onChange={event => setNote(event.target.value)} /></label>
        {room.turns.length >= 2 && <label className="checkbox-label"><input type="checkbox" checked={synthesis} disabled={locked}
          onChange={event => setSynthesis(event.target.checked)} />{r('synthesis')}</label>}
        {cloudConsentNeeded && <label className="checkbox-label"><input type="checkbox" checked={consent} disabled={locked}
          onChange={event => setConsent(event.target.checked)} />{r('manuscriptConsent')}</label>}
        <div className="button-row"><button type="button" className="button secondary" disabled={locked || synthesis || !eligible.length || (cloudConsentNeeded && !consent)}
          onClick={() => void speak(eligible, true)}>{t('askRound')}</button>
          <span className="helper">{r('roundHint')}{eligible.length > 0 && <> <bdi>{eligible.map(item => item.name).join(' · ')}</bdi></>}</span></div>
      </>}
    </div>
    <section className="roundtable-roster" aria-label={t('participants')}>
      {room.participants.map(participant => {
        const paused = participant.status === 'paused' || !routeAvailable(participant);
        const speaking = working && activeSpeaker === participant.id;
        const edit = assignment?.participantId === participant.id ? assignment : null;
        const canSave = edit && (participant.pinned && !edit.pinned
          || (edit.connectionId ? readyConnections.some(connection => connection.id === edit.connectionId) : readyConnections.length > 0));
        const basis = participant.allocation_basis;
        return <article className="panel roundtable-speaker" key={participant.id}>
          <div className="panel-heading"><h3 dir="auto">{participant.name}</h3>{participant.pinned && <span className="pill">{r('pinned')}</span>}</div>
          <p className="helper">{r('participant')} · {roundtablePersonaName(participant.persona_id, personas, locale)}</p>
          {participant.perspective && <p className="muted" dir="auto">{participant.perspective}</p>}
          <p className="helper"><bdi>{participant.provider} · {participant.model_id}</bdi> · {r(participant.local ? 'localRoute' : 'cloudRoute')}</p>
          <p className="helper">{r(participant.allocation === 'automatic' ? 'automaticAssignment' : 'manualAssignment')}
            {basis && basis !== 'moderator' && <> · {r(allocationBasisKeys[basis])}</>}</p>
          {speaking && <p className="helper" role="status">{r('running')}</p>}
          {paused && <p className="inline-warning">{r('paused')}{participant.last_error?.code && <> · <code>{participant.last_error.code}</code></>}</p>}
          {!stopped && <div className="button-row">
            <button type="button" className="button primary" aria-label={`${r('giveFloor')} · ${participant.name}`} disabled={locked || !canSpeak(participant) || (consentNeeded([participant]) && !consent)}
              onClick={() => void speak([participant])}>{r('giveFloor')}</button>
            <button type="button" className="text-button" aria-label={`${r('changeAssignment')} · ${participant.name}`} disabled={locked}
              onClick={() => setAssignment({ participantId: participant.id, connectionId: participant.connection_id, pinned: participant.pinned })}>{r('changeAssignment')}</button>
          </div>}
          {!stopped && edit && <form className="roundtable-assignment" onSubmit={event => { event.preventDefault(); if (canSave) void updateRoom('assignment'); }}>
            <label>{t('model')}<select value={edit.connectionId} disabled={locked || participant.pinned}
              onChange={event => setAssignment({ ...edit, connectionId: event.target.value, pinned: !!event.target.value && edit.pinned })}>
              <option value="">{r('chooseAutomatically')}</option>
              {!connections.some(connection => connection.id === participant.connection_id) && <option value={participant.connection_id} disabled>{participant.model_id}</option>}
              {connections.map(connection => <option key={connection.id} value={connection.id} disabled={!canUseConnection(connection, settings)}>{connection.title} · {connection.model_id}</option>)}
            </select></label>
            <label className="checkbox-label"><input type="checkbox" checked={edit.pinned} disabled={locked || !edit.connectionId} onChange={event => setAssignment({ ...edit, pinned: event.target.checked })} />{t('pin')}</label>
            {participant.pinned && <p className="helper">{r('releaseToReassign')}</p>}
            <div className="button-row"><button className="button secondary" disabled={locked || !canSave}>{r('saveAssignment')}</button>
              <button type="button" className="button quiet" onClick={() => setAssignment(null)}>{t('cancel')}</button></div>
          </form>}
        </article>;
      })}
    </section>
    {eligible.length === 0 && !working && !stopped && <div className="notice"><span>{c('noReadyConnections')}</span><button type="button" className="text-button" onClick={openConnections}>{c('connections')}</button></div>}
    <section className="panel roundtable-evidence" aria-label={r('evidence')}>
      <div className="panel-heading"><h2>{r('evidence')}</h2>{room.evidence_version !== null && <span className="pill">{r('evidenceVersion')} {room.evidence_version}</span>}</div>
      {room.evidence_version === null && <p className="helper">{r('scopeOnFirstTurn')}</p>}
      <CitationChips citations={room.evidence} locale={locale} onCitation={setCitation} />
      {room.evidence_sha256 && <details className="passage-hash"><summary>SHA-256</summary><code dir="ltr">{room.evidence_sha256}</code></details>}
    </section>
    <section className="roundtable-transcript" aria-label={r('transcript')}>
      <h2>{r('transcript')}</h2>
      {room.turns.length === 0 && !stopped && <p className="helper">{r('noTurns')}</p>}
      {room.turns.map(turn => <article className="panel roundtable-turn" key={turn.id}>
        <div className="panel-heading"><h3 dir="auto">{room.participants.find(item => item.id === turn.participant_id)?.name ?? turn.participant_id}</h3>
          {turn.synthesis && <span className="pill">{r('synthesisTurn')}</span>}</div>
        {turn.moderator_note && <p className="helper">{r('noteLabel')} · <bdi>{turn.moderator_note}</bdi></p>}
        <AnswerText answer={turn.answer} citations={turn.citations} onCitation={setCitation} />
        <div className="turn-meta"><code>{turn.model_id}</code></div>
        {turn.grounding?.web_research && <WebResearchStatus research={turn.grounding.web_research} locale={locale} />}
        {turn.grounding?.manuscripts && <ManuscriptReadingStatus evidence={turn.grounding.manuscripts} locale={locale} />}
        <CitationChips citations={turn.citations} locale={locale} onCitation={setCitation} />
        {turn.warnings.length > 0 && <details className="turn-warnings"><summary>{c('warnings')} ({turn.warnings.length})</summary>
          <ul>{turn.warnings.map((warning, index) => <li key={index} dir="auto">{warning}</li>)}</ul></details>}
      </article>)}
    </section>
    {citation && <CitationPanel citation={citation} locale={locale} onClose={() => setCitation(null)} />}
    {error instanceof ApiError && <code className="sr-only">{error.code}</code>}
  </section>;
}
