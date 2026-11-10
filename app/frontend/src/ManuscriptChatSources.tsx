import { useEffect, useState } from 'react';
import { api } from './api';
import { translate } from './i18n';
import { manuscriptTranslate } from './manuscript-i18n';
import type { ManuscriptKey } from './manuscript-i18n';
import type { Dossier, Locale, ManuscriptReadingChoice } from './types';

export interface ManuscriptSelection {
  enabled: boolean;
  dossierId: string;
  readings: ManuscriptReadingChoice[];
  cloudConsent: boolean;
  only: boolean;
}

export const emptyManuscriptSelection: ManuscriptSelection = {
  enabled: false, dossierId: '', readings: [], cloudConsent: false, only: false,
};

type ReadingList = { items: ManuscriptReadingChoice[]; truncated?: boolean };
const maximumRevisions = 6;

export function ManuscriptChatSources({ locale, dossiers, selection, onChange, remote, disabled, hasCorpus }: {
  locale: Locale; dossiers: Dossier[]; selection: ManuscriptSelection; onChange: (selection: ManuscriptSelection) => void;
  remote: boolean; disabled: boolean; hasCorpus: boolean;
}) {
  const t = (key: ManuscriptKey) => manuscriptTranslate(locale, key);
  const dossierId = selection.enabled ? selection.dossierId : '';
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<{ dossierId: string; attempt: number; result: ReadingList | null } | null>(null);
  const current = load?.dossierId === dossierId && load.attempt === attempt ? load : null;
  const blocked = remote && selection.readings.some(reading => reading.external_processing !== true);
  const dateFormat = new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' });

  useEffect(() => {
    if (!dossierId) return;
    const controller = new AbortController();
    void api<ReadingList>(`/dossiers/${encodeURIComponent(dossierId)}/manuscript-readings`, { signal: controller.signal })
      .then(result => {
        if (!controller.signal.aborted) setLoad({ dossierId, attempt, result });
      }).catch(() => {
        if (!controller.signal.aborted) setLoad({ dossierId, attempt, result: null });
      });
    return () => controller.abort();
  }, [dossierId, attempt]);

  function changeReading(reading: ManuscriptReadingChoice, checked: boolean) {
    if (checked && selection.readings.length >= maximumRevisions) return;
    const readings = checked ? [...selection.readings, reading] : selection.readings.filter(item => item.id !== reading.id);
    onChange({ ...selection, readings, cloudConsent: false });
  }

  return <div className="chat-manuscript-sources">
    <label className="checkbox-label">
      <input type="checkbox" checked={selection.enabled} disabled={disabled || !dossiers.length}
        onChange={event => onChange({ ...emptyManuscriptSelection, enabled: event.target.checked })} />
      {t('includeReadings')}
    </label>
    {!dossiers.length && <p className="helper">{t('noReadingDossier')}</p>}
    {selection.enabled && <>
      <label>{t('sourceDossier')}
        <select value={dossierId} disabled={disabled} onChange={event => onChange({ ...selection, dossierId: event.target.value, readings: [], cloudConsent: false })}>
          <option value="">{t('selectDossier')}</option>
          {dossiers.map(dossier => <option key={dossier.id} value={dossier.id}>{dossier.title}</option>)}
        </select>
      </label>
      {dossierId && !current && <p role="status" className="helper">{t('readingsLoading')}</p>}
      {current && !current.result && <div className="notice warning manuscript-notice" role="alert">
        <span>{t('readingsError')}</span><button className="text-button" onClick={() => setAttempt(value => value + 1)}>{t('retry')}</button>
      </div>}
      {current?.result?.items.length === 0 && <p role="status" className="helper">{t('readingsEmpty')}</p>}
      {!!current?.result?.items.length && <fieldset disabled={disabled}>
        <legend>{t('chooseRevisions')}</legend>
        <p className="helper">{t('chooseRevisionsHint')} <bdi>{selection.readings.length}/{maximumRevisions}</bdi></p>
        <div className="chat-reading-options">
          {current.result.items.map(reading => {
            const checked = selection.readings.some(item => item.id === reading.id);
            const allowed = !remote || reading.external_processing === true;
            return <label className="checkbox-label chat-reading-option" key={reading.id}>
              <input type="checkbox" checked={checked} disabled={!checked && (!allowed || selection.readings.length >= maximumRevisions)}
                onChange={event => changeReading(reading, event.target.checked)} />
              <span>
                <strong dir="auto">{reading.title} · {reading.folio_label}</strong>
                <small>{translate(locale, reading.kind === 'user_corrected' ? 'userCorrected' : 'automatic')} · <bdi>{dateFormat.format(new Date(reading.created_at))}</bdi> · <bdi>{reading.id.slice(0, 8)}</bdi></small>
                {!reading.external_processing && <small className="inline-warning">{t('externalRestricted')}</small>}
              </span>
            </label>;
          })}
        </div>
        {current.result.truncated && <p className="helper">{t('readingsTruncated')}</p>}
      </fieldset>}
      {hasCorpus && <label className="checkbox-label">
        <input type="checkbox" checked={selection.only} disabled={disabled} onChange={event => onChange({ ...selection, only: event.target.checked })} />
        {t('manuscriptOnly')}
      </label>}
      {remote && selection.readings.length > 0 && <>
        {blocked ? <p role="status" className="inline-warning">{t('removeRestricted')}</p> : <label className="checkbox-label">
          <input type="checkbox" checked={selection.cloudConsent} disabled={disabled}
            onChange={event => onChange({ ...selection, cloudConsent: event.target.checked })} />
          {t('manuscriptCloudConsent')}
        </label>}
        <p className="helper">{t('manuscriptCloudHint')}</p>
      </>}
    </>}
  </div>;
}
