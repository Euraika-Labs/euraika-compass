import { expect, test } from '@playwright/test';
import type { Dossier, ImageAsset, Manuscript, ManuscriptFolio, ModelRoute } from '../src/types';

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAIAAAAUMWhjAAAAM0lEQVR4nO3RwQ0AMAjDQMr+O6cjmE9+vgGCZF6Sadrq+njgwB8gEyETIRMhEyEToXqiDwu6Ay07tmdtAAAAAElFTkSuQmCC', 'base64');
const manuscript: Manuscript = {
  id: 'catalogue-fixture', title: 'Catalogue manuscript fixture', institution: 'Collection fixture', shelfmark: 'MS TEST',
  language: 'he', collections: ['torah'], date: 'Fixture date', description: 'A neutral catalogue fixture.',
  catalog_url: 'https://example.org/catalogue', manifest_url: 'https://example.org/manifest',
  attribution: 'Attribution for the neutral UI fixture.', rights_url: 'https://example.org/rights',
  use_limits: { preview: true, local_storage: true, local_ocr: true, external_processing: false },
};
const folio: ManuscriptFolio = {
  id: 'folio-2r', label: 'f. 2r', index: 1, canvas_id: 'https://example.org/canvas/2r', width: 32, height: 24,
  source_url: 'https://example.org/folio/2r', preview_url: '/api/v1/manuscripts/catalogue-fixture/folios/folio-2r/preview',
  use_limits: manuscript.use_limits,
};
const blockedFolio: ManuscriptFolio = {
  ...folio, id: 'folio-1r', label: 'f. 1r', index: 0, canvas_id: 'https://example.org/canvas/1r',
  source_url: 'https://example.org/folio/1r', preview_url: null,
  use_limits: { preview: false, local_storage: false, local_ocr: false, external_processing: false },
};
const timestamp = '2026-11-09T16:00:00Z';
const dossier: Dossier = { id: 'target', title: 'Target dossier', question: '', notes: '', revision: 1, created_at: timestamp, updated_at: timestamp };
const priorDossier: Dossier = { ...dossier, id: 'prior', title: 'Prior dossier' };
const priorImage: ImageAsset = { id: 'prior-image', dossier_id: priorDossier.id, filename: 'prior.png', media_type: 'image/png', width: 32, height: 24, sha256: 'c'.repeat(64), created_at: timestamp };
const targetFirstImage: ImageAsset = { ...priorImage, id: 'target-old-image', dossier_id: dossier.id, filename: 'target-first.png' };
const attached: ImageAsset = {
  ...priorImage, id: 'attached-folio', dossier_id: dossier.id, filename: 'MS TEST - f. 2r.png', sha256: 'a'.repeat(64),
  provenance: {
    kind: 'manuscript', manuscript_id: manuscript.id, manuscript_title: manuscript.title, institution: manuscript.institution,
    shelfmark: manuscript.shelfmark, language: manuscript.language, date: manuscript.date, catalog_url: manuscript.catalog_url,
    manifest_url: manuscript.manifest_url, manifest_sha256: 'b'.repeat(64), folio_id: folio.id, folio_label: folio.label,
    canvas_id: folio.canvas_id, image_url: 'https://example.org/image/2r', source_url: folio.source_url,
    attribution: manuscript.attribution, rights_url: manuscript.rights_url, use_limits: folio.use_limits, retrieved_at: timestamp,
  },
};
const localRoute: ModelRoute = {
  id: 'local-fixture', title: 'Local OCR fixture', model_id: 'fixture-ocr', provider: 'kraken', local: true,
  kind: 'ocr', enabled: true, configured: true, available: true, status: 'configured', message: '', capabilities: ['image_transcription'],
};
const externalRoute: ModelRoute = { ...localRoute, id: 'external-fixture', title: 'External OCR fixture', provider: 'openai', local: false };

test('manuscript rights, preview and exact local reading handoff follow the catalogue', async ({ page }) => {
  let previewAttempts = 0;
  const searches: URLSearchParams[] = [];
  const imports: unknown[] = [];
  const jobs: unknown[] = [];
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1', '');
    let body: unknown = { items: [] };
    if (path === '/health') body = { status: 'ready', version: 'test', database: { ready: true, message: '' }, features: {} };
    else if (path === '/models') body = { items: [localRoute, externalRoute] };
    else if (path === '/dossiers') body = { items: [priorDossier, dossier] };
    else if (path === '/dossiers/prior') body = priorDossier;
    else if (path === '/dossiers/target') body = dossier;
    else if (path === '/dossiers/prior/images') body = { items: [priorImage] };
    else if (path === '/dossiers/target/images') body = { items: [targetFirstImage, attached] };
    else if (path === '/manuscripts') {
      searches.push(url.searchParams);
      body = { items: [manuscript] };
    } else if (path === '/manuscripts/catalogue-fixture/folios') body = { manuscript, items: [blockedFolio, folio], manifest_sha256: 'b'.repeat(64) };
    else if (path === '/manuscripts/catalogue-fixture/folios/folio-2r/preview') {
      if (++previewAttempts === 1) await route.fulfill({ status: 503, json: { error: { code: 'fixture_failure', message: 'Preview retry fixture.' } } });
      else await route.fulfill({ status: 200, contentType: 'image/png', body: png });
      return;
    } else if (path === '/manuscripts/catalogue-fixture/folios/folio-2r/import') {
      imports.push(request.postDataJSON());
      body = attached;
    } else if (path.endsWith('/content')) {
      await route.fulfill({ status: 200, contentType: 'image/png', body: png });
      return;
    } else if (path === '/transcription-jobs' || path === '/jobs/fixture-job') {
      if (request.method() === 'POST') jobs.push(request.postDataJSON());
      body = { id: 'fixture-job', image_id: attached.id, route_id: localRoute.id, status: 'queued', message: '', created_at: timestamp, updated_at: timestamp };
    }
    await route.fulfill({ status: 200, json: body });
  });

  await page.goto('/');
  await page.getByRole('button', { name: /Prior dossier/ }).click();
  const readingModel = page.getByRole('combobox', { name: 'Reading model', exact: true });
  await readingModel.selectOption(externalRoute.id);
  await page.getByRole('button', { name: 'Manuscripts', exact: true }).click();
  const language = page.getByRole('combobox', { name: 'Manuscript language', exact: true });
  await language.selectOption('he');
  await page.getByRole('searchbox', { name: 'Title, shelfmark or institution', exact: true }).fill(manuscript.shelfmark);
  await page.getByRole('button', { name: 'Search manuscripts', exact: true }).click();
  await page.getByRole('button', { name: /Catalogue manuscript fixture/ }).click();
  expect(searches.at(-1)?.get('q')).toBe(manuscript.shelfmark);
  expect(searches.at(-1)?.get('language')).toBe('he');
  await expect(page.getByRole('link', { name: /Open collection record/ })).toHaveAttribute('href', manuscript.catalog_url);
  await expect(page.getByRole('link', { name: /Open rights statement/ })).toHaveAttribute('href', manuscript.rights_url!);
  await expect(page.getByText(manuscript.attribution, { exact: true })).toBeVisible();

  const picker = page.getByRole('combobox', { name: 'Folio', exact: true });
  const attach = page.getByRole('button', { name: 'Add folio to dossier', exact: true });
  await picker.selectOption(blockedFolio.id);
  await expect(page.getByText('Preview is restricted by the collection’s terms.', { exact: true })).toBeVisible();
  await expect(page.getByText('The collection’s terms allow consultation but restrict saving this scan to a dossier.', { exact: true })).toBeVisible();
  await expect(attach).toHaveCount(0);
  expect(previewAttempts).toBe(0);

  await picker.selectOption(folio.id);
  await expect(page.getByRole('alert').getByText('The folio scan could not be displayed.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  const preview = page.getByRole('img', { name: `${manuscript.title} — ${folio.label}`, exact: true });
  await expect.poll(() => preview.evaluate(image => (image as HTMLImageElement).naturalWidth)).toBe(32);
  await expect(attach).toBeDisabled();
  await page.getByRole('combobox', { name: 'Destination dossier', exact: true }).selectOption(dossier.id);
  await attach.click();
  await expect(page.getByRole('status').getByText('Folio saved to dossier', { exact: true })).toBeVisible();
  expect(imports).toEqual([{ dossier_id: dossier.id }]);
  expect(jobs).toEqual([]);
  await page.getByRole('button', { name: 'Open saved scan in Research', exact: true }).click();
  await expect(page.getByRole('heading', { name: dossier.title, exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: attached.filename, exact: true })).toBeVisible();
  const savedRecord = page.locator('.manuscript-scan-record');
  await expect(savedRecord.getByText(manuscript.attribution, { exact: true })).toBeVisible();
  await expect(savedRecord.getByRole('link', { name: /Open folio source/ })).toHaveAttribute('href', folio.source_url!);
  await expect(readingModel).toHaveValue('');
  await expect(readingModel.locator(`option[value="${externalRoute.id}"]`)).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Read text', exact: true })).toBeDisabled();
  await readingModel.selectOption(localRoute.id);
  await page.getByRole('button', { name: 'Read text', exact: true }).click();
  await expect.poll(() => jobs).toEqual([{ image_id: attached.id, route_id: localRoute.id, language: manuscript.language }]);

  await page.getByRole('button', { name: 'Manuscripts', exact: true }).click();
  await expect(picker).toHaveValue(folio.id);
  await page.getByRole('combobox', { name: 'Interface language', exact: true }).selectOption('ar');
  await expect(page.getByRole('heading', { name: 'المخطوطات', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
});
