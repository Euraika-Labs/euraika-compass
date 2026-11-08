import { useState } from 'react';
import type { FormEvent } from 'react';
import { api } from './api';
import { chatTranslate } from './chat-i18n';
import { translate } from './i18n';
import type { ChatSettings, Connection, Locale, Provider } from './types';
import { RequestError } from './research-chat';

const providers: Provider[] = ['mistral', 'local', 'openrouter', 'alibaba', 'anthropic', 'openai', 'minimax'];
const initialForm = { title: '', provider: 'mistral' as Provider, model_id: '', base_url: '', api_key: '' };

export function ConnectionsPanel({ locale, connections, settings, ready, refresh }: {
  locale: Locale; connections: Connection[]; settings: ChatSettings | null; ready: boolean; refresh: () => Promise<void>;
}) {
  const c = (key: Parameters<typeof chatTranslate>[1]) => chatTranslate(locale, key);
  const t = (key: Parameters<typeof translate>[1]) => translate(locale, key);
  const [form, setForm] = useState(initialForm);
  const [editing, setEditing] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<{ ok: boolean; model_id: string; message: string } | null>(null);
  const [accountModels, setAccountModels] = useState<{ connectionId: string; items: { id: string; title?: string }[] } | null>(null);
  const [pendingLocalOnly, setPendingLocalOnly] = useState<boolean | null>(null);
  function edit(connection: Connection) {
    setEditing(connection.id);
    setForm({ title: connection.title, provider: connection.provider, model_id: connection.model_id, base_url: connection.base_url ?? '', api_key: '' });
    setError(null);
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setError(null); setResult(null); setBusy('save');
    const payload = { title: form.title.trim(), provider: form.provider, model_id: form.model_id.trim(),
      base_url: form.base_url.trim() || (editing ? null : undefined), api_key: form.api_key || undefined, ...(!editing ? { enabled: true } : {}) };
    try {
      await api<Connection>(editing ? `/connections/${encodeURIComponent(editing)}` : '/connections', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(payload) });
      setForm(initialForm); setEditing(''); await refresh();
    } catch (problem) { setError(problem); setForm(value => ({ ...value, api_key: '' })); }
    finally { setBusy(''); }
  }
  async function act(id: string, action: 'test' | 'models' | 'toggle') {
    setBusy(`${id}-${action}`); setError(null); setResult(null);
    try {
      if (action === 'test') setResult(await api(`/connections/${encodeURIComponent(id)}/test`, { method: 'POST' }));
      else if (action === 'models') {
        const data = await api<{ items: { id: string; title?: string }[] }>(`/connections/${encodeURIComponent(id)}/models`);
        setAccountModels({ connectionId: id, items: data.items });
      } else {
        await api(`/connections/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ enabled: !connections.find(item => item.id === id)?.enabled }) });
        await refresh();
      }
    } catch (problem) { setError(problem); }
    finally { setBusy(''); }
  }
  async function changeLocalOnly(local_only: boolean) {
    setBusy('policy'); setError(null); setPendingLocalOnly(local_only);
    try { await api('/chat-settings', { method: 'PATCH', body: JSON.stringify({ local_only }) }); await refresh(); }
    catch (problem) { setError(problem); }
    finally { setBusy(''); setPendingLocalOnly(null); }
  }
  return <section className="connection-setup">
    <h2>{c('connections')}</h2><p className="lead">{c('connectionIntro')}</p>
    <RequestError error={error} locale={locale} />
    <div className="policy-box"><label className="checkbox-label"><input type="checkbox" checked={pendingLocalOnly ?? settings?.local_only ?? true} disabled={!ready || !!busy || !settings} onChange={event => void changeLocalOnly(event.target.checked)} />{c('localOnly')}</label><p className="helper">{c('cloudPermission')}</p></div>
    {!!busy && <p className="helper setup-working" role="status">{t('working')}</p>}
    {result && <div role="status" className={`notice ${result.ok ? 'success' : 'warning'}`}><span>{result.message}</span><code>{result.model_id}</code></div>}
    <div className="connection-layout"><div className="connection-cards">
      {!connections.length && <p className="muted">{c('noConnections')}</p>}
      {connections.map(connection => <article className="panel connection-card" key={connection.id}>
        <div className="panel-heading"><h3>{connection.title}</h3><span className="pill">{connection.enabled ? t('enabled') : t('disabled')}</span></div>
        <code dir="ltr">{connection.provider} · {connection.model_id}</code>
        <p className="helper">{connection.configured ? t('configured') : t('notConfigured')} · {connection.api_key_set ? c('keySet') : c('keyMissing')}</p>
        {settings?.local_only && !connection.local && <p className="inline-warning">{c('cloudBlocked')}</p>}
        <div className="button-row"><button className="button secondary" disabled={!!busy} onClick={() => edit(connection)}>{c('edit')}</button><button className="button secondary" disabled={!ready || !!busy} onClick={() => void act(connection.id, 'toggle')}>{connection.enabled ? t('disable') : t('enable')}</button><button className="button secondary" disabled={!ready || !!busy || !connection.configured || (settings?.local_only !== false && !connection.local)} onClick={() => void act(connection.id, 'test')}>{c('testConnection')}</button><button className="text-button" disabled={!ready || !!busy || !connection.configured || (settings?.local_only !== false && !connection.local)} onClick={() => void act(connection.id, 'models')}>{c('discover')}</button></div>
        {accountModels?.connectionId === connection.id && <div className="account-models"><label>{c('actualModels')}<select value="" onChange={event => { edit(connection); setForm(value => ({ ...value, model_id: event.target.value })); }}><option value="">{c('modelId')}</option>{accountModels.items.map(item => <option key={item.id} value={item.id}>{item.title ? `${item.title} · ${item.id}` : item.id}</option>)}</select></label>{!accountModels.items.length && <p className="helper">{c('modelListEmpty')}</p>}</div>}
      </article>)}
      <p className="helper">{c('testCost')}</p>
    </div><form className="panel connection-form" onSubmit={event => void save(event)} autoComplete="off">
      <h3>{editing ? c('edit') : c('addConnection')}</h3>
      <label>{c('title')}<input required maxLength={200} value={form.title} onChange={event => setForm(value => ({ ...value, title: event.target.value }))} /></label>
      <label>{c('provider')}<select value={form.provider} onChange={event => setForm(value => ({ ...value, provider: event.target.value as Provider, api_key: '' }))}>{providers.map(provider => <option key={provider} value={provider}>{provider === 'local' ? 'Local · OpenAI-compatible' : provider}</option>)}</select></label>
      <label>{c('modelId')}<input required value={form.model_id} onChange={event => setForm(value => ({ ...value, model_id: event.target.value }))} spellCheck={false} dir="ltr" /></label>
      <label>{c('baseUrl')}<input type="url" value={form.base_url} onChange={event => setForm(value => ({ ...value, base_url: event.target.value }))} spellCheck={false} dir="ltr" /></label>
      <label>{c('apiKey')}<input type="password" autoComplete="new-password" value={form.api_key} onChange={event => setForm(value => ({ ...value, api_key: event.target.value }))} spellCheck={false} dir="ltr" /></label><p className="helper">{c('keyHint')}</p>
      <div className="button-row"><button className="button primary" disabled={!ready || !!busy || !form.title.trim() || !form.model_id.trim()}>{busy === 'save' ? t('working') : c('save')}</button>{editing && <button type="button" className="button quiet" onClick={() => { setForm(initialForm); setEditing(''); }}>{c('cancel')}</button>}</div>
    </form></div>
  </section>;
}
