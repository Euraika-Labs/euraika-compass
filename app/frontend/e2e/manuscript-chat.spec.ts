import { expect, test } from '@playwright/test';
import type { ChatResponse, Dossier, ManuscriptCitation, ManuscriptReadingChoice } from '../src/types';

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAIAAAAUMWhjAAAAM0lEQVR4nO3RwQ0AMAjDQMr+O6cjmE9+vgGCZF6Sadrq+njgwB8gEyETIRMhEyEToXqiDwu6Ay07tmdtAAAAAElFTkSuQmCC', 'base64');
const time = '2026-11-10T16:00:00Z';
const dossier: Dossier = { id: 'dossier-fixture', title: 'Manuscript dossier fixture', question: '', notes: '', revision: 1, created_at: time, updated_at: time };
const otherDossier: Dossier = { ...dossier, id: 'other-fixture', title: 'Other dossier fixture' };
const reading: ManuscriptReadingChoice = {
  id: 'allowed-revision', image_id: 'image-fixture', title: 'Catalogue manuscript fixture', folio_label: 'f. 2r',
  created_at: time, kind: 'user_corrected', language: 'he', external_processing: true,
};
const restricted: ManuscriptReadingChoice = { ...reading, id: 'restricted-revision', title: 'Restricted manuscript fixture', external_processing: false };
const region = { x: 3.5, y: 5.25, width: 8.5, height: 6.5, coordinate_system: 'original_image_pixels', kind: 'text_region' } as const;
const citation: ManuscriptCitation = {
  id: 'S1', kind: 'manuscript', source_type: 'manuscript_transcription', evidence_type: reading.kind, title: reading.title,
  reference: reading.folio_label, quote: 'טֶקְסְט לְבְדִיקָה', quote_sha256: 'a'.repeat(64), excerpt_start: 2, excerpt_end: 16,
  image_id: reading.image_id, image_content_url: '/api/v1/images/image-fixture/content', image_width: 32, image_height: 24,
  dossier_id: dossier.id, transcription_id: reading.id, created_at: time, language: reading.language, folio_label: reading.folio_label,
  engine: 'manual', model_id: 'manual', region,
  provenance: { kind: 'manuscript', institution: 'Neutral fixture collection', shelfmark: 'MS TEST', catalog_url: 'https://example.org/catalogue', attribution: 'Neutral fixture attribution.' },
};
const crop = { x: 4, y: 6, width: 10, height: 8, coordinate_system: 'original_image_pixels', kind: 'input_crop' } as const;
const reply: ChatResponse = {
  answer: 'The fixture answer draws on three recorded excerpts [S1] [S2] [S3].',
  citations: [citation, { ...citation, id: 'S2', quote: 'קטע', region: crop }, { ...citation, id: 'S3', quote: 'ללא אזור', region: null }],
  warnings: [], connection_id: 'local-fixture', model_id: 'local-fixture-model', session_id: 'fixture-session',
  grounding: { mode: 'retrieved_sources', retrieved_count: 3, collections: [], manuscripts: { status: 'used', retrieved_count: 3, source_count: 3, blocked_count: 0 } },
};

test('chat uses selected manuscript revisions and preserves image coordinates and scope', async ({ page }) => {
  const submitted: Record<string, unknown>[] = [];
  const saved = { id: 'saved-fixture', title: 'Saved manuscript fixture', dossier_id: dossier.id, created_at: time };
  let savedCreated = false;
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    let body: unknown = { items: [] };
    if (path === '/health') body = { status: 'ok', version: 'test', database: { ready: true, message: '' }, features: {} };
    else if (path === '/connections') body = { items: [
      { id: 'local-fixture', title: 'Local fixture', provider: 'local', model_id: reply.model_id, base_url: null, local: true, enabled: true, configured: true, api_key_set: false },
      { id: 'cloud-fixture', title: 'Cloud fixture', provider: 'mistral', model_id: 'cloud-fixture-model', base_url: null, local: false, enabled: true, configured: true, api_key_set: true },
    ] };
    else if (path === '/chat-settings') body = { local_only: false };
    else if (path === '/dossiers') body = { items: [dossier, otherDossier] };
    else if (path === '/dossiers/dossier-fixture/manuscript-readings') body = { items: [reading, restricted], truncated: false };
    else if (path === '/dossiers/other-fixture/manuscript-readings') body = { items: [], truncated: false };
    else if (path === '/images/image-fixture/content') {
      await route.fulfill({ status: 200, contentType: 'image/png', body: png });
      return;
    } else if (path === '/chat') {
      submitted.push(request.postDataJSON());
      body = { ...reply, turn_id: `fixture-turn-${submitted.length}` };
    } else if (path === '/conversations' && request.method() === 'POST') {
      expect(request.postDataJSON().session_id).toBe(reply.session_id);
      savedCreated = true;
      body = saved;
    } else if (path === '/conversations') body = { items: savedCreated ? [saved] : [] };
    else if (path === '/conversations/saved-fixture') body = { ...saved, turns: [{ ...reply, id: 'stored-turn', question: 'First fixture question', created_at: time }] };
    await route.fulfill({ status: 200, json: body });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  const model = page.getByRole('combobox', { name: 'Choose a connection', exact: true });
  const optIn = page.getByRole('checkbox', { name: 'Include manuscript readings from a dossier', exact: true });
  const scope = page.getByRole('combobox', { name: 'Manuscript source dossier', exact: true });
  const allowedReading = page.getByRole('checkbox', { name: /Catalogue manuscript fixture/ });
  const restrictedReading = page.getByRole('checkbox', { name: /Restricted manuscript fixture/ });
  const question = page.getByRole('textbox', { name: 'Research question', exact: true });
  const ask = page.getByRole('button', { name: 'Ask Compass', exact: true });
  await model.selectOption('local-fixture');
  await question.fill('First fixture question');
  await expect(ask).toBeDisabled();
  await expect(optIn).not.toBeChecked();
  await optIn.check();
  await scope.selectOption(dossier.id);
  await allowedReading.check();
  await scope.selectOption(otherDossier.id);
  await expect(page.getByText('No catalogue manuscript readings are saved in this dossier.', { exact: true })).toBeVisible();
  await expect(ask).toBeDisabled();
  await scope.selectOption(dossier.id);
  await expect(allowedReading).not.toBeChecked();
  await allowedReading.check();
  await ask.click();
  await expect(page.getByText('Manuscript readings cited · 3', { exact: true })).toBeVisible();
  expect(submitted[0]).toMatchObject({ manuscript_dossier_id: dossier.id, manuscript_revision_ids: [reading.id], allow_manuscript_cloud: false, source_ids: [], collection_filter: [] });

  const card = page.getByRole('article', { name: 'Manuscript reading', exact: true });
  const image = page.locator('.manuscript-coordinate-image');
  const overlay = page.locator('.manuscript-evidence .region-overlay');
  async function expectRegion(expected: { x: number; y: number; width: number; height: number }) {
    await expect(overlay).toBeVisible();
    const [pixels, box] = await Promise.all([image.boundingBox(), overlay.boundingBox()]);
    expect(Math.abs(box!.x - pixels!.x - pixels!.width * expected.x / 32)).toBeLessThan(1);
    expect(Math.abs(box!.y - pixels!.y - pixels!.height * expected.y / 24)).toBeLessThan(1);
    expect(Math.abs(box!.width - pixels!.width * expected.width / 32)).toBeLessThan(1);
  }
  await page.getByRole('button', { name: '[S1]', exact: true }).click();
  await expect(card.locator('blockquote')).toHaveText(citation.quote);
  await expect(card.locator('blockquote')).toHaveAttribute('dir', 'rtl');
  await expect(image).toHaveAttribute('src', citation.image_content_url!);
  await expectRegion(region);
  await expect(card.getByRole('link', { name: /Open collection record/ })).toHaveAttribute('href', citation.provenance!.catalog_url!);
  await card.getByText('Saved reading revision', { exact: true }).click();
  await expect(card.getByText(reading.id, { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '[S2]', exact: true }).click();
  await expect(card.getByText('Area supplied for this reading', { exact: true })).toBeVisible();
  await expectRegion(crop);
  await page.getByRole('button', { name: '[S3]', exact: true }).click();
  await expect(card.getByText('Folio-level evidence. Compare the excerpt with the full scan.', { exact: true })).toBeVisible();
  await expect(overlay).toHaveCount(0);

  await restrictedReading.check();
  await model.selectOption('cloud-fixture');
  await question.fill('Cloud follow-up fixture');
  await expect(page.getByText('Remove readings restricted to local use or choose a local model.', { exact: true })).toBeVisible();
  await expect(ask).toBeDisabled();
  await restrictedReading.uncheck();
  await expect(restrictedReading).toBeDisabled();
  const consent = page.getByRole('checkbox', { name: 'Send permitted reading excerpts to this cloud model for this question', exact: true });
  await expect(ask).toBeDisabled();
  await consent.check();
  await ask.click();
  await expect(page.getByText('Manuscript readings cited · 3', { exact: true })).toHaveCount(2);
  await expect(consent).not.toBeChecked();
  expect(submitted[1]).toMatchObject({ connection_id: 'cloud-fixture', manuscript_revision_ids: [reading.id], allow_manuscript_cloud: true });
  expect(submitted[1].history).toEqual([{ role: 'user', content: 'First fixture question' }]);

  await page.getByRole('button', { name: 'Save conversation', exact: true }).click();
  await page.getByRole('textbox', { name: 'Conversation title', exact: true }).fill(saved.title);
  await page.getByRole('button', { name: 'Save conversation', exact: true }).last().click();
  await expect(page.getByText('Future turns will be saved', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'New temporary chat', exact: true }).click();
  await page.getByRole('combobox', { name: 'Saved conversations', exact: true }).selectOption(saved.id);
  await expect(page.getByText('Manuscript readings cited · 3', { exact: true })).toBeVisible();
  await expect(optIn).not.toBeChecked();
  await optIn.check();
  await expect(scope.locator(`option[value="${otherDossier.id}"]`)).toHaveCount(0);
  await page.getByRole('button', { name: '[S1]', exact: true }).click();
  await page.getByRole('combobox', { name: 'Interface language', exact: true }).selectOption('ar');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expectRegion(region);
});
