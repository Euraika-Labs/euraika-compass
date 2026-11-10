import { describe, expect, it } from 'vitest';
import { chatCatalog, chatTranslate } from './chat-i18n';
import { answerSegments, canUseConnection, chatRequest, parseSourceJson, safeExternalUrl } from './research-chat';
import type { ChatTurn, Citation, Connection, Locale } from './types';

const connection: Connection = { id: 'mistral-account', title: 'My account', provider: 'mistral', model_id: 'actual-account-model', base_url: null, enabled: true, configured: true, local: false, api_key_set: true };
const citation: Citation = { id: 'S1', passage_id: 'passage', source_id: 'source', source_title: 'Test source', edition_title: 'Test edition', reference: 'Fixture 1', quote: 'Neutral test passage', url: 'https://example.org/source', collection_memberships: ['torah'], language: 'en', revision: 'fixture', content_sha256: 'a'.repeat(64) };
const turn: ChatTurn = { id: 'turn', question: 'Earlier question', answer: 'Earlier answer [S1]', citations: [citation], warnings: [], connection_id: connection.id, model_id: connection.model_id, grounding: { mode: 'retrieval', retrieved_count: 1, collections: ['torah'] } };

describe('research chat boundaries', () => {
  it('defaults answers to the question language and permits an independent explicit choice', () => {
    const input = { message: 'Een Nederlandse vraag', connectionId: connection.id, personaId: 'supportive', turns: [], filter: ['torah'] as const };
    expect(chatRequest({ ...input, filter: [...input.filter] }).language).toBe('auto');
    expect(chatRequest({ ...input, filter: [...input.filter], answerLanguage: 'nl' }).language).toBe('nl');
    expect(chatRequest({ ...input, filter: [...input.filter], answerLanguage: 'fr' }).language).toBe('fr');
  });
  it('requires explicit cloud permission and does not treat an unknown policy as permission', () => {
    expect(canUseConnection(connection, null)).toBe(false);
    expect(canUseConnection(connection, { local_only: true })).toBe(false);
    expect(canUseConnection(connection, { local_only: false })).toBe(true);
    expect(canUseConnection({ ...connection, local: true }, { local_only: true })).toBe(true);
    expect(canUseConnection({ ...connection, enabled: false }, { local_only: false })).toBe(false);
    expect(canUseConnection({ ...connection, configured: false }, { local_only: false })).toBe(false);
  });
  it('sends the selected connection, plain conversation history and explicit filters without secrets', () => {
    const payload = chatRequest({ message: '  Current question  ', connectionId: connection.id, personaId: 'critical', answerLanguage: 'nl', turns: [turn], sessionId: 'temporary-id', filter: ['torah'], sourceIds: ['source'] });
    expect(JSON.parse(JSON.stringify(payload))).toEqual({ message: 'Current question', connection_id: 'mistral-account', persona_id: 'critical', language: 'nl', history: [{ role: 'user', content: 'Earlier question' }, { role: 'assistant', content: 'Earlier answer [S1]' }], session_id: 'temporary-id', collection_filter: ['torah'], source_ids: ['source'], web_research: false });
    expect(payload).not.toHaveProperty('api_key');
    expect(payload).not.toHaveProperty('citations');
  });
  it('does not auto-persist a temporary chat and retires the session ID after explicit saving', () => {
    const temporary = chatRequest({ message: 'Question', connectionId: connection.id, personaId: 'textual', turns: [], filter: ['quran'] });
    expect(temporary.conversation_id).toBeUndefined();
    const saved = chatRequest({ message: 'Question', connectionId: connection.id, personaId: 'textual', turns: [turn], filter: ['quran'], sessionId: 'old-session', conversationId: 'explicitly-saved' });
    expect(saved.conversation_id).toBe('explicitly-saved');
    expect(saved.session_id).toBeUndefined();
  });
  it('bounds model history to the last six full turns without losing the visible conversation', () => {
    const turns = Array.from({ length: 8 }, (_, index) => ({ ...turn, id: String(index), question: `Q${index}`, answer: `A${index}` }));
    const payload = chatRequest({ message: 'Next', connectionId: connection.id, personaId: 'textual', turns, filter: ['torah'] });
    expect(payload.history).toHaveLength(12);
    expect(payload.history[0]).toEqual({ role: 'user', content: 'Q2' });
    expect(payload.history.at(-1)).toEqual({ role: 'assistant', content: 'A7' });
    expect(turns).toHaveLength(8);
  });
  it('excludes an earlier answer exposed to manuscript readings even if it cited none', () => {
    const manuscriptTurn: ChatTurn = { ...turn, grounding: { ...turn.grounding,
      manuscripts: { status: 'not_used', retrieved_count: 1, source_count: 0, blocked_count: 0 } } };
    const payload = chatRequest({ message: 'Follow-up', connectionId: connection.id, personaId: 'textual', turns: [manuscriptTurn], filter: ['torah'] });
    expect(payload.history).toEqual([{ role: 'user', content: turn.question }]);
    expect(payload).not.toHaveProperty('manuscript_dossier_id');
    expect(payload).not.toHaveProperty('allow_manuscript_cloud');
  });
  it('only attaches citation controls to IDs returned by the backend', () => {
    const parts = answerSegments('Claim [S1] and unknown [S999]. <script> stays text.', [citation]);
    expect(parts.filter(part => part.citation).map(part => part.text)).toEqual(['[S1]']);
    expect(parts.map(part => part.text).join('')).toBe('Claim [S1] and unknown [S999]. <script> stays text.');
  });
  it('permits original HTTP(S) source links but rejects executable, relative and credential URLs', () => {
    expect(safeExternalUrl('https://example.org/text#verse')).toBe('https://example.org/text#verse');
    for (const value of ['javascript:alert(1)', 'data:text/html,hi', '/private', 'file:///C:/private', 'https://secret@example.org']) expect(safeExternalUrl(value)).toBeUndefined();
  });
  it('requires HTTPS for web evidence links', () => {
    expect(safeExternalUrl('https://example.org/article', true)).toBe('https://example.org/article');
    expect(safeExternalUrl('http://example.org/article', true)).toBeUndefined();
    expect(safeExternalUrl('https://secret@example.org/article', true)).toBeUndefined();
  });
});

describe('manual source imports', () => {
  const source = { title: 'Neutral test source', source_type: 'text', edition: { title: 'Fixture edition', language: 'ar', revision: 'test', collection_memberships: ['quran'] }, passages: [{ reference: 'Fixture 1', text: 'ابت · אבג · αβγ' }], use_limits: { external_processing: false } };
  it('preserves multilingual passages and explicit processing restrictions', () => {
    expect(parseSourceJson(JSON.stringify(source))).toEqual(source);
  });
  it('rejects missing permissions, empty passages and unsupported collection labels', () => {
    expect(() => parseSourceJson(JSON.stringify({ ...source, use_limits: {} }))).toThrow();
    expect(() => parseSourceJson(JSON.stringify({ ...source, passages: [] }))).toThrow();
    expect(() => parseSourceJson(JSON.stringify({ ...source, edition: { ...source.edition, collection_memberships: ['unspecified'] } }))).toThrow();
    expect(() => parseSourceJson('{broken')).toThrow();
  });
});

it('provides each new visible label in all five UI languages', () => {
  for (const locale of ['en', 'nl', 'ar', 'fr', 'de'] as Locale[]) {
    for (const key of Object.keys(chatCatalog) as (keyof typeof chatCatalog)[]) expect(chatTranslate(locale, key).trim().length).toBeGreaterThan(0);
  }
});
