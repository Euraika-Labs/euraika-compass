import { useEffect, useState } from 'react';
import { api } from './api';
import { chatTranslate } from './chat-i18n';
import type { ChatKey } from './chat-i18n';
import { safeExternalUrl } from './research-chat';
import type { Locale, ParallelPassage, ParallelPassages, PassageAlignment, PassageSnapshot } from './types';

const alignmentLabels: Record<PassageAlignment, ChatKey> = {
  same_reference: 'sameReference',
  mapped_reference: 'mappedReference',
  compare_only: 'compareOnly',
};

export function passageKind(sourceType: string | undefined): ChatKey {
  if (sourceType === 'original_text') return 'originalText';
  if (sourceType === 'translation') return 'translatedText';
  return 'sourceText';
}

const languageAliases: Record<string, string> = {
  hebrew: 'he', hbo: 'he', heb: 'he', iw: 'he',
  arabic: 'ar', ara: 'ar', arb: 'ar',
  greek: 'grc', ell: 'el', gre: 'el',
  english: 'en', eng: 'en',
};

export function passageLanguage(language: string) {
  const value = language.trim().toLowerCase().replaceAll('_', '-');
  const normalized = languageAliases[value] ?? value;
  const lang = /^[a-z]{2,8}(?:-[a-z0-9]{1,8})*$/.test(normalized) ? normalized : 'und';
  const primary = lang.split('-')[0];
  if (['he', 'ar', 'fa', 'ur', 'arc', 'syc', 'yi'].includes(primary)) return { lang, dir: 'rtl' as const };
  if (['grc', 'el', 'en', 'nl', 'fr', 'de'].includes(primary)) return { lang, dir: 'ltr' as const };
  return { lang, dir: 'auto' as const };
}

function sameSnapshot(selected: PassageSnapshot, current: PassageSnapshot) {
  return selected.passage_id === current.passage_id && selected.reference === current.reference
    && selected.quote === current.quote && selected.revision === current.revision
    && (!selected.edition_id || selected.edition_id === current.edition_id)
    && (!selected.content_sha256 || selected.content_sha256 === current.content_sha256)
    && (!selected.quote_sha256 || selected.quote_sha256 === current.quote_sha256);
}

function preferredParallel(parallels: ParallelPassage[], anchorType: string | undefined) {
  const aligned = parallels.filter(item => item.alignment !== 'compare_only');
  const oppositeType = anchorType === 'original_text' ? 'translation' : 'original_text';
  return aligned.find(item => item.source_type === oppositeType) ?? aligned[0] ?? parallels[0];
}

function PassageCard({ passage, label, locale, parallel }: {
  passage: PassageSnapshot; label?: ChatKey; locale: Locale; parallel?: ParallelPassage;
}) {
  const t = (key: ChatKey) => chatTranslate(locale, key);
  const sourceUrl = safeExternalUrl(passage.url);
  const licenceUrl = safeExternalUrl(passage.licence_url ?? passage.use_limits?.licence_url);
  return <article className="passage-card">
    <div className="passage-badges">
      {label && <span className="pill">{t(label)}</span>}
      <span className="pill passage-kind">{t(passageKind(passage.source_type))}</span>
      {parallel && <span className={`pill ${parallel.alignment === 'compare_only' ? 'warning' : ''}`}>
        {t(alignmentLabels[parallel.alignment])}
      </span>}
    </div>
    <h3 dir="auto">{passage.source_title}</h3>
    <p className="passage-edition" dir="auto">{passage.edition_title}</p>
    <strong dir="auto">{passage.reference}</strong>
    <blockquote className="passage-quote" {...passageLanguage(passage.language)}>{passage.quote}</blockquote>
    <p className="helper">
      <bdi>{passage.language}</bdi> · <bdi>{passage.revision}</bdi>
      {passage.collection_memberships.length > 0 && ` · ${passage.collection_memberships.map(id => t(id)).join(' · ')}`}
    </p>
    {parallel?.alignment === 'compare_only' && <p className="inline-warning">{t('uncertainAlignment')}</p>}
    {parallel?.alignment_note && <p className="helper" dir="auto">{parallel.alignment_note}</p>}
    {sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer">{t('openSource')} ↗</a>}
    {(passage.use_limits?.rights_note || licenceUrl) && <div className="passage-rights">
      <strong>{t('editionRights')}</strong>
      {passage.use_limits?.rights_note && <p dir="auto">{passage.use_limits.rights_note}</p>}
      {licenceUrl && <a href={licenceUrl} target="_blank" rel="noreferrer">{t('licenceDetails')} ↗</a>}
    </div>}
    {passage.content_sha256 && <details className="passage-hash">
      <summary>SHA-256</summary><code dir="ltr">{passage.content_sha256}</code>
    </details>}
  </article>;
}

export function ParallelPassageReader({ snapshot, locale, cited = false }: {
  snapshot: PassageSnapshot; locale: Locale; cited?: boolean;
}) {
  const t = (key: ChatKey) => chatTranslate(locale, key);
  const passageId = snapshot.passage_id;
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<{ passageId: string; attempt: number; result: ParallelPassages | null } | null>(null);
  const [selectedId, setSelectedId] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const path = `/passages/${encodeURIComponent(passageId)}/parallel`;
    void api<ParallelPassages>(path, { signal: controller.signal }).then(result => {
      if (controller.signal.aborted) return;
      // Preserve the anchor even if a stale local backend does not have this endpoint yet.
      if (!result.anchor || !Array.isArray(result.parallels) || !Array.isArray(result.warnings)) {
        setLoad({ passageId, attempt, result: null });
        return;
      }
      setLoad({ passageId, attempt, result });
    }).catch(() => {
      if (!controller.signal.aborted) setLoad({ passageId, attempt, result: null });
    });
    return () => controller.abort();
  }, [passageId, attempt]);

  const current = load?.passageId === passageId && load.attempt === attempt ? load : null;
  const result = current?.result;
  const mismatch = !!result && !sameSnapshot(snapshot, result.anchor);
  const matchingAnchor = result && !mismatch ? result.anchor : undefined;
  const anchorType = snapshot.source_type ?? matchingAnchor?.source_type;
  const displayedAnchor = {
    ...snapshot,
    source_type: anchorType,
    use_limits: snapshot.use_limits ?? matchingAnchor?.use_limits,
    licence_url: snapshot.licence_url ?? matchingAnchor?.licence_url,
  };
  const parallels = result && !mismatch ? result.parallels : [];
  const parallel = parallels.find(item => item.passage_id === selectedId) ?? preferredParallel(parallels, anchorType);
  const onlyUncertain = parallels.length > 0 && parallels.every(item => item.alignment === 'compare_only');

  return <section className="parallel-reader" aria-label={t('parallelReader')}>
    {parallel && <label className="parallel-picker">
      {t('parallelEdition')}
      <select value={parallel.passage_id} onChange={event => setSelectedId(event.target.value)}>
        {parallels.map(item => <option key={item.passage_id} value={item.passage_id}>
          {item.edition_title} · {item.reference} · {t(alignmentLabels[item.alignment])}
        </option>)}
      </select>
    </label>}
    <div className={`parallel-grid${parallel ? ' has-parallel' : ''}`}>
      <PassageCard passage={displayedAnchor} label={cited ? 'citedSnapshot' : 'selectedPassage'} locale={locale} />
      {parallel && <PassageCard passage={parallel} locale={locale} parallel={parallel} />}
    </div>
    {!current && <p className="helper" role="status">{t('parallelLoading')}</p>}
    {current && !result && <div className="notice warning parallel-notice" role="alert">
      <span>{t('parallelError')}</span>
      <button className="text-button" onClick={() => setAttempt(value => value + 1)}>{t('retryPassages')}</button>
    </div>}
    {mismatch && <p className="notice warning parallel-notice" role="status">{t('snapshotMismatch')}</p>}
    {result && !mismatch && !parallel && <p className="notice parallel-notice" role="status">{t('noParallel')}</p>}
    {onlyUncertain && <p className="helper" role="status">{t('onlyUncertain')}</p>}
    {result && !mismatch && result.warnings.length > 0 && <details className="turn-warnings">
      <summary>{t('warnings')} ({result.warnings.length})</summary>
      <ul>{result.warnings.map((warning, index) => <li key={index} dir="auto">{warning}</li>)}</ul>
    </details>}
  </section>;
}
