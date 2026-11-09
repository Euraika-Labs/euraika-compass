import { chatTranslate } from './chat-i18n';
import type { ChatKey } from './chat-i18n';
import { passageLanguage } from './ParallelPassageReader';
import { safeExternalUrl } from './research-chat';
import type { Locale, WebCitation, WebResearchGrounding } from './types';

const statusLabels: Record<WebResearchGrounding['status'], ChatKey> = {
  off: 'webOff',
  used: 'webUsed',
  not_used: 'webNotUsed',
  no_results: 'webNoResults',
  unavailable: 'webUnavailable',
  restricted: 'webRestricted',
};

export function WebResearchStatus({ research, locale }: { research: WebResearchGrounding; locale: Locale }) {
  const t = (key: ChatKey) => chatTranslate(locale, key);
  const warning = research.status === 'unavailable' || research.status === 'restricted';
  return <div className="web-research-status">
    <span className={`pill${warning ? ' warning' : ''}`}>{t(statusLabels[research.status])}
      {research.status === 'used' && typeof research.source_count === 'number' && ` · ${t('sources')}: ${research.source_count.toLocaleString(locale)}`}
    </span>
    {research.partial && <p className="helper">{t('webPartial')}</p>}
    {!!research.queries?.length && <details className="turn-warnings web-queries">
      <summary>{t('webQueries')}</summary>
      <ul>{research.queries.map((query, index) => <li key={index} dir="auto">{query}</li>)}</ul>
    </details>}
  </div>;
}

function webEvidenceType(citation: WebCitation, t: (key: ChatKey) => string) {
  switch (citation.evidence_type) {
    case 'publisher_abstract': return t('webAbstract');
    case 'abstract': return t('webIndexedAbstract');
    case 'article_extract':
    case 'page_excerpt': return t('webArticleExtract');
    case 'web_snippet': return t('webSnippet');
    default: return citation.source_type;
  }
}

export function WebEvidenceCard({ citation, locale }: { citation: WebCitation; locale: Locale }) {
  const t = (key: ChatKey) => chatTranslate(locale, key);
  const sourceUrl = safeExternalUrl(citation.source_url, true);
  const recordUrl = safeExternalUrl(citation.provenance?.record_url, true);
  const licenseUrl = safeExternalUrl(citation.license_url, true);
  const title = citation.title || citation.source_title || citation.edition_title || t('webEvidence');
  const publication = citation.publication || citation.edition_title;
  const retrieved = new Date(citation.retrieved_at);
  const retrievedLabel = Number.isNaN(retrieved.getTime()) ? citation.retrieved_at
    : new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(retrieved);

  return <article className="passage-card web-evidence" aria-label={t('webEvidence')}>
    <div className="passage-badges">
      <span className="pill passage-kind">{t('webEvidence')}</span>
      <span className="pill">{webEvidenceType(citation, t)}</span>
    </div>
    <h3 dir="auto">{title}</h3>
    <dl className="web-source-metadata">
      {publication && publication !== title && <><dt>{t('webPublication')}</dt><dd dir="auto">{publication}</dd></>}
      {!!citation.authors?.length && <><dt>{t('webAuthors')}</dt><dd dir="auto">{citation.authors.join(', ')}</dd></>}
      {citation.issued_date && <><dt>{t('webIssued')}</dt><dd><time dateTime={citation.issued_date}>{citation.issued_date}</time></dd></>}
      {retrievedLabel && <><dt>{t('webRetrieved')}</dt><dd><time dateTime={citation.retrieved_at}>{retrievedLabel}</time></dd></>}
      {citation.provider && <><dt>{t('webProvider')}</dt><dd dir="auto">{citation.provider}</dd></>}
      {(citation.license || licenseUrl) && <><dt>{t('webLicense')}</dt><dd>
        {licenseUrl ? <a href={licenseUrl} target="_blank" rel="noreferrer">{citation.license || t('licenceDetails')} ↗</a> : citation.license}
      </dd></>}
    </dl>
    <h4>{t('webExcerpt')}</h4>
    <blockquote className="passage-quote" {...(citation.language ? passageLanguage(citation.language) : { dir: 'auto' })}>{citation.quote}</blockquote>
    {sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer">{t('openSource')} ↗ <bdi>{new URL(sourceUrl).hostname}</bdi></a>}
    {recordUrl && recordUrl !== sourceUrl && <a href={recordUrl} target="_blank" rel="noreferrer">{t('webIndexRecord')} ↗ <bdi>{new URL(recordUrl).hostname}</bdi></a>}
    {citation.content_sha256 && <details className="passage-hash">
      <summary>SHA-256</summary><code dir="ltr">{citation.content_sha256}</code>
    </details>}
    <p className="helper">{t('webEvidenceCaveat')}</p>
  </article>;
}
