import { createHash } from 'node:crypto';
import { expect, test } from '@playwright/test';
import type { ChatResponse, Connection } from '../src/types';

test('live research cites both a stored edition and an online source', async ({ page }, testInfo) => {
  test.skip(process.env.COMPASS_LIVE_WEB !== '1', 'Explicit opt-in: this uses web services and a configured Mistral model.');
  test.setTimeout(540_000);
  const catalog = await page.request.get('/api/v1/connections');
  expect(catalog.ok()).toBeTruthy();
  const connection = ((await catalog.json()).items as Connection[]).find(item =>
    item.provider === 'mistral' && item.model_id === 'mistral-large-4-0' && item.configured && item.enabled);
  expect(connection, 'Configure Mistral Large 4.0 and allow online processing before the live test.').toBeTruthy();
  await page.goto('/');
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  await page.getByRole('combobox', { name: 'Choose a connection', exact: true }).selectOption(connection!.id);
  await page.getByRole('textbox', { name: 'Research question', exact: true }).fill(
    'Compare the Greek and English of John 1:1. Search for scholarly background on John 1:1 and the Logos. Distinguish what the verse says from how the authors of the online sources interpret it.',
  );
  const webSwitch = page.getByRole('checkbox', { name: 'Web research for this question' });
  await expect(webSwitch).not.toBeChecked();
  await webSwitch.check();
  const pending = page.waitForResponse(response =>
    response.url().endsWith('/api/v1/chat') && response.request().method() === 'POST', { timeout: 510_000 });
  await page.getByRole('button', { name: 'Ask Compass', exact: true }).click();
  const response = await pending;
  const reply = await response.json() as ChatResponse;
  expect(response.ok(), JSON.stringify(reply)).toBeTruthy();
  expect(reply.model_id).toBe('mistral-large-4-0');
  expect(reply.grounding.web_research?.status, JSON.stringify(reply.grounding.web_research)).toBe('used');
  expect(reply.grounding.web_research?.queries?.length).toBeGreaterThan(0);
  const web = reply.citations.find(item => item.kind === 'web' && item.provider === 'doaj');
  const edition = reply.citations.find(item => item.kind !== 'web' && item.reference === 'John 1:1' && item.language === 'grc');
  expect(web, 'The model should cite a retrieved publisher abstract.').toBeTruthy();
  expect(edition, 'The model should cite the stored Greek passage from John.').toBeTruthy();
  expect(reply.citations.some(item => item.kind !== 'web' && item.reference === 'John 1:1' && item.language === 'en')).toBeTruthy();
  if (!web || !edition || edition.kind === 'web') throw new Error('Missing mixed evidence');
  expect(web.source_url).toMatch(/^https:\/\//);
  expect(web.content_sha256).toMatch(/^[0-9a-f]{64}$/);
  expect(web).toHaveProperty('quote_sha256', createHash('sha256').update(web.quote).digest('hex'));
  const stored = await page.request.get('/api/v1/passages/' + edition.passage_id);
  expect(stored.ok()).toBeTruthy();
  expect((await stored.json()).quote).toBe(edition.quote);
  await expect(webSwitch).not.toBeChecked();
  await page.locator('.citation-chip').filter({ hasText: `[${edition.id}]` }).click();
  const details = page.getByRole('complementary', { name: 'Citation details' });
  await expect(details).toContainText(edition.quote);
  await page.locator('.citation-chip').filter({ hasText: `[${web.id}]` }).click();
  await expect(details.getByRole('article', { name: 'Web source' })).toContainText(web.quote);
  await expect(details.getByRole('link', { name: 'Open original source' })).toHaveAttribute('href', web.source_url);
  await page.screenshot({ path: testInfo.outputPath('live-web-research.png'), fullPage: true });
  testInfo.annotations.push({ type: 'online evidence', description: `${web.provider}: ${web.source_url}` });
});
