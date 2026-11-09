import { useEffect, useRef, useState } from 'react';
import { api } from './api';
import { chatTranslate } from './chat-i18n';
import { translate } from './i18n';
import { manuscriptTranslate } from './manuscript-i18n';
import type { ManuscriptKey } from './manuscript-i18n';
import { passageLanguage } from './ParallelPassageReader';
import { safeExternalUrl } from './research-chat';
import type { Dossier, ImageAsset, Locale, Manuscript, ManuscriptFolio, ManuscriptFolios, ManuscriptUseLimits } from './types';

type Load<T> = { state: 'loading' } | { state: 'error' } | { state: 'ready'; value: T };

function languageName(language: string, locale: Locale) {
  const { lang } = passageLanguage(language);
  return lang === 'und' ? language : new Intl.DisplayNames(locale, { type: 'language', fallback: 'none' }).of(lang) ?? language;
}

function folioPath(manuscriptId: string, folioId: string) {
  return `/manuscripts/${encodeURIComponent(manuscriptId)}/folios/${encodeURIComponent(folioId)}`;
}

export function ManuscriptLinks({ catalogUrl, manifestUrl, rightsUrl, folioUrl, locale }: {
  catalogUrl: string | null; manifestUrl?: string | null; rightsUrl?: string | null; folioUrl?: string | null; locale: Locale;
}) {
  const entries: [ManuscriptKey, string | null | undefined][] = [
    ['openCatalog', catalogUrl], ['openManifest', manifestUrl], ['openRights', rightsUrl], ['openFolio', folioUrl],
  ];
  return <div className="manuscript-links">{entries.map(([label, url]) => {
    const href = safeExternalUrl(url);
    return href && <a href={href} key={label} target="_blank" rel="noreferrer">{manuscriptTranslate(locale, label)} ↗</a>;
  })}</div>;
}

export function ManuscriptProcessingLimits({ limits, locale }: { limits: ManuscriptUseLimits; locale: Locale }) {
  const t = (key: ManuscriptKey) => manuscriptTranslate(locale, key);
  return <div className="passage-badges">
    <span className={`pill${limits.local_ocr ? '' : ' warning'}`}>{t(limits.local_ocr ? 'localOcrAllowed' : 'localOcrRestricted')}</span>
    <span className={`pill${limits.external_processing ? '' : ' warning'}`}>{t(limits.external_processing ? 'externalAllowed' : 'externalRestricted')}</span>
  </div>;
}

function FolioPreview({ previewUrl, title, locale }: { previewUrl: string; title: string; locale: Locale }) {
  const t = (key: ManuscriptKey) => manuscriptTranslate(locale, key);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [attempt, setAttempt] = useState(0);
  return <>
    {state === 'loading' && <p role="status" className="helper">{t('previewLoading')}</p>}
    {state === 'error' && <div role="alert" className="notice warning manuscript-notice">
      <span>{t('previewError')}</span>
      <button className="text-button" onClick={() => { setState('loading'); setAttempt(value => value + 1); }}>{t('retry')}</button>
    </div>}
    {state !== 'error' && <div className="manuscript-viewport" aria-busy={state === 'loading'}>
      <img src={attempt ? `${previewUrl}?retry=${attempt}` : previewUrl} alt={title}
        onLoad={() => setState('ready')} onError={() => setState('error')} />
    </div>}
  </>;
}

export function ManuscriptsPanel({ locale, dossiers, ready, openBlocked, opening, onCreateDossier, onOpen }: {
  locale: Locale; dossiers: Dossier[]; ready: boolean; openBlocked: boolean; opening: boolean;
  onCreateDossier: () => void; onOpen: (asset: ImageAsset) => void;
}) {
  const t = (key: ManuscriptKey) => manuscriptTranslate(locale, key);
  const [query, setQuery] = useState('');
  const [language, setLanguage] = useState('');
  const [languages, setLanguages] = useState<string[]>([]);
  const [catalogue, setCatalogue] = useState<Load<Manuscript[]>>({ state: 'loading' });
  const [selected, setSelected] = useState<Manuscript | null>(null);
  const [folioList, setFolioList] = useState<Load<ManuscriptFolios> | null>(null);
  const [folioId, setFolioId] = useState('');
  const [destination, setDestination] = useState('');
  const [attachment, setAttachment] = useState<Load<ImageAsset> | null>(null);
  const catalogueRequest = useRef<AbortController | null>(null);
  const folioRequest = useRef<AbortController | null>(null);
  const attaching = attachment?.state === 'loading';
  const manuscript = folioList?.state === 'ready' ? folioList.value.manuscript : selected;
  const folio = folioList?.state === 'ready' ? folioList.value.items.find(item => item.id === folioId) : undefined;

  async function search(term: string, selectedLanguage: string) {
    catalogueRequest.current?.abort();
    folioRequest.current?.abort();
    const controller = new AbortController();
    catalogueRequest.current = controller;
    setCatalogue({ state: 'loading' });
    setSelected(null);
    setFolioList(null);
    setFolioId('');
    setAttachment(null);
    const params = new URLSearchParams();
    if (term.trim()) params.set('q', term.trim());
    if (selectedLanguage) params.set('language', selectedLanguage);
    try {
      const response = await api<{ items: Manuscript[] }>(`/manuscripts${params.size ? `?${params}` : ''}`, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setCatalogue({ state: 'ready', value: response.items });
      setLanguages(previous => [...new Set([...previous, ...response.items.map(item => item.language)])].sort());
    } catch {
      if (!controller.signal.aborted) setCatalogue({ state: 'error' });
    }
  }

  useEffect(() => {
    void search('', '');
    return () => { catalogueRequest.current?.abort(); folioRequest.current?.abort(); };
  }, []);

  async function chooseManuscript(value: Manuscript) {
    folioRequest.current?.abort();
    const controller = new AbortController();
    folioRequest.current = controller;
    setSelected(value);
    setFolioList({ state: 'loading' });
    setFolioId('');
    setAttachment(null);
    try {
      const response = await api<ManuscriptFolios>(`/manuscripts/${encodeURIComponent(value.id)}/folios`, { signal: controller.signal });
      if (!controller.signal.aborted) setFolioList({ state: 'ready', value: response });
    } catch {
      if (!controller.signal.aborted) setFolioList({ state: 'error' });
    }
  }

  async function attach() {
    if (!manuscript || !folio?.use_limits?.local_storage || !destination || !ready || attaching) return;
    setAttachment({ state: 'loading' });
    try {
      const asset = await api<ImageAsset>(`${folioPath(manuscript.id, folio.id)}/import`, {
        method: 'POST', body: JSON.stringify({ dossier_id: destination }),
      });
      const source = asset.provenance;
      if (asset.dossier_id !== destination || source?.kind !== 'manuscript' || source.manuscript_id !== manuscript.id || source.folio_id !== folio.id) {
        setAttachment({ state: 'error' });
        return;
      }
      setAttachment({ state: 'ready', value: asset });
    } catch {
      setAttachment({ state: 'error' });
    }
  }

  function previewUrl(item: ManuscriptFolio) {
    if (!manuscript || !item.use_limits?.preview) return undefined;
    const expected = `/api/v1${folioPath(manuscript.id, item.id)}/preview`;
    return item.preview_url === expected ? expected : undefined;
  }

  const preview = folio && previewUrl(folio);
  return <section className="manuscripts-view">
    <div className="section-heading"><div><p className="eyebrow">Euraika Compass</p><h1>{t('manuscripts')}</h1></div></div>
    <p className="lead">{t('intro')}</p>
    <form className="panel manuscript-search" onSubmit={event => { event.preventDefault(); if (!attaching) void search(query, language); }}>
      <label>{t('searchQuery')}<input type="search" value={query} onChange={event => setQuery(event.target.value)} dir="auto" maxLength={160} disabled={attaching} /></label>
      <label>{t('filterLanguage')}<select value={language} onChange={event => setLanguage(event.target.value)} disabled={attaching}>
        <option value="">{t('allLanguages')}</option>
        {languages.map(item => <option key={item} value={item}>{languageName(item, locale)}</option>)}
      </select></label>
      <button className="button primary" disabled={catalogue.state === 'loading' || attaching}>{t('search')}</button>
    </form>
    <div className="manuscript-layout">
      <section className="panel manuscript-list" aria-label={t('catalogue')}>
        <h2>{t('catalogue')}</h2>
        {catalogue.state === 'loading' && <p role="status" className="helper">{t('catalogLoading')}</p>}
        {catalogue.state === 'error' && <p role="alert" className="helper">{t('catalogError')}</p>}
        {catalogue.state === 'ready' && (catalogue.value.length ? catalogue.value.map(item => <button type="button" key={item.id}
          className="passage-result" aria-pressed={selected?.id === item.id} disabled={attaching} onClick={() => void chooseManuscript(item)}>
          <strong dir="auto">{item.title}</strong>
          <span className="helper"><bdi>{item.institution}</bdi> · <bdi>{item.shelfmark}</bdi></span>
          <span className="helper">{languageName(item.language, locale)}{item.date && <> · <bdi>{item.date}</bdi></>}</span>
        </button>) : <p role="status" className="helper">{t('noMatches')}</p>)}
      </section>
      <section className="panel manuscript-detail">
        {!manuscript ? <p className="muted">{t('selectManuscript')}</p> : <>
          <h2 dir="auto">{manuscript.title}</h2>
          <p className="muted"><bdi>{manuscript.institution}</bdi> · <bdi>{manuscript.shelfmark}</bdi>{manuscript.date && <> · <bdi>{manuscript.date}</bdi></>}</p>
          <p className="helper">{languageName(manuscript.language, locale)}{manuscript.collections.length > 0 && ` · ${manuscript.collections.map(id => chatTranslate(locale, id)).join(' · ')}`}</p>
          {manuscript.description && <p className="muted" dir="auto">{manuscript.description}</p>}
          <ManuscriptLinks locale={locale} catalogUrl={manuscript.catalog_url} manifestUrl={manuscript.manifest_url}
            rightsUrl={manuscript.rights_url} folioUrl={folio?.source_url} />
          {manuscript.attribution && <p className="helper manuscript-attribution" dir="auto">{manuscript.attribution}</p>}
          <ManuscriptProcessingLimits limits={folio?.use_limits ?? manuscript.use_limits} locale={locale} />
          {folioList?.state === 'loading' && <p role="status" className="helper">{t('foliosLoading')}</p>}
          {folioList?.state === 'error' && <div role="alert" className="notice warning manuscript-notice">
            <span>{t('foliosError')}</span><button className="text-button" onClick={() => void chooseManuscript(manuscript)}>{t('retry')}</button>
          </div>}
          {folioList?.state === 'ready' && (folioList.value.items.length ? <label>{t('folio')}
            <select value={folioId} disabled={attaching} onChange={event => { setFolioId(event.target.value); setAttachment(null); }}>
              <option value="">{t('selectFolio')}</option>
              {folioList.value.items.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </label> : <p className="helper" role="status">{t('noFolios')}</p>)}
          {folio && <>
            <div className="manuscript-folio-heading"><strong dir="auto">{folio.label}</strong>
              {folio.width > 0 && folio.height > 0 && <span className="helper"><bdi>{folio.width} × {folio.height} px</bdi></span>}
            </div>
            {preview ? <FolioPreview key={preview} previewUrl={preview} title={`${manuscript.title} — ${folio.label}`} locale={locale} />
              : <p className="notice manuscript-notice">{t(folio.use_limits?.preview ? 'previewUnavailable' : 'previewRestricted')}</p>}
            {folio.use_limits?.local_storage ? <div className="manuscript-attach">
              {dossiers.length ? <><label>{t('chooseDossier')}
                <select value={destination} disabled={attaching} onChange={event => { setDestination(event.target.value); setAttachment(null); }}>
                  <option value="">{t('selectDossier')}</option>
                  {dossiers.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
                </select>
              </label>
              <button className="button primary" disabled={!destination || !ready || attaching || attachment?.state === 'ready'} onClick={() => void attach()}>
                {attaching ? t('attaching') : t('attach')}
              </button></> : <button className="button secondary" disabled={!ready} onClick={onCreateDossier}>{translate(locale, 'newDossier')}</button>}
              <p className="helper">{t('attachHint')}</p>
              {attachment?.state === 'error' && <p role="alert" className="notice warning manuscript-notice">{t('attachError')}</p>}
              {attachment?.state === 'ready' && <>
                <p role="status" className="notice success manuscript-notice">{t('attached')}</p>
                <button className="button primary" disabled={!ready || openBlocked || opening} onClick={() => onOpen(attachment.value)}>
                  {opening ? translate(locale, 'working') : t('openReading')}
                </button>
                {openBlocked && <p className="helper">{t('openBlocked')}</p>}
              </>}
            </div> : <p className="notice manuscript-notice">{t('storageRestricted')}</p>}
          </>}
        </>}
      </section>
    </div>
  </section>;
}
