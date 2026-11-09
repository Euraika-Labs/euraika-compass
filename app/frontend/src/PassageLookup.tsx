import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api } from './api';
import { chatTranslate } from './chat-i18n';
import type { ChatKey } from './chat-i18n';
import { translate } from './i18n';
import { ParallelPassageReader, passageKind, passageLanguage } from './ParallelPassageReader';
import { collections } from './research-chat';
import type { Collection, CorpusSource, Locale, PassageSnapshot } from './types';

export function PassageLookup({ locale, sources, ready }: { locale: Locale; sources: CorpusSource[]; ready: boolean }) {
  const t = (key: ChatKey) => chatTranslate(locale, key);
  const [query, setQuery] = useState('');
  const [collection, setCollection] = useState<Collection | ''>('');
  const [sourceId, setSourceId] = useState('');
  const [results, setResults] = useState<PassageSnapshot[] | null>(null);
  const [selected, setSelected] = useState<PassageSnapshot | null>(null);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const request = useRef<AbortController | null>(null);

  useEffect(() => () => request.current?.abort(), []);

  async function search(event: FormEvent) {
    event.preventDefault();
    const term = query.trim();
    if (!ready || !term || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const params = new URLSearchParams({ q: term });
    if (collection) params.set('collection', collection);
    if (sourceId) params.set('source_id', sourceId);
    setPending(true);
    setFailed(false);
    setResults(null);
    setSelected(null);
    try {
      const response = await api<{ items: PassageSnapshot[] }>(`/corpus/search?${params}`, { signal: controller.signal });
      if (!controller.signal.aborted) setResults(response.items);
    } catch {
      if (!controller.signal.aborted) setFailed(true);
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setPending(false);
    }
  }

  return <section className="panel passage-lookup">
    <h2>{t('passageLookup')}</h2>
    <form onSubmit={event => void search(event)}>
      <div className="passage-search-fields">
        <label>{t('passageQuery')}<input dir="auto" type="search" maxLength={2000} value={query} onChange={event => setQuery(event.target.value)} placeholder={t('passageExample')} /></label>
        <label>{t('collections')}<select value={collection} onChange={event => setCollection(event.target.value as Collection | '')}>
          <option value="">{t('allCollections')}</option>
          {collections.map(item => <option key={item} value={item}>{t(item)}</option>)}
        </select></label>
        <label>{t('sources')}<select value={sourceId} onChange={event => setSourceId(event.target.value)}>
          <option value="">{t('allSources')}</option>
          {sources.map(source => <option key={source.id} value={source.id}>{source.title}</option>)}
        </select></label>
        <button className="button primary" disabled={!ready || pending || !query.trim() || !sources.length}>
          {pending ? translate(locale, 'working') : t('searchPassages')}
        </button>
      </div>
      <p className="helper">{t('lookupHint')}</p>
    </form>
    {pending && <p className="helper" role="status">{translate(locale, 'working')}</p>}
    {failed && <p className="notice warning parallel-notice" role="alert">{t('lookupError')}</p>}
    {results?.length === 0 && <p className="notice parallel-notice" role="status">{t('noPassages')}</p>}
    {!!results?.length && <div className="passage-results" role="group" aria-label={t('passageResults')}>
      {results.map(passage => <button type="button" className="passage-result" key={passage.passage_id}
        aria-pressed={selected?.passage_id === passage.passage_id} onClick={() => setSelected(passage)}>
        <strong><bdi>{passage.reference}</bdi> · <bdi>{passage.edition_title}</bdi></strong>
        <span className="helper">{t(passageKind(passage.source_type))} · <bdi>{passage.language}</bdi></span>
        <span className="passage-preview" {...passageLanguage(passage.language)}>{passage.quote}</span>
      </button>)}
    </div>}
    {selected && <ParallelPassageReader key={selected.passage_id} snapshot={selected} locale={locale} />}
  </section>;
}
