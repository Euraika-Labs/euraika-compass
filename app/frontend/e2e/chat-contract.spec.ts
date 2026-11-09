import { expect, test } from '@playwright/test';
import type { Connection } from '../src/types';

test('setup keeps cloud permission explicit and chat citations remain inspectable', async ({ page }, testInfo) => {
  // These neutral responses exercise the UI contract only; no provider, scripture or inference is simulated as research evidence.
  let connections: Connection[] = [];
  let localOnly = true;
  let saved = false;
  let saveBody: Record<string, unknown> | null = null;
  let chatBody: Record<string, unknown> | null = null;
  let chatCalls = 0;
  let snapshotChanged = false;
  const citation = { id: 'S1', passage_id: 'fixture-passage', source_id: 'fixture-source', source_title: 'Neutral source fixture', edition_title: 'UI test edition', reference: 'Fixture 1', quote: 'A neutral excerpt for a UI test.', url: 'https://example.org/fixture', collection_memberships: ['torah'], language: 'en', revision: 'fixture-v1', content_sha256: 'a'.repeat(64) };
  const original = { ...citation, passage_id: 'fixture-original', source_title: 'Hebrew test fixture', edition_title: 'Hebrew test edition', quote: 'טֶקְסְט לְבְדִיקָה', url: 'https://example.org/hebrew-fixture', language: 'hbo', source_type: 'original_text', alignment: 'same_reference', alignment_note: 'The fixture editions use the same reference.' };
  const result = { answer: 'Neutral fixture answer [S1]. <img src=x> remains text.', citations: [citation], warnings: ['This is a UI test fixture.'], connection_id: 'fixture-connection', model_id: 'fixture-account-model', grounding: { mode: 'retrieval', retrieved_count: 1, collections: ['torah'] }, session_id: 'fixture-session' };
  const conversation = { id: 'fixture-conversation', title: 'Explicitly saved fixture', dossier_id: null, created_at: new Date().toISOString() };
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    let body: unknown = { items: [] };
    if (path === '/health') body = { status: 'ready', version: 'test', database: { ready: true, message: '' }, features: {} };
    else if (path === '/connections' && request.method() === 'POST') {
      const data = request.postDataJSON();
      expect(data.provider).toBe('mistral');
      expect(data.api_key).toBe('fixture-not-a-secret');
      connections = [{ ...data, id: 'fixture-connection', local: false, configured: true, enabled: true, api_key_set: true, base_url: null }];
      // The write-only DTO deliberately omits the submitted key.
      delete (connections[0] as unknown as Record<string, unknown>).api_key;
      body = connections[0];
    } else if (path === '/connections') body = { items: connections };
    else if (path === '/chat-settings') {
      if (request.method() === 'PATCH') localOnly = request.postDataJSON().local_only;
      body = { local_only: localOnly };
    } else if (path === '/corpus') body = { items: [{ id: 'fixture-source', title: citation.source_title, url: citation.url, source_type: 'text', provenance: { test: true }, use_limits: { external_processing: true }, editions: [{ id: 'fixture-edition', title: citation.edition_title, language: 'en', revision: 'fixture-v1', collection_memberships: ['torah'], passage_count: 1 }] }] };
    else if (path === '/passages/fixture-passage/parallel') {
      const current = snapshotChanged ? { quote: 'A different current edition excerpt.', revision: 'fixture-v2' } : {};
      body = { anchor: { ...citation, source_type: 'translation', ...current }, parallels: [original], warnings: [] };
    } else if (path === '/chat') {
      chatCalls += 1; chatBody = request.postDataJSON();
      if (chatBody?.message === 'No matching evidence') {
        await route.fulfill({ status: 422, json: { error: { code: 'no_evidence', message: 'No suitable passages.' } } });
        return;
      }
      body = result;
    }
    else if (path === '/conversations' && request.method() === 'POST') { saveBody = request.postDataJSON(); saved = true; body = conversation; }
    else if (path === '/conversations') body = { items: saved ? [conversation] : [] };
    else if (path === '/conversations/fixture-conversation') body = { ...conversation, turns: [{ ...result, id: 'fixture-turn', question: 'Neutral UI question', created_at: conversation.created_at }] };
    await route.fulfill({ status: 200, json: body });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Models & settings', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Provider', exact: true })).toHaveValue('mistral');
  await page.getByLabel('Title', { exact: true }).fill('Fixture account');
  await page.getByLabel('Model ID', { exact: true }).fill('fixture-account-model');
  await page.getByLabel('API key', { exact: true }).fill('fixture-not-a-secret');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText('Key saved', { exact: false })).toBeVisible();
  await expect(page.getByLabel('API key', { exact: true })).toHaveValue('');
  await expect(page.getByRole('checkbox', { name: 'Local models only', exact: true })).toBeChecked();
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain('fixture-not-a-secret');
  await page.getByRole('checkbox', { name: 'Local models only', exact: true }).uncheck();
  await expect(page.getByRole('checkbox', { name: 'Local models only', exact: true })).not.toBeChecked();
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  await page.getByRole('combobox', { name: 'Choose a connection', exact: true }).selectOption('fixture-connection');
  await page.getByRole('textbox', { name: 'Research question', exact: true }).fill('Neutral UI question');
  await page.getByRole('button', { name: 'Ask Compass', exact: true }).click();
  await expect(page.getByText('Neutral fixture answer', { exact: false })).toBeVisible();
  expect(chatBody).toMatchObject({ message: 'Neutral UI question', connection_id: 'fixture-connection', language: 'auto' });
  expect(chatBody).not.toHaveProperty('conversation_id');
  expect(chatBody).not.toHaveProperty('api_key');
  await expect(page.locator('.assistant-message img')).toHaveCount(0);
  await page.getByRole('button', { name: '[S1]', exact: true }).click();
  const citationDetails = page.getByRole('complementary', { name: 'Citation details', exact: true });
  await expect(citationDetails.getByText(citation.quote, { exact: true })).toBeVisible();
  const anchorCard = citationDetails.getByRole('article').filter({ hasText: citation.quote });
  await expect(anchorCard.getByRole('link', { name: 'Open original source', exact: false })).toHaveAttribute('href', citation.url);
  const hebrewQuote = citationDetails.locator('blockquote').filter({ hasText: original.quote });
  await expect(hebrewQuote).toHaveAttribute('lang', 'he');
  await expect(hebrewQuote).toHaveAttribute('dir', 'rtl');
  await page.screenshot({ path: testInfo.outputPath('chat-citation-contract.png'), fullPage: true });
  await page.getByRole('button', { name: 'Research', exact: true }).click();
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  await expect(page.getByText('Neutral fixture answer', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Save conversation', exact: true }).click();
  await page.getByLabel('Conversation title', { exact: true }).fill(conversation.title);
  await page.getByRole('button', { name: 'Save conversation', exact: true }).last().click();
  await expect(page.getByText('Future turns will be saved', { exact: true })).toBeVisible();
  expect(saveBody).toEqual({ title: conversation.title, session_id: 'fixture-session' });
  await page.getByRole('button', { name: 'New temporary chat', exact: true }).click();
  await page.getByRole('combobox', { name: 'Saved conversations', exact: true }).selectOption(conversation.id);
  await expect(page.getByText('Neutral fixture answer', { exact: false })).toBeVisible();
  snapshotChanged = true;
  await page.getByRole('button', { name: '[S1]', exact: true }).click();
  await expect(citationDetails.getByText('The current edition differs from this snapshot.', { exact: false })).toBeVisible();
  await expect(citationDetails.getByText(citation.quote, { exact: true })).toBeVisible();
  await expect(citationDetails.getByText('A different current edition excerpt.', { exact: true })).toHaveCount(0);
  await expect(hebrewQuote).toHaveCount(0);
  await citationDetails.getByRole('button', { name: 'Close', exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath('chat-saved-contract.png'), fullPage: true });
  await page.getByRole('textbox', { name: 'Research question', exact: true }).fill('No matching evidence');
  await page.getByRole('combobox', { name: 'Answer language', exact: true }).selectOption('nl');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.getByRole('button', { name: 'Ask Compass', exact: true }).click();
  await expect(page.getByRole('alert').getByText('No suitable passages were found', { exact: false })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Research question', exact: true })).toHaveValue('No matching evidence');
  expect(chatCalls).toBe(2);
  expect(chatBody).toMatchObject({ language: 'nl' });
  await page.getByRole('combobox', { name: 'Interface language', exact: true }).selectOption('ar');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('combobox', { name: 'لغة الإجابة', exact: true })).toHaveValue('nl');
  await expect(page.getByRole('button', { name: 'اسأل Compass', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '[S1]', exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath('chat-arabic-contract.png'), fullPage: true });
});
