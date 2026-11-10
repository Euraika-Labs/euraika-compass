import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { api, ApiError, originalImageUrl } from './api';
import { direction, locales, savedLocale, translate } from './i18n';
import type { MessageKey } from './i18n';
import type { ChatSettings, Connection, CorpusSource, CorpusStarter, Dossier, Health, ImageAsset, Job, Locale, ManuscriptProvenance, ModelRoute, Persona, Region, Transcription, View } from './types';
import { jobFinished, validRegion } from './workspace';
import { ChatPanel } from './ChatPanel';
import { ConnectionsPanel } from './ConnectionsPanel';
import { SourcesPanel } from './SourcesPanel';
import { ManuscriptLinks, ManuscriptProcessingLimits, ManuscriptsPanel } from './ManuscriptsPanel';
import { manuscriptTranslate } from './manuscript-i18n';
import { chatTranslate } from './chat-i18n';
import { RequestError } from './research-chat';

type List<T> = { items: T[] };
type Translator = (key: MessageKey) => string;

function CompassMark() {
  return <svg viewBox="0 0 40 40" width="34" height="34" aria-hidden="true"><circle cx="20" cy="20" r="16.5" fill="none" stroke="currentColor" strokeWidth="1.5" /><path d="m25.8 10.4-3.2 12.2-8.4 7 3.2-12.2z" fill="#f4a616" /><circle cx="20" cy="20" r="2" fill="currentColor" /></svg>;
}

function Notice({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'warning' | 'success' }) {
  return <div className={`notice ${tone}`} role={tone === 'warning' ? 'alert' : 'status'}>{children}</div>;
}

function errorMessage(error: unknown, t: Translator): string {
  if (!(error instanceof ApiError)) return t('errorGeneric');
  if (error.status === 409 || /revision|conflict/.test(error.code)) return t('errorConflict');
  if (error.code === 'network_error') return t('errorNetwork');
  if (/database|storage_not_ready/.test(error.code)) return t('errorDb');
  if (/route|model|adapter|configuration|local_only/.test(error.code)) return t('errorRoute');
  return t('errorGeneric');
}

function JobState({ job, t }: { job: Job; t: Translator }) {
  const key: MessageKey = job.status === 'queued' ? 'queued'
    : ['running', 'verifying'].includes(job.status) ? 'running'
      : ['complete', 'completed', 'succeeded'].includes(job.status) ? 'completed'
        : job.status === 'cancelled' ? 'cancelled' : job.status === 'interrupted' ? 'interrupted' : 'failed';
  return <span className={`pill ${key === 'failed' ? 'warning' : ''}`}>{t(key)}</span>;
}

function runsLocally(route: ModelRoute) {
  return route.local ?? ['local', 'kraken', 'llama.cpp'].includes(route.provider);
}

function routeAllowedForScan(route: ModelRoute, scan: ManuscriptProvenance | null) {
  if (!scan) return true;
  return runsLocally(route) ? scan.use_limits.local_ocr === true : scan.use_limits.external_processing === true;
}

export default function App() {
  const [locale, setLocale] = useState<Locale>(savedLocale);
  const t: Translator = key => translate(locale, key);
  const c = (key: Parameters<typeof chatTranslate>[1]) => chatTranslate(locale, key);
  const m = (key: Parameters<typeof manuscriptTranslate>[1]) => manuscriptTranslate(locale, key);
  const [view, setView] = useState<View>('research');
  const [manuscriptsOpened, setManuscriptsOpened] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [routes, setRoutes] = useState<ModelRoute[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [dossiers, setDossiers] = useState<Dossier[]>([]);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [formTitle, setFormTitle] = useState('');
  const [formQuestion, setFormQuestion] = useState('');
  const [formNotes, setFormNotes] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [images, setImages] = useState<ImageAsset[]>([]);
  const [image, setImage] = useState<ImageAsset | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [readingId, setReadingId] = useState('');
  const [readingText, setReadingText] = useState('');
  const [readingRoute, setReadingRoute] = useState('');
  const [sourceLanguage, setSourceLanguage] = useState('');
  const [useRegion, setUseRegion] = useState(false);
  const [region, setRegion] = useState<Region>({ x: 0, y: 0, width: 1, height: 1 });
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<MessageKey | null>(null);
  const [chatDraft, setChatDraft] = useState('');
  const [connections, setConnections] = useState<Connection[]>([]);
  const [chatSettings, setChatSettings] = useState<ChatSettings | null>(null);
  const [sources, setSources] = useState<CorpusSource[]>([]);
  const [starters, setStarters] = useState<CorpusStarter[]>([]);
  const [setupError, setSetupError] = useState<unknown>(null);
  const selectedDossier = useRef('');
  const selectedImage = useRef('');
  const readingEditor = useRef('');
  const selectionVersion = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const dbReady = health?.database.ready === true;
  const unsaved = !!dossier && (formTitle !== dossier.title || formQuestion !== (dossier.question ?? '') || formNotes !== (dossier.notes ?? ''));
  const currentReading = transcriptions.find(item => item.id === readingId);
  const manuscriptScan = image?.provenance?.kind === 'manuscript' ? image.provenance : null;
  const unsavedReading = !!image && readingText !== (currentReading?.text ?? '');
  const activeJob = job?.image_id === image?.id ? job : null;
  const jobRunning = !!activeJob && !jobFinished(activeJob.status);
  const readingRoutes = routes.filter(route => route.kind !== 'chat');
  const selectedRoute = readingRoutes.find(route => route.id === readingRoute);
  const canRunReadingRoute = !!selectedRoute?.available && routeAllowedForScan(selectedRoute, manuscriptScan);
  const regionValid = !useRegion || (!!image && validRegion(region, image.width, image.height));

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = direction(locale);
    try { localStorage.setItem('compass.locale', locale); } catch { /* Language still changes without storage. */ }
  }, [locale]);

  async function refreshConnection() {
    setError(null);
    const results = await Promise.allSettled([
      api<Health>('/health'), api<List<ModelRoute>>('/models'),
      api<List<Persona>>('/personas'), api<List<Dossier>>('/dossiers'),
    ]);
    if (results[0].status === 'fulfilled') setHealth(results[0].value);
    else { setHealth(null); setError(results[0].reason); }
    if (results[1].status === 'fulfilled') setRoutes(results[1].value.items);
    if (results[2].status === 'fulfilled') setPersonas(results[2].value.items);
    if (results[3].status === 'fulfilled') setDossiers(results[3].value.items);
    await refreshSetup();
  }

  async function refreshSetup() {
    setSetupError(null);
    const results = await Promise.allSettled([
      api<List<Connection>>('/connections'), api<ChatSettings>('/chat-settings'),
      api<List<CorpusSource>>('/corpus'), api<List<CorpusStarter>>('/corpus/starters'),
    ]);
    if (results[0].status === 'fulfilled') setConnections(results[0].value.items);
    if (results[1].status === 'fulfilled') setChatSettings(results[1].value);
    if (results[2].status === 'fulfilled') setSources(results[2].value.items);
    if (results[3].status === 'fulfilled') setStarters(results[3].value.items);
    const failed = results.find(item => item.status === 'rejected');
    if (failed?.status === 'rejected') setSetupError(failed.reason);
  }

  useEffect(() => { void refreshConnection(); }, []);

  function updateReadingText(value: string) {
    readingEditor.current = value;
    setReadingText(value);
  }

  async function loadReadings(asset: ImageAsset, preserveDraft = false) {
    const result = await api<List<Transcription>>(`/images/${asset.id}/transcriptions`);
    if (selectedImage.current !== asset.id) return;
    setTranscriptions(result.items);
    if (!preserveDraft || !readingEditor.current.trim()) {
      const latest = result.items.at(-1);
      setReadingId(latest?.id ?? '');
      updateReadingText(latest?.text ?? '');
    }
  }

  async function selectImage(asset: ImageAsset) {
    selectedImage.current = asset.id;
    setImage(asset);
    setImageFailed(false);
    setUseRegion(false);
    setRegion({ x: 0, y: 0, width: asset.width, height: asset.height });
    setTranscriptions([]);
    setReadingId('');
    updateReadingText('');
    if (asset.provenance?.kind === 'manuscript') {
      setReadingRoute('');
      setSourceLanguage(asset.provenance.language ?? '');
    }
    setNotice(null);
    try { await loadReadings(asset); } catch (problem) { if (selectedImage.current === asset.id) setError(problem); }
  }

  async function openDossier(id: string, initialImageId?: string) {
    const version = ++selectionVersion.current;
    selectedDossier.current = id;
    selectedImage.current = '';
    setError(null);
    setNotice(null);
    setImage(null);
    setImages([]);
    setTranscriptions([]);
    updateReadingText('');
    setBusy('open');
    try {
      const [record, imageList] = await Promise.all([api<Dossier>(`/dossiers/${id}`), api<List<ImageAsset>>(`/dossiers/${id}/images`)]);
      if (selectionVersion.current !== version) return;
      if (selectedDossier.current !== record.id) return;
      const firstImage = initialImageId ? imageList.items.find(item => item.id === initialImageId) : imageList.items[0];
      if (initialImageId && !firstImage) throw new ApiError('asset_unavailable', 'The attached image could not be opened.', 404);
      setDossier(record);
      setFormTitle(record.title);
      setFormQuestion(record.question ?? '');
      setFormNotes(record.notes ?? '');
      setImages(imageList.items);
      setView('research');
      if (firstImage) await selectImage(firstImage);
    } catch (problem) { if (selectionVersion.current === version) setError(problem); }
    finally { if (selectionVersion.current === version) setBusy(''); }
  }

  async function openManuscriptImage(asset: ImageAsset) {
    if (!dbReady || busy || unsaved || unsavedReading) return;
    if (dossier?.id !== asset.dossier_id) {
      await openDossier(asset.dossier_id, asset.id);
      return;
    }
    setImages(items => items.some(item => item.id === asset.id) ? items : [...items, asset]);
    setError(null);
    setView('research');
    await selectImage(asset);
  }

  async function createDossier(event: FormEvent) {
    event.preventDefault();
    if (!newTitle.trim() || !dbReady) return;
    setBusy('create'); setError(null);
    try {
      const record = await api<Dossier>('/dossiers', { method: 'POST', body: JSON.stringify({ title: newTitle.trim(), question: chatDraft }) });
      setDossiers(items => [record, ...items]);
      setNewTitle(''); setCreateOpen(false);
      await openDossier(record.id);
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }

  async function saveDossier() {
    if (!dossier || !formTitle.trim()) return;
    setBusy('save'); setError(null); setNotice(null);
    try {
      const record = await api<Dossier>(`/dossiers/${dossier.id}`, {
        method: 'PATCH', body: JSON.stringify({ title: formTitle.trim(), question: formQuestion, notes: formNotes, expected_revision: dossier.revision }),
      });
      if (selectedDossier.current !== record.id) return;
      setDossier(record);
      setDossiers(items => items.map(item => item.id === record.id ? record : item));
      setNotice('saved');
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }

  async function uploadImage(file: File | undefined) {
    if (!file || !dossier) return;
    setBusy('upload'); setError(null); setNotice(null);
    const data = new FormData(); data.set('file', file); data.set('dossier_id', dossier.id);
    try {
      const asset = await api<ImageAsset>('/images', { method: 'POST', body: data });
      if (selectedDossier.current !== dossier.id) return;
      setImages(items => [...items, asset]);
      await selectImage(asset);
    } catch (problem) { setError(problem); }
    finally { setBusy(''); if (fileInput.current) fileInput.current.value = ''; }
  }

  async function startReading() {
    if (!image || !canRunReadingRoute || !regionValid) return;
    setBusy('read'); setError(null); setNotice(null);
    try {
      setJob(await api<Job>('/transcription-jobs', { method: 'POST', body: JSON.stringify({
        image_id: image.id, route_id: readingRoute, language: sourceLanguage.trim() || undefined,
        region: useRegion ? region : undefined,
      }) }));
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }

  useEffect(() => {
    if (!job || jobFinished(job.status)) return;
    let stopped = false;
    let inFlight = false;
    const jobId = job.id;
    const timer = window.setInterval(async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const update = await api<Job>(`/jobs/${jobId}`);
        if (stopped) return;
        setJob(update);
        if (jobFinished(update.status)) {
          window.clearInterval(timer);
          if (selectedImage.current === update.image_id && image) await loadReadings(image, true);
        }
      } catch (problem) { if (!stopped) { setError(problem); window.clearInterval(timer); } }
      finally { inFlight = false; }
    }, 1100);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [job?.id, job?.status]);

  async function cancelReading() {
    if (!activeJob) return;
    setBusy('cancel'); setError(null);
    try { setJob(await api<Job>(`/jobs/${activeJob.id}/cancel`, { method: 'POST' })); }
    catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }

  async function saveReading() {
    if (!image || !readingText.trim()) return;
    const submittedText = readingText;
    setBusy('reading-save'); setError(null); setNotice(null);
    try {
      const reading = await api<Transcription>(currentReading ? `/transcriptions/${currentReading.id}/revisions` : `/images/${image.id}/transcriptions`, {
        method: 'POST', body: JSON.stringify({ text: readingText, language: sourceLanguage.trim() || undefined }),
      });
      if (selectedImage.current !== image.id) return;
      setTranscriptions(items => [...items, reading]);
      setReadingId(reading.id);
      if (readingEditor.current === submittedText) updateReadingText(reading.text);
      setNotice('saved');
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }

  async function toggleRoute(route: ModelRoute) {
    setBusy(route.id); setError(null);
    try {
      const updated = await api<ModelRoute>(`/models/${route.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: !route.enabled }) });
      setRoutes(items => items.map(item => item.id === route.id ? updated : item));
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }

  function selectReading(id: string) {
    const reading = transcriptions.find(item => item.id === id);
    setReadingId(id); updateReadingText(reading?.text ?? ''); setNotice(null);
  }

  return <div className="app-shell">
    <a className="skip-link" href="#workspace">{t('research')}</a>
    <header className="topbar">
      <div className="brand"><CompassMark /><div><strong>Euraika <span>Compass</span></strong><small>{t('personal')}</small></div></div>
      <nav className="mode-switch" aria-label={t('personal')}>
        <button className={view === 'research' ? 'active' : ''} aria-current={view === 'research' ? 'page' : undefined} onClick={() => setView('research')}>{t('research')}</button>
        <button className={view === 'chat' ? 'active' : ''} aria-current={view === 'chat' ? 'page' : undefined} onClick={() => setView('chat')}>{t('chat')}</button>
      </nav>
      <div className="topbar-tools"><span className="build-label">{t('personal')}</span><label className="locale-picker"><span className="sr-only">{t('language')}</span><select value={locale} onChange={event => setLocale(event.target.value as Locale)}>{locales.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label></div>
    </header>
    <div className="workspace-shell">
      <aside className="sidebar">
        <div className="sidebar-heading"><h2>{t('dossiers')}</h2><button className="icon-button" disabled={!dbReady} onClick={() => setCreateOpen(value => !value)} aria-label={t('newDossier')} title={t('newDossier')}>＋</button></div>
        <button className="button primary new-research" disabled={!dbReady} onClick={() => setCreateOpen(true)}>＋ {t('newDossier')}</button>
        {createOpen && <form className="create-form" onSubmit={event => void createDossier(event)}>
          <label>{t('dossierTitle')}<input autoFocus value={newTitle} onChange={event => setNewTitle(event.target.value)} placeholder={t('titlePlaceholder')} maxLength={200} /></label>
          <div className="button-row"><button className="button primary" disabled={!!busy || !newTitle.trim()}>{busy === 'create' ? t('working') : t('create')}</button><button className="button quiet" type="button" onClick={() => setCreateOpen(false)}>{t('cancel')}</button></div>
        </form>}
        <div className="dossier-list">{dossiers.length ? dossiers.map(item => <button key={item.id} className={`dossier-item ${dossier?.id === item.id ? 'selected' : ''}`} onClick={() => void openDossier(item.id)} disabled={!dbReady || !!busy}><span className="dossier-symbol" aria-hidden="true">▤</span><span><strong dir="auto">{item.title}</strong><small>{new Date(item.updated_at).toLocaleDateString(locale)}</small></span></button>) : <p className="muted empty-small">{t('noDossiers')}</p>}</div>
        <div className="sidebar-bottom"><button className={`sidebar-link ${view === 'sources' ? 'selected' : ''}`} aria-current={view === 'sources' ? 'page' : undefined} onClick={() => setView('sources')}><span aria-hidden="true">▤</span>{c('sources')}</button><button className={`sidebar-link ${view === 'manuscripts' ? 'selected' : ''}`} aria-current={view === 'manuscripts' ? 'page' : undefined} onClick={() => { setManuscriptsOpened(true); setView('manuscripts'); }}><span aria-hidden="true">▧</span>{m('manuscripts')}</button><button className={`sidebar-link ${view === 'models' ? 'selected' : ''}`} aria-current={view === 'models' ? 'page' : undefined} onClick={() => setView('models')}><span aria-hidden="true">⚙</span>{t('models')}</button><div className="connection-note"><span className={`status-dot ${health ? 'online' : ''}`} />{health ? t('online') : t('offline')}</div><div className="connection-note"><span className={`status-dot ${dbReady ? 'online' : ''}`} />{dbReady ? t('dbReady') : t('dbUnavailable')}</div><button className="text-button" onClick={() => void refreshConnection()}>{t('retry')}</button></div>
      </aside>
      <main id="workspace" className="main-workspace" tabIndex={-1}>
        {!!error && <Notice tone="warning"><span>{errorMessage(error, t)}</span>{error instanceof ApiError && <code>{error.code}</code>}</Notice>}
        {notice && <Notice tone="success">{t(notice)}</Notice>}
        {!dbReady && view !== 'models' && <Notice tone="warning">{t('errorDb')}</Notice>}

        {view !== 'research' && <RequestError error={setupError} locale={locale} />}
        <div hidden={view !== 'chat'}><ChatPanel locale={locale} connections={connections} settings={chatSettings} sources={sources} dossiers={dossiers} personas={personas} ready={dbReady} webResearchAvailable={health?.features?.web_research === true} roundtableAvailable={health?.features?.roundtable_generation === true} draft={chatDraft} setDraft={setChatDraft} openConnections={() => setView('models')} openSources={() => setView('sources')} openResearch={() => setView('research')} /></div>
        {manuscriptsOpened && <div hidden={view !== 'manuscripts'}><ManuscriptsPanel locale={locale} dossiers={dossiers} ready={dbReady}
          openBlocked={unsaved || unsavedReading} opening={!!busy} onCreateDossier={() => setCreateOpen(true)}
          onOpen={asset => void openManuscriptImage(asset)} /></div>}
        {view === 'chat' || view === 'manuscripts' ? null : view === 'sources' ? <SourcesPanel locale={locale} sources={sources} starters={starters} ready={dbReady} refresh={refreshSetup} /> : view === 'models' ? <section className="models-view">
          <ConnectionsPanel locale={locale} connections={connections} settings={chatSettings} ready={dbReady} refresh={refreshSetup} />
          <div className="section-heading"><div><p className="eyebrow">Euraika Compass</p><h1>{t('connectedModels')}</h1></div><button className="button secondary" onClick={() => void refreshConnection()}>{t('retry')}</button></div>
          <p className="lead">{t('modelIntro')}</p><Notice>{t('configurationHint')}</Notice><p className="helper">{t('connectionNotProbed')}</p>
          <div className="model-grid">{routes.map(route => <article className="model-card" key={route.id}><div className="model-card-heading"><span className="model-type">{route.kind.toUpperCase()}</span><span className={`pill ${route.available ? 'ready' : ''}`}>{route.available ? t('available') : !route.enabled ? t('disabled') : !route.configured ? t('notConfigured') : t('unavailable')}</span></div><h2>{route.title}</h2><code className="model-id" dir="ltr">{route.model_id}</code><p className="muted">{route.provider}</p><div className="model-card-footer"><span>{route.enabled ? t('enabled') : t('disabled')} · {route.configured ? t('configured') : t('notConfigured')}</span><button className="button secondary" disabled={!!busy || !health} onClick={() => void toggleRoute(route)}>{busy === route.id ? t('working') : route.enabled ? t('disable') : t('enable')}</button></div></article>)}</div>
        </section> : <section className="research-view">
          <div className="section-heading"><div><p className="eyebrow">{t('research')}</p><h1 dir="auto">{dossier?.title ?? t('selectDossier')}</h1></div>{dossier && <div className="save-actions"><span className={`save-indicator ${unsaved ? 'dirty' : ''}`}>{unsaved ? t('unsaved') : t('saved')} · {t('revision')} {dossier.revision}</span><button className="button primary" disabled={!dbReady || !!busy || !unsaved || !formTitle.trim()} onClick={() => void saveDossier()}>{busy === 'save' ? t('working') : t('save')}</button></div>}</div>
          {!dossier ? <div className="empty-workspace"><div className="empty-compass"><CompassMark /></div><h2>{t('selectDossier')}</h2><p>{t('createIntro')}</p><button className="button primary" disabled={!dbReady} onClick={() => setCreateOpen(true)}>＋ {t('newDossier')}</button></div> : <>
            <div className="dossier-details"><label className="title-field">{t('dossierTitle')}<input value={formTitle} onChange={event => setFormTitle(event.target.value)} maxLength={200} dir="auto" /></label><label className="question-field">{t('question')}<textarea value={formQuestion} onChange={event => setFormQuestion(event.target.value)} placeholder={t('questionPlaceholder')} rows={2} dir="auto" /></label><details className="notes-disclosure"><summary>{t('notes')}</summary><textarea aria-label={t('notes')} value={formNotes} onChange={event => setFormNotes(event.target.value)} placeholder={t('notesPlaceholder')} rows={5} dir="auto" /></details></div>
            <div className="research-grid"><section className="image-panel panel"><div className="panel-heading"><h2>{t('images')}</h2><label className={`button secondary file-label ${busy ? 'is-disabled' : ''}`}>{busy === 'upload' ? t('working') : t('addImage')}<input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" disabled={!dbReady || !!busy} onChange={event => void uploadImage(event.target.files?.[0])} /></label></div><p className="helper">{t('imageHint')}</p>
              {images.length > 0 && <div className="image-tabs" role="group" aria-label={t('images')}>{images.map(asset => <button className={image?.id === asset.id ? 'active' : ''} key={asset.id} disabled={!!busy} onClick={() => void selectImage(asset)}><bdi>{asset.filename}</bdi></button>)}</div>}
              {image ? <><div className="image-meta"><span className="pill">{manuscriptScan ? m('manuscriptScan') : t('original')}</span><span className="muted">{t('dimensions')}: <bdi>{image.width} × {image.height}</bdi></span></div><div className="image-viewport"><div className="scan-frame"><img src={originalImageUrl(image.id)} alt={image.filename} onError={() => setImageFailed(true)} />{useRegion && regionValid && <div className="region-overlay" style={{ left: `${100 * region.x / image.width}%`, top: `${100 * region.y / image.height}%`, width: `${100 * region.width / image.width}%`, height: `${100 * region.height / image.height}%` }} />}</div></div>{imageFailed && <Notice tone="warning">{t('imageFailed')}</Notice>}<p className="source-caption">{manuscriptScan ? <><bdi>{manuscriptScan.institution}</bdi> · <bdi>{manuscriptScan.shelfmark}</bdi> · <bdi>{manuscriptScan.folio_label}</bdi></> : t('unknownOrigin')} · <code dir="ltr">SHA-256 {image.sha256.slice(0, 16)}…</code></p>
                {manuscriptScan && <div className="manuscript-scan-record">
                  <strong dir="auto">{manuscriptScan.manuscript_title}</strong>
                  {manuscriptScan.attribution && <p className="helper" dir="auto">{manuscriptScan.attribution}</p>}
                  <ManuscriptLinks locale={locale} catalogUrl={manuscriptScan.catalog_url} manifestUrl={manuscriptScan.manifest_url}
                    rightsUrl={manuscriptScan.rights_url} folioUrl={manuscriptScan.source_url} />
                  <ManuscriptProcessingLimits limits={manuscriptScan.use_limits} locale={locale} />
                </div>}<details className="region-controls"><summary>{t('region')} · {useRegion ? `${region.width} × ${region.height}` : t('fullImage')}</summary><label className="checkbox-label"><input type="checkbox" checked={useRegion} onChange={event => setUseRegion(event.target.checked)} />{t('useRegion')}</label>{useRegion && <div className="coordinate-grid" dir="ltr">{(['x', 'y', 'width', 'height'] as const).map(key => <label key={key}>{key === 'x' || key === 'y' ? key.toUpperCase() : t(key)}<input type="number" min={key === 'x' || key === 'y' ? 0 : 1} step={1} value={region[key]} onChange={event => setRegion(value => ({ ...value, [key]: event.target.value === '' ? 0 : Number(event.target.value) }))} /></label>)}</div>}{!regionValid && <p className="inline-warning">{t('invalidRegion')}</p>}</details></> : <div className="image-empty"><span aria-hidden="true">▧</span><p>{t('noImages')}</p></div>}
            </section>
              <section className="reading-panel panel"><div className="panel-heading"><h2>{t('transcription')}</h2><span className="pill">{currentReading?.kind === 'automatic' ? t('automatic') : currentReading ? t('userCorrected') : t('manualReading')}</span></div><label>{t('readingRoute')}<select value={readingRoute} onChange={event => setReadingRoute(event.target.value)}><option value="">{t('chooseRoute')}</option>{readingRoutes.map(route => {
                  const permitted = routeAllowedForScan(route, manuscriptScan);
                  return <option key={route.id} value={route.id} disabled={!route.available || !permitted}>
                    {route.title}{manuscriptScan && ` · ${m(runsLocally(route) ? 'localRoute' : 'cloudRoute')}`}
                    {!permitted ? ` — ${m('routeRestricted')}` : !route.available ? ` — ${t('unavailable')}` : ''}
                  </option>;
                })}</select></label>{!readingRoutes.some(route => route.available && routeAllowedForScan(route, manuscriptScan)) && <p className="helper">{t('noAvailableRoutes')}</p>}<label>{t('languageScript')}<input value={sourceLanguage} onChange={event => setSourceLanguage(event.target.value)} placeholder={t('languageScriptPlaceholder')} /></label><div className="button-row"><button className="button primary" disabled={!dbReady || !image || !canRunReadingRoute || !!busy || jobRunning || !regionValid} onClick={() => void startReading()}>{busy === 'read' ? t('working') : t('readText')}</button>{jobRunning && <button className="button secondary" disabled={!!busy} onClick={() => void cancelReading()}>{t('cancelJob')}</button>}</div><p className="helper">{manuscriptScan ? m('readingRights') : t('routeDisclosure')}</p>
                {manuscriptScan && selectedRoute && !runsLocally(selectedRoute) && <p className="helper">{t('routeDisclosure')}</p>}{activeJob && <div className="job-state" role="status"><span>{t('jobStatus')}</span><JobState job={activeJob} t={t} /></div>}
                {transcriptions.length > 0 && <label>{t('revisions')}<select value={readingId} onChange={event => selectReading(event.target.value)}><option value="">{t('manualReading')}</option>{transcriptions.map((item, index) => <option value={item.id} key={item.id}>{index + 1} · {item.kind === 'automatic' ? t('automatic') : t('userCorrected')} · {new Date(item.created_at).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}</option>)}</select></label>}
                <label className="reading-editor-label"><span className="sr-only">{t('transcription')}</span><textarea className="reading-editor" value={readingText} onChange={event => { updateReadingText(event.target.value); setNotice(null); }} disabled={!image || !dbReady} placeholder={t('readingPlaceholder')} dir="auto" spellCheck={false} rows={11} /></label><div className="reading-footer"><span className="muted">{t('notReviewed')}</span><button className="button secondary" disabled={!image || !dbReady || !!busy || !readingText.trim() || readingText === currentReading?.text} onClick={() => void saveReading()}>{busy === 'reading-save' ? t('working') : currentReading ? t('saveCorrection') : t('saveReading')}</button></div>{currentReading && <p className="engine-note"><code dir="ltr">{currentReading.engine} · {currentReading.model_id}</code></p>}<p className="helper">{t('uncertaintyNote')}</p><div className="translation-placeholder"><h3>{t('translation')}</h3><p>{t('translationPending')}</p></div>
              </section></div>
          </>}
          <div className="source-scope"><strong>{t('sourceScope')}</strong><span>{sources.length ? `${sources.length} · ${c('editions')}` : c('noSources')}</span><button className="text-button" onClick={() => setView('sources')}>{c('sources')}</button></div>
        </section>}
      </main>
    </div>
  </div>;
}
