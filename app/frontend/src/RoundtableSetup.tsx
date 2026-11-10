import { useId, useRef, useState } from 'react';
import { api, ApiError } from './api';
import { chatTranslate } from './chat-i18n';
import { locales, translate } from './i18n';
import { emptyManuscriptSelection, ManuscriptChatSources } from './ManuscriptChatSources';
import { canUseConnection, collections, RequestError } from './research-chat';
import { roundtableProfile, roundtableTranslate } from './roundtable-i18n';
import type { RoundtableKey } from './roundtable-i18n';
import type { ChatSettings, Collection, Connection, CorpusSource, Dossier, Locale, Persona, RoundtableRoom, RoundtableScope } from './types';

const personaIds = ['supportive', 'wisdom', 'textual', 'comparative', 'critical'] as const;
const teams = {
  textContext: ['textual', 'historical', 'literary'],
  compareInterpretations: ['comparative', 'reception', 'critical'],
  manuscriptStudy: ['manuscripts', 'philology', 'source_verification'],
  lifeQuestion: ['supportive', 'wisdom', 'comparative'],
} satisfies Partial<Record<RoundtableKey, string[]>>;
type Team = keyof typeof teams;
type ParticipantDraft = { id: number; name: string; persona_id: string; connection_id: string; perspective: string; pinned: boolean };
const newParticipant = (id: number, persona_id: string): ParticipantDraft => ({ id, name: '', persona_id, connection_id: '', perspective: '', pinned: false });

export function roundtablePersonaName(id: string, personas: Persona[], locale: Locale) {
  const known = personaIds.find(item => item === id);
  return known ? translate(locale, known) : roundtableProfile(locale, id)?.name ?? personas.find(item => item.id === id)?.name ?? id;
}

function participantNames(participants: ParticipantDraft[], personas: Persona[], locale: Locale) {
  const used = new Set(participants.flatMap(participant => {
    const label = participant.name.trim().toLocaleLowerCase(locale);
    return label ? [label] : [];
  }));
  return participants.map(participant => {
    if (participant.name.trim()) return participant.name.trim();
    const profile = roundtablePersonaName(participant.persona_id, personas, locale);
    let label = profile;
    let suffix = 2;
    while (used.has(label.toLocaleLowerCase(locale))) label = `${profile} ${suffix++}`;
    used.add(label.toLocaleLowerCase(locale));
    return label;
  });
}

const routingErrorKeys: Partial<Record<string, RoundtableKey>> = {
  roundtable_no_eligible_connection: 'noEligibleConnection', roundtable_source_restricted: 'sourceRestricted',
};

export function RoundtableRequestError({ error, locale, manuscriptSearch }: Parameters<typeof RequestError>[0]) {
  const routingError = error instanceof ApiError && routingErrorKeys[error.code];
  if (routingError) return <p className="notice warning" role="alert">{roundtableTranslate(locale, routingError)}</p>;
  return <RequestError error={error} locale={locale} manuscriptSearch={manuscriptSearch} />;
}

export interface RoundtableSetupProps {
  locale: Locale; connections: Connection[]; settings: ChatSettings | null; sources: CorpusSource[];
  dossiers: Dossier[]; personas: Persona[]; ready: boolean; available: boolean; webResearchAvailable: boolean;
  openConnections: () => void; openSources: () => void; onCreated: (room: RoundtableRoom) => void;
}

export function RoundtableSetup({ locale, connections, settings, sources, dossiers, personas, ready, available, webResearchAvailable,
  openConnections, openSources, onCreated }: RoundtableSetupProps) {
  const r = (key: RoundtableKey) => roundtableTranslate(locale, key);
  const t = (key: Parameters<typeof translate>[1]) => translate(locale, key);
  const c = (key: Parameters<typeof chatTranslate>[1]) => chatTranslate(locale, key);
  const [topic, setTopic] = useState('');
  const [language, setLanguage] = useState('auto');
  const [participants, setParticipants] = useState(() => [newParticipant(1, 'textual'), newParticipant(2, 'critical')]);
  const [rosterEdited, setRosterEdited] = useState(false);
  const [pendingTeam, setPendingTeam] = useState<Team | null>(null);
  const [filter, setFilter] = useState<Collection[]>([...collections]);
  const [restrictSources, setRestrictSources] = useState(false);
  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [manuscripts, setManuscripts] = useState(emptyManuscriptSelection);
  const [webResearch, setWebResearch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const creating = useRef(false);
  const nextId = useRef(3);
  const descriptionId = useId();
  const hasCorpus = sources.length > 0;
  const useCorpus = hasCorpus && filter.length > 0 && !(manuscripts.enabled && manuscripts.only);
  const canWeb = webResearchAvailable && settings?.local_only === false;
  const useWeb = canWeb && webResearch;
  const readyConnections = connections.filter(connection => canUseConnection(connection, settings));
  const assigned = participants.map(participant => connections.find(connection => connection.id === participant.connection_id));
  const remote = assigned.some(connection => connection?.local === false);
  const hasAutomatic = participants.some(participant => !participant.connection_id);
  const names = participantNames(participants, personas, locale);
  const defaultPerspectives = participants.map(({ persona_id }) => roundtableProfile(locale, persona_id)?.perspective
    ?? personas.find(item => item.id === persona_id)?.description ?? '');
  const perspectives = participants.map((participant, index) => participant.perspective.trim() || defaultPerspectives[index]);
  const distinct = new Set(names.map(name => name.toLocaleLowerCase(locale))).size === names.length;
  const validManuscripts = manuscripts.enabled && dossiers.some(dossier => dossier.id === manuscripts.dossierId)
    && manuscripts.readings.length > 0 && manuscripts.readings.length <= 6
    && (!remote || manuscripts.readings.every(reading => reading.external_processing === true));
  const validCorpus = useCorpus && sources.some(source => (!restrictSources || sourceIds.includes(source.id))
    && (!remote || source.use_limits.external_processing === true)
    && source.editions.some(edition => edition.collection_memberships.some(collection => filter.includes(collection))));
  const restrictedSharedSource = remote && useCorpus && restrictSources && sources.some(source =>
    sourceIds.includes(source.id) && source.use_limits.external_processing !== true);
  const hasEvidence = validCorpus || validManuscripts || useWeb;
  const canStart = ready && available && !busy && !!topic.trim() && distinct && participants.length >= 2
    && readyConnections.length > 0 && participants.every(participant => !participant.connection_id
      || readyConnections.some(connection => connection.id === participant.connection_id))
    && hasEvidence && !restrictedSharedSource && (!manuscripts.enabled || validManuscripts);
  const personaOptions = personas.length ? personas.map(item => item.id) : [...personaIds];

  function updateParticipant(id: number, patch: Partial<ParticipantDraft>) {
    setRosterEdited(true);
    setParticipants(items => items.map(item => item.id === id ? { ...item, ...patch } : item));
  }

  function applyTeam(team: Team) {
    const roster = teams[team].map(persona => newParticipant(nextId.current++, persona));
    setParticipants(roster);
    setRosterEdited(false);
    setPendingTeam(null);
    setError(null);
  }

  async function createRoom() {
    if (!canStart || creating.current) return;
    creating.current = true;
    setBusy(true);
    setError(null);
    const scope: RoundtableScope = {
      collection_filter: useCorpus ? filter : [],
      source_ids: !useCorpus ? [] : restrictSources ? sourceIds : undefined,
      web_research: useWeb,
      ...(validManuscripts && { manuscript_dossier_id: manuscripts.dossierId, manuscript_revision_ids: manuscripts.readings.map(reading => reading.id) }),
    };
    try {
      const room = await api<RoundtableRoom>('/roundtables', { method: 'POST', body: JSON.stringify({
        topic: topic.trim(), language, ...scope,
        participants: participants.map(({ persona_id, connection_id, pinned }, index) => ({
          name: names[index], persona_id, connection_id: connection_id || null, perspective: perspectives[index], pinned,
        })),
      }) });
      onCreated(room);
    } catch (problem) { setError(problem); }
    finally { creating.current = false; setBusy(false); }
  }

  return <form className="roundtable-setup" onSubmit={event => { event.preventDefault(); void createRoom(); }}>
    <p className="lead">{r('introduction')}</p>
    {!available && <p className="notice warning" role="status">{r('unavailable')}</p>}
    <RoundtableRequestError error={error} locale={locale} />
    <div className="panel roundtable-topic">
      <label>{r('topic')}<textarea value={topic} dir="auto" rows={3} required maxLength={10000} disabled={busy} onChange={event => setTopic(event.target.value)} /></label>
      <label>{c('answerLanguage')}<select value={language} disabled={busy} onChange={event => setLanguage(event.target.value)}>
        <option value="auto">{c('questionLanguage')}</option>
        {locales.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select></label>
    </div>
    <section className="panel roundtable-teams" aria-label={r('teams')}>
      <h3>{r('teams')}</h3><p className="helper">{r('teamsHint')}</p>
      <div className="button-row">{(Object.keys(teams) as Team[]).map(team => <button className="button secondary" type="button" key={team}
        disabled={busy || teams[team].some(persona => !personaOptions.includes(persona))}
        onClick={() => rosterEdited ? setPendingTeam(team) : applyTeam(team)}>{r(team)}</button>)}</div>
      {pendingTeam && <div className="notice" role="group" aria-label={r('replaceRoster')}>
        <p>{r('replaceRosterHint')}</p><div className="button-row">
          <button className="button secondary" type="button" disabled={busy} onClick={() => applyTeam(pendingTeam)}>{r('replaceRoster')}</button>
          <button className="text-button" type="button" onClick={() => setPendingTeam(null)}>{t('cancel')}</button>
        </div>
      </div>}
    </section>
    <section className="roundtable-preview" aria-label={t('participants')}>
      <h2>{t('participants')}</h2>
      <p className="helper">{r('quickStartHint')}</p>
      <div className="roundtable-roster">
        {participants.map((participant, index) => {
          const route = assigned[index];
          return <article className="panel roundtable-speaker" key={participant.id}>
            <h3 dir="auto">{names[index]}</h3>
            <p className="muted" dir="auto">{perspectives[index]}</p>
            {route && <p className="helper"><bdi>{route.title} · {route.model_id}</bdi></p>}
            {!participant.connection_id && <p className="helper">{r('automaticModelOnStart')}</p>}
            {participant.connection_id && (!route || !canUseConnection(route, settings)) &&
              <p className="inline-warning">{participant.pinned ? t('pinnedUnavailable') : t('unavailable')}</p>}
          </article>;
        })}
      </div>
    </section>
    {readyConnections.length === 0 && <div className="notice"><span>{c('noReadyConnections')}</span>
      <button type="button" className="text-button" onClick={openConnections}>{c('connections')}</button></div>}
    {!distinct && <p className="inline-warning" role="status">{r('duplicateNames')}</p>}
    <button className="button primary" disabled={!canStart}>{busy ? t('working') : r('start')}</button>
    <details className="panel roundtable-customize">
      <summary>{r('customizeParticipants')}</summary>
      <div className="roundtable-customize-fields">
        <button className="button secondary" type="button" disabled={busy || participants.length >= 4}
          onClick={() => {
            const participant = newParticipant(nextId.current++, 'comparative');
            setParticipants(items => [...items, participant]);
            setRosterEdited(true);
          }}>{t('addParticipant')}</button>
        {participants.map((participant, index) => {
          const description = roundtableProfile(locale, participant.persona_id)?.method
            ?? personas.find(item => item.id === participant.persona_id)?.description;
          const profileDescriptionId = `${descriptionId}-${participant.id}`;
          return <fieldset className="participant-card roundtable-participant-form" key={participant.id} disabled={busy}>
            <legend><bdi>{names[index]}</bdi></legend>
            <div className="participant-fields">
              <label>{r('participantName')}<input maxLength={80} value={participant.name} placeholder={names[index]} dir="auto"
                onChange={event => updateParticipant(participant.id, { name: event.target.value })} /></label>
              <div>
                <label>{t('persona')}<select value={participant.persona_id} aria-describedby={description ? profileDescriptionId : undefined}
                  onChange={event => updateParticipant(participant.id, { persona_id: event.target.value })}>
                  {personaOptions.map(id => <option key={id} value={id}>{roundtablePersonaName(id, personas, locale)}</option>)}
                </select></label>
                {description && <p id={profileDescriptionId} className="helper roundtable-profile-description" dir="auto">{description}</p>}
              </div>
              <label>{t('perspective')}<input maxLength={300} value={participant.perspective} placeholder={defaultPerspectives[index]} dir="auto"
                onChange={event => updateParticipant(participant.id, { perspective: event.target.value })} /></label>
              <label>{t('model')}<select value={participant.connection_id} disabled={participant.pinned}
                onChange={event => updateParticipant(participant.id, { connection_id: event.target.value })}>
                <option value="">{r('chooseAutomatically')}</option>
                {connections.map(connection => <option key={connection.id} value={connection.id} disabled={!canUseConnection(connection, settings)}>
                  {connection.title} · {connection.model_id} · {r(connection.local ? 'localRoute' : 'cloudRoute')}
                </option>)}
              </select></label>
              <label className="checkbox-label"><input type="checkbox" checked={participant.pinned} disabled={!participant.connection_id}
                onChange={event => updateParticipant(participant.id, { pinned: event.target.checked })} />{t('pin')}</label>
              {!!participant.connection_id && (!assigned[index] || !canUseConnection(assigned[index], settings)) &&
                <p className="inline-warning">{participant.pinned ? t('pinnedUnavailable') : t('unavailable')}</p>}
            </div>
            {participants.length > 2 && <button type="button" className="text-button" onClick={() => {
              setParticipants(items => items.filter(item => item.id !== participant.id));
              setRosterEdited(true);
            }}>{t('remove')}</button>}
          </fieldset>;
        })}
      </div>
    </details>
    <section className="panel grounding-controls roundtable-grounding" aria-label={r('fixedScope')}>
      <h2>{r('fixedScope')}</h2>
      {hasCorpus && !manuscripts.only && <>
        <fieldset disabled={busy}><legend>{c('collections')}</legend><div className="collection-options">
          {collections.map(id => <label key={id} className="checkbox-label"><input type="checkbox" checked={filter.includes(id)}
            onChange={event => setFilter(items => event.target.checked ? [...items, id] : items.filter(item => item !== id))} />{c(id)}</label>)}
        </div></fieldset>
        <label className="checkbox-label"><input type="checkbox" checked={restrictSources} disabled={busy}
          onChange={event => setRestrictSources(event.target.checked)} />{c('selectedSources')}</label>
        {restrictSources && <div className="source-options">{sources.map(source => <label key={source.id} className="checkbox-label">
          <input type="checkbox" checked={sourceIds.includes(source.id)}
            disabled={busy || (remote && source.use_limits.external_processing !== true && !sourceIds.includes(source.id))}
            onChange={event => setSourceIds(items => event.target.checked ? [...items, source.id] : items.filter(id => id !== source.id))} />
          <bdi>{source.title}</bdi>{!source.use_limits.external_processing && <small>{c('cloudDenied')}</small>}
        </label>)}</div>}
      </>}
      <ManuscriptChatSources locale={locale} dossiers={dossiers} selection={manuscripts} onChange={setManuscripts}
        remote={remote} disabled={busy || !ready} hasCorpus={hasCorpus} showCloudConsent={false} />
      <label className="checkbox-label roundtable-web"><input type="checkbox" checked={useWeb} disabled={!canWeb || busy}
        onChange={event => setWebResearch(event.target.checked)} />{r('webScope')}</label>
      {useWeb && <p className="helper">{c('webResearchHint')}</p>}
      <p className="helper">{r('sharedRights')}</p>
      {restrictedSharedSource && <p className="inline-warning" role="status">{r('removeRestrictedSources')}</p>}
      {(remote || (hasAutomatic && readyConnections.some(connection => !connection.local))) && <p className="helper">{r('cloudTopic')}</p>}
      {!hasEvidence && <p className="inline-warning">{r('chooseSources')}</p>}
      <button className="text-button" type="button" onClick={openSources}>{c('sources')}</button>
    </section>
  </form>;
}
