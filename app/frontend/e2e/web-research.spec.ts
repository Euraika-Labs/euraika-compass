import { expect, test } from '@playwright/test';
import type { ChatResponse, CorpusSource, ScriptureCitation, WebCitation } from '../src/types';

const scripture: ScriptureCitation = {
  id: 'S1', passage_id: 'fixture-scripture', source_id: 'fixture-corpus', source_title: 'Imported text fixture',
  edition_title: 'Fixture edition', reference: 'Fixture 1:1', quote: 'Imported passage fixture.',
  url: 'https://example.org/imported-text', collection_memberships: ['torah'], language: 'en', revision: 'fixture-v1',
  content_sha256: 'a'.repeat(64), source_type: 'translation',
};
const web: WebCitation = {
  id: 'S2', kind: 'web', title: 'Research article fixture', source_url: 'https://example.org/research',
  quote: 'A research excerpt. <img src=x> stays plain text.', source_type: 'journal_article',
  evidence_type: 'publisher_abstract', retrieved_at: '2026-11-09T16:00:00Z', authors: ['Fixture Author'],
  issued_date: '2024-10-01', publication: 'Fixture Journal', provider: 'fixture-index',
  license: 'Fixture licence', license_url: 'https://example.org/licence', content_sha256: 'b'.repeat(64),
  provenance: { record_url: 'https://example.org/index-record' },
};
const corpus: CorpusSource = {
  id: scripture.source_id, title: scripture.source_title, url: scripture.url, source_type: 'translation',
  provenance: {}, use_limits: { external_processing: true }, editions: [{ id: 'fixture-edition',
    title: scripture.edition_title, revision: scripture.revision, language: scripture.language,
    collection_memberships: scripture.collection_memberships, passage_count: 1 }],
};
const localAnswer: ChatResponse = {
  answer: 'Imported answer fixture [S1].', citations: [scripture], warnings: [],
  connection_id: 'fixture-local', model_id: 'fixture-local-model',
  grounding: { mode: 'retrieved_sources', retrieved_count: 1, collections: ['torah'], web_research: { status: 'off' } },
};
const mixedAnswer: ChatResponse = {
  ...localAnswer, answer: 'Mixed answer fixture [S1] with research context [S2].', citations: [scripture, web],
  grounding: { ...localAnswer.grounding, retrieved_count: 2,
    web_research: { status: 'used', source_count: 1, queries: ['neutral research query'], partial: true } },
};

test('web research is a per-question opt-in and mixed citations open their own evidence', async ({ page }) => {
  let localOnly = true;
  const submitted: boolean[] = [];
  const passageRequests: string[] = [];
  const conversation = { id: 'fixture-conversation', title: 'Stored mixed answer', dossier_id: null, created_at: web.retrieved_at };
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    let body: unknown = { items: [] };
    if (path === '/health') body = { status: 'ready', version: 'test', database: { ready: true, message: '' }, features: { web_research: true } };
    else if (path === '/connections') body = { items: [{ id: 'fixture-local', title: 'Local fixture', provider: 'local', model_id: localAnswer.model_id, base_url: null, local: true, enabled: true, configured: true, api_key_set: false }] };
    else if (path === '/chat-settings') {
      if (request.method() === 'PATCH') localOnly = request.postDataJSON().local_only;
      body = { local_only: localOnly };
    } else if (path === '/corpus') body = { items: [corpus] };
    else if (path === '/conversations') body = { items: [conversation] };
    else if (path === '/conversations/fixture-conversation') body = { ...conversation, turns: [{
      ...mixedAnswer, id: 'fixture-saved-turn', question: 'Saved fixture question', created_at: web.retrieved_at,
    }] };
    else if (path === '/chat') {
      const payload = request.postDataJSON();
      submitted.push(payload.web_research);
      if (payload.web_research && payload.message === 'Unused source fixture question') {
        body = { ...localAnswer, grounding: { ...localAnswer.grounding,
          web_research: { status: 'not_used', retrieved_count: 1, source_count: 0 } } };
      } else body = payload.web_research ? mixedAnswer : localAnswer;
    } else if (path.startsWith('/passages/')) {
      passageRequests.push(path);
      body = { anchor: scripture, parallels: [], warnings: [] };
    }
    await route.fulfill({ status: 200, json: body });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  const optIn = page.getByRole('checkbox', { name: 'Web research for this question', exact: true });
  const question = page.getByRole('textbox', { name: 'Research question', exact: true });
  const ask = page.getByRole('button', { name: 'Ask Compass', exact: true });
  await expect(optIn).toBeDisabled();
  await expect(optIn).not.toBeChecked();
  await expect(page.getByText('Web research is blocked while Local models only is on.', { exact: true })).toBeVisible();
  await page.getByRole('combobox', { name: 'Choose a connection', exact: true }).selectOption('fixture-local');
  await question.fill('Local fixture question');
  await ask.click();
  await expect(page.getByText('Web research off', { exact: true })).toBeVisible();
  expect(submitted).toEqual([false]);

  await page.getByRole('button', { name: 'Models & settings', exact: true }).click();
  await page.getByRole('checkbox', { name: 'Local models only', exact: true }).uncheck();
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  await expect(optIn).toBeEnabled();
  await expect(optIn).not.toBeChecked();
  await question.fill('Mixed fixture question');
  await optIn.check();
  await ask.click();
  await expect(page.getByText('Web research used · Sources: 1', { exact: true })).toBeVisible();
  await expect(optIn).not.toBeChecked();
  expect(submitted).toEqual([false, true]);
  await page.getByText('Web search queries', { exact: true }).click();
  await expect(page.getByText('neutral research query', { exact: true })).toBeVisible();
  await expect(page.getByText('Some searches could not be completed or returned sources Compass could not use.', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '[S2]', exact: true }).click();
  const details = page.getByRole('complementary', { name: 'Citation details', exact: true });
  const webCard = details.getByRole('article', { name: 'Web source', exact: true });
  await expect(webCard.getByText(web.title, { exact: true })).toBeVisible();
  await expect(webCard.getByText(web.quote, { exact: true })).toBeVisible();
  await expect(webCard.getByText('Publisher abstract', { exact: true })).toBeVisible();
  await expect(webCard.getByText('Fixture Author', { exact: true })).toBeVisible();
  await expect(webCard.getByRole('link', { name: /Open original source/ })).toHaveAttribute('href', web.source_url);
  await expect(webCard.getByRole('link', { name: /Open index record/ })).toHaveAttribute('href', web.provenance!.record_url!);
  await expect(webCard.getByRole('link', { name: /Fixture licence/ })).toHaveAttribute('href', web.license_url!);
  await expect(webCard.locator('img')).toHaveCount(0);
  expect(passageRequests).toEqual([]);

  await page.locator('.chat-turn').last().getByRole('button', { name: '[S1]', exact: true }).click();
  const reader = details.getByRole('region', { name: 'Parallel passage reader', exact: true });
  await expect(reader.getByText(scripture.quote, { exact: true })).toBeVisible();
  await expect(reader.getByText('No parallel passage was found among the imported editions.', { exact: true })).toBeVisible();
  expect(passageRequests).toEqual(['/passages/fixture-scripture/parallel']);

  await question.fill('Unused source fixture question');
  await optIn.check();
  await ask.click();
  await expect(page.getByText('Web sources found. The answer cites none.', { exact: true })).toBeVisible();
  await expect(optIn).not.toBeChecked();
  expect(submitted).toEqual([false, true, true]);

  await page.getByRole('combobox', { name: 'Saved conversations', exact: true }).selectOption(conversation.id);
  await expect(page.getByText('Saved fixture question', { exact: true })).toBeVisible();
  await expect(page.getByText('Web research used · Sources: 1', { exact: true })).toBeVisible();
  await expect(optIn).not.toBeChecked();
});
