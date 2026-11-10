import { useState } from 'react';
import { originalImageUrl } from './api';
import { translate } from './i18n';
import { ManuscriptLinks } from './ManuscriptsPanel';
import { manuscriptTranslate } from './manuscript-i18n';
import type { ManuscriptKey } from './manuscript-i18n';
import { passageLanguage } from './ParallelPassageReader';
import type { Locale, ManuscriptCitation, ManuscriptGrounding, Region } from './types';

const statusLabels: Record<ManuscriptGrounding['status'], ManuscriptKey> = {
  used: 'manuscriptUsed', not_used: 'manuscriptNotUsed', no_results: 'manuscriptNoResults', restricted: 'manuscriptRestricted',
};

function regionFitsImage(region: Region, width: number, height: number) {
  return [region.x, region.y, region.width, region.height, width, height].every(Number.isFinite)
    && region.x >= 0 && region.y >= 0 && region.width > 0 && region.height > 0
    && region.x + region.width <= width && region.y + region.height <= height;
}

export function ManuscriptReadingStatus({ evidence, locale }: { evidence: ManuscriptGrounding; locale: Locale }) {
  const t = (key: ManuscriptKey) => manuscriptTranslate(locale, key);
  return <div className="manuscript-reading-status passage-badges">
    <span className={`pill${evidence.status === 'restricted' ? ' warning' : ''}`}>{t(statusLabels[evidence.status])}
      {evidence.status === 'used' && <> · {evidence.source_count.toLocaleString(locale)}</>}
    </span>
    {evidence.blocked_count > 0 && <span className="pill warning">{t('manuscriptBlockedCount')} · {evidence.blocked_count.toLocaleString(locale)}</span>}
  </div>;
}

export function ManuscriptEvidenceCard({ citation, locale }: { citation: ManuscriptCitation; locale: Locale }) {
  const t = (key: ManuscriptKey) => manuscriptTranslate(locale, key);
  const [attempt, setAttempt] = useState(0);
  const [imageState, setImageState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [regionAligned, setRegionAligned] = useState(false);
  const imageUrl = originalImageUrl(citation.image_id);
  const region = citation.region;
  const width = citation.image_width;
  const height = citation.image_height;
  const highlight = imageState === 'ready' && regionAligned && region
    && region.coordinate_system === 'original_image_pixels'
    && (region.kind === 'text_region' || region.kind === 'input_crop')
    && regionFitsImage(region, width, height) ? region : null;
  const created = new Date(citation.created_at);
  const createdLabel = Number.isNaN(created.getTime()) ? citation.created_at
    : new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(created);
  const readingLabel = translate(locale, citation.evidence_type === 'user_corrected' ? 'userCorrected' : 'automatic');
  const provenance = citation.provenance;
  const sourceIdentity = [provenance?.institution, provenance?.shelfmark, citation.folio_label].filter(Boolean);

  return <article className="passage-card manuscript-evidence" aria-label={t('manuscriptEvidence')}>
    <div className="passage-badges"><span className="pill passage-kind">{t('manuscriptEvidence')}</span><span className="pill">{readingLabel}</span></div>
    <h3 dir="auto">{citation.title}</h3>
    {!!sourceIdentity.length && <p className="helper">{sourceIdentity.map((part, index) => <span key={index}>{index > 0 && ' · '}<bdi>{part}</bdi></span>)}</p>}
    <div className="manuscript-evidence-grid">
      <div className="manuscript-evidence-scan">
        {imageState === 'loading' && <p role="status" className="helper">{t('previewLoading')}</p>}
        {imageState === 'error' && <div className="notice warning manuscript-notice" role="alert">
          <span>{translate(locale, 'imageFailed')}</span>
          <button className="text-button" onClick={() => { setImageState('loading'); setRegionAligned(false); setAttempt(value => value + 1); }}>{t('retry')}</button>
        </div>}
        {imageState !== 'error' && <div className="image-viewport" aria-busy={imageState === 'loading'}>
          <div className="scan-frame">
            <img className="manuscript-coordinate-image" src={attempt ? `${imageUrl}?retry=${attempt}` : imageUrl}
              alt={`${citation.title} — ${citation.folio_label}`} onLoad={event => {
                const image = event.currentTarget;
                setRegionAligned(image.naturalWidth === width && image.naturalHeight === height);
                setImageState('ready');
              }} onError={() => setImageState('error')} />
            {highlight && <div aria-hidden="true" className={`region-overlay${highlight.kind === 'input_crop' ? ' input-crop' : ''}`} style={{
              left: `${100 * highlight.x / width}%`, top: `${100 * highlight.y / height}%`,
              width: `${100 * highlight.width / width}%`, height: `${100 * highlight.height / height}%`,
            }} />}
          </div>
        </div>}
        {highlight && <p className="helper">{t(highlight.kind === 'input_crop' ? 'readingInputCrop' : 'readingTextRegion')}</p>}
        {imageState === 'ready' && !highlight && <p className="helper">{t('readingWholeFolio')}</p>}
      </div>
      <div className="manuscript-evidence-reading">
        <h4>{t('citedExcerpt')}</h4>
        <blockquote className="passage-quote" {...(citation.language ? passageLanguage(citation.language) : { dir: 'auto' })}>{citation.quote}</blockquote>
        <p className="helper">{t('readingSnapshotHint')}</p>
        <details className="passage-hash">
          <summary>{t('revisionRecord')}</summary>
          <p className="helper"><time dateTime={citation.created_at}>{createdLabel}</time></p>
          <code dir="ltr">{citation.transcription_id}</code>
          {(citation.engine || citation.model_id) && <code dir="ltr">{[citation.engine, citation.model_id].filter(Boolean).join(' · ')}</code>}
          <code dir="ltr">SHA-256 {citation.quote_sha256}</code>
        </details>
      </div>
    </div>
    {provenance?.attribution && <p className="helper manuscript-attribution" dir="auto">{provenance.attribution}</p>}
    <ManuscriptLinks locale={locale} catalogUrl={provenance?.catalog_url ?? null} manifestUrl={provenance?.manifest_url}
      rightsUrl={provenance?.rights_url} folioUrl={citation.source_url ?? provenance?.source_url} />
  </article>;
}
