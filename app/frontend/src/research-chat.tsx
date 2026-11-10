import { ApiError } from './api';
import { chatTranslate } from './chat-i18n';
import { manuscriptTranslate } from './manuscript-i18n';
import type { ManuscriptKey } from './manuscript-i18n';
import type { ChatSettings, ChatTurn, Citation, Collection, Connection, Locale } from './types';

export const collections: Collection[] = ['torah', 'bible', 'quran'];
export function safeExternalUrl(value: string | null | undefined, httpsOnly = false): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    const allowedProtocol = url.protocol === 'https:' || (!httpsOnly && url.protocol === 'http:');
    return allowedProtocol && !url.username && !url.password ? url.href : undefined;
  } catch { return undefined; }
}
function record(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value); }
export function parseSourceJson(input: string): Record<string, unknown> {
  const source: unknown = JSON.parse(input);
  const nonempty = (value: unknown) => typeof value === 'string' && value.trim().length > 0;
  if (!record(source) || !nonempty(source.title) || !nonempty(source.source_type) || !record(source.edition)
    || !nonempty(source.edition.title) || !nonempty(source.edition.language) || !nonempty(source.edition.revision)
    || !Array.isArray(source.edition.collection_memberships) || !source.edition.collection_memberships.length
    || !source.edition.collection_memberships.every(item => collections.includes(item as Collection))
    || !Array.isArray(source.passages) || !source.passages.length
    || !source.passages.every(item => record(item) && nonempty(item.reference) && nonempty(item.text))
    || !record(source.use_limits) || typeof source.use_limits.external_processing !== 'boolean') throw new Error('invalid_source_json');
  return source;
}
export function answerSegments(answer: string, citations: Citation[]): { text: string; citation?: Citation }[] {
  const pieces = answer.split(/(\[S\d+\])/g);
  return pieces.map(text => ({ text, citation: /^\[S\d+\]$/.test(text) ? citations.find(item => item.id === text.slice(1, -1)) : undefined }));
}
export function canUseConnection(connection: Connection, settings: ChatSettings | null): boolean {
  return connection.enabled && connection.configured && (connection.local || settings?.local_only === false);
}
export function chatRequest(input: {
  message: string; connectionId: string; personaId: string; answerLanguage?: string; turns: ChatTurn[];
  conversationId?: string; sessionId?: string; filter: Collection[]; sourceIds?: string[]; webResearch?: boolean;
  manuscriptScope?: { dossierId: string; revisionIds: string[]; allowCloud: boolean };
}) {
  const history = input.turns.flatMap(turn => {
    const user = { role: 'user', content: turn.question };
    const usedManuscripts = (turn.grounding.manuscripts?.retrieved_count ?? 0) > 0
      || turn.citations.some(citation => citation.kind === 'manuscript');
    return usedManuscripts ? [user] : [user, { role: 'assistant', content: turn.answer }];
  }).slice(-12);
  if (history[0]?.role === 'assistant') history.shift();
  const scope = input.manuscriptScope;
  return {
    message: input.message.trim(), connection_id: input.connectionId, persona_id: input.personaId, language: input.answerLanguage ?? 'auto',
    history,
    conversation_id: input.conversationId, session_id: input.conversationId ? undefined : input.sessionId,
    collection_filter: input.filter, source_ids: input.sourceIds, web_research: input.webResearch ?? false,
    ...(scope && { manuscript_dossier_id: scope.dossierId, manuscript_revision_ids: scope.revisionIds, allow_manuscript_cloud: scope.allowCloud }),
  };
}
const manuscriptErrors: Partial<Record<string, ManuscriptKey>> = {
  invalid_manuscript_selection: 'manuscriptSelectionError',
  manuscript_dossier_not_found: 'manuscriptDossierError',
  manuscript_dossier_conflict: 'manuscriptScopeConflict',
  manuscript_cloud_consent_required: 'manuscriptConsentRequired',
  manuscript_processing_blocked: 'removeRestricted',
};

export function RequestError({ error, locale, manuscriptSearch = false }: { error: unknown; locale: Locale; manuscriptSearch?: boolean }) {
  if (!error) return null;
  const code = error instanceof ApiError ? error.code : undefined;
  const manuscriptKey = code === 'no_evidence' && manuscriptSearch ? 'manuscriptNoResults' : code && manuscriptErrors[code];
  const key = code === 'no_evidence' ? 'noEvidence' : code === 'session_expired' ? 'sessionExpired'
    : code === 'corpus_empty' ? 'noSources' : code === 'local_only' ? 'cloudBlocked'
      : code === 'provider_authentication' ? 'authenticationError' : code === 'invalid_citations' ? 'citationError' : 'requestFailed';
  return <div className="notice warning" role="alert"><span>{manuscriptKey ? manuscriptTranslate(locale, manuscriptKey) : chatTranslate(locale, key)}</span>{code && <code>{code}</code>}</div>;
}
