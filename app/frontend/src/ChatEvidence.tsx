import { useEffect, useRef } from 'react';
import { chatTranslate } from './chat-i18n';
import { manuscriptTranslate } from './manuscript-i18n';
import { ManuscriptEvidenceCard } from './ManuscriptEvidenceCard';
import { ParallelPassageReader } from './ParallelPassageReader';
import { answerSegments } from './research-chat';
import type { Citation, Locale } from './types';
import { WebEvidenceCard } from './WebEvidenceCard';

function citationClass(kind: Citation['kind']) {
  if (kind === 'web') return ' web-citation';
  if (kind === 'manuscript') return ' manuscript-citation';
  return '';
}

export function AnswerText({ answer, citations, onCitation }: {
  answer: string; citations: Citation[]; onCitation: (citation: Citation) => void;
}) {
  return <div className="assistant-message" dir="auto">{answerSegments(answer, citations).map((segment, index) => {
    const source = segment.citation;
    if (!source) return <span key={index}>{segment.text}</span>;
    return <button className={`citation-button${citationClass(source.kind)}`} key={index} onClick={() => onCitation(source)}>{segment.text}</button>;
  })}</div>;
}

export function CitationChips({ citations, locale, onCitation }: {
  citations: Citation[]; locale: Locale; onCitation: (citation: Citation) => void;
}) {
  if (!citations.length) return null;
  return <div className="citation-list">
    {citations.map(item => <button className={`citation-chip${citationClass(item.kind)}`} key={item.id} onClick={() => onCitation(item)}>
      [{item.id}] {item.kind === 'web' ? <>{chatTranslate(locale, 'webEvidence')} · <bdi>{item.title}</bdi></>
        : item.kind === 'manuscript' ? <>{manuscriptTranslate(locale, 'manuscriptEvidence')} · <bdi>{item.reference}</bdi></>
          : <bdi>{item.reference}</bdi>}
    </button>)}
  </div>;
}

export function CitationPanel({ citation, locale, onClose }: { citation: Citation; locale: Locale; onClose: () => void }) {
  const panel = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const active = document.activeElement;
    if (active instanceof HTMLElement && !panel.current?.contains(active)) trigger.current = active;
    panel.current?.focus();
  }, [citation]);
  return <aside ref={panel} tabIndex={-1} className="panel citation-panel" aria-label={chatTranslate(locale, 'citationDetails')}>
    <div className="panel-heading">
      <h2>{chatTranslate(locale, 'citationDetails')} [{citation.id}]</h2>
      <button className="text-button" onClick={() => { onClose(); trigger.current?.focus(); }}>{chatTranslate(locale, 'close')}</button>
    </div>
    {citation.kind === 'web' ? <WebEvidenceCard citation={citation} locale={locale} />
      : citation.kind === 'manuscript' ? <ManuscriptEvidenceCard key={citation.transcription_id} citation={citation} locale={locale} /> : <>
        <ParallelPassageReader key={citation.passage_id} snapshot={citation} locale={locale} cited />
        <p className="helper">{chatTranslate(locale, 'citationCaveat')}</p>
      </>}
  </aside>;
}
