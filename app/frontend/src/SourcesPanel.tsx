import { useRef, useState } from 'react';
import { api } from './api';
import { chatTranslate } from './chat-i18n';
import { translate } from './i18n';
import { PassageLookup } from './PassageLookup';
import { passageKind } from './ParallelPassageReader';
import type { CorpusSource, CorpusStarter, Locale } from './types';
import { parseSourceJson, RequestError, safeExternalUrl } from './research-chat';

const schema = '{\n  "title": "",\n  "url": "",\n  "source_type": "text",\n  "edition": {"title": "", "language": "", "revision": "", "collection_memberships": ["torah"]},\n  "passages": [{"reference": "", "text": ""}],\n  "use_limits": {"external_processing": false, "rights_note": ""}\n}';

export function SourcesPanel({ locale, sources, starters, ready, refresh }: {
  locale: Locale; sources: CorpusSource[]; starters: CorpusStarter[]; ready: boolean; refresh: () => Promise<void>;
}) {
  const c = (key: Parameters<typeof chatTranslate>[1]) => chatTranslate(locale, key);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [json, setJson] = useState('');
  const [invalid, setInvalid] = useState(false);
  const [imported, setImported] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  async function importSource(starter?: string) {
    setError(null); setInvalid(false); setImported(false);
    let payload: Record<string, unknown> | undefined;
    if (!starter) {
      try { payload = parseSourceJson(json); } catch { setInvalid(true); return; }
    }
    setBusy(starter ?? 'manual');
    try {
      await api(starter ? `/corpus/starters/${encodeURIComponent(starter)}/import` : '/corpus/import', { method: 'POST', ...(payload ? { body: JSON.stringify(payload) } : {}) });
      setImported(true); await refresh();
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }
  async function openFile(file: File | undefined) {
    if (!file) return;
    setInvalid(false);
    if (file.size > 5 * 1024 * 1024) { setInvalid(true); return; }
    try { setJson(await file.text()); } catch (problem) { setError(problem); }
    finally { if (input.current) input.current.value = ''; }
  }
  return <section className="sources-view">
    <div className="section-heading"><div><p className="eyebrow">Euraika Compass</p><h1>{c('sources')}</h1></div><button className="button secondary" disabled={!!busy} onClick={() => void refresh()}>{translate(locale, 'retry')}</button></div>
    <p className="lead">{c('sourceIntro')}</p><RequestError error={error} locale={locale} />
    <PassageLookup locale={locale} sources={sources} ready={ready} />
    {imported && <div className="notice success" role="status">{c('imported')}</div>}
    {busy && <div className="notice" role="status">{c('importing')}</div>}
    <section className="panel starters-panel"><h2>{c('starters')}</h2><p className="helper">{c('importHint')}</p><div className="starter-grid">{starters.map(starter => <article className="starter-card" key={starter.id}><h3>{starter.title}</h3><p className="muted">{starter.language} · {starter.collections.map(id => c(id)).join(' · ')}</p>{starter.source_type && <span className="pill passage-kind">{c(passageKind(starter.source_type))}</span>}{starter.description && <p className="helper">{starter.description}</p>}<button className="button secondary" disabled={!ready || !!busy} onClick={() => void importSource(starter.id)}>{busy === starter.id ? c('importing') : c('importSource')}</button></article>)}</div></section>
    <h2 className="subsection-heading">{c('editions')}</h2>
    {!sources.length && <div className="notice">{c('noSources')}</div>}
    <div className="source-cards">{sources.map(source => <article className="panel source-card" key={source.id}><div className="panel-heading"><h3 dir="auto">{source.title}</h3><span className="pill">{c(passageKind(source.source_type))}</span></div>
      {source.editions.map(edition => <div className="edition-row" key={edition.id}><strong dir="auto">{edition.title}</strong><p>{edition.language} · {edition.revision} · {edition.passage_count.toLocaleString(locale)} {c('passages')}</p><p>{edition.collection_memberships.map(id => c(id)).join(' · ')}</p></div>)}
      <span className="pill">{source.use_limits.external_processing ? c('cloudAllowed') : c('cloudDenied')}</span>
      <details className="source-provenance"><summary>{c('provenance')}</summary><pre dir="auto">{typeof source.provenance === 'string' ? source.provenance : JSON.stringify(source.provenance, null, 2)}</pre>{source.use_limits.rights_note && <p>{source.use_limits.rights_note}</p>}</details>
      {safeExternalUrl(source.url) && <a href={safeExternalUrl(source.url)} target="_blank" rel="noreferrer">{c('openSource')} ↗</a>}
    </article>)}</div>
    <details className="panel manual-import"><summary>{c('importJson')}</summary><p className="helper">{c('sourceSchema')}</p><label className="button secondary file-label">{c('sourceFile')}<input ref={input} type="file" accept="application/json,.json" disabled={!!busy} onChange={event => void openFile(event.target.files?.[0])} /></label><label>{c('sourceJson')}<textarea dir="ltr" rows={13} value={json} placeholder={schema} spellCheck={false} disabled={!!busy} onChange={event => { setJson(event.target.value); setInvalid(false); }} /></label>{invalid && <p className="inline-warning" role="alert">{c('jsonInvalid')}</p>}<button className="button primary" disabled={!ready || !!busy || !json.trim()} onClick={() => void importSource()}>{c('importSource')}</button></details>
    <p className="helper">{c('neutralReminder')}</p>
  </section>;
}
