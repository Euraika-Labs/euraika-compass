import { expect, test } from '@playwright/test';
import type { CorpusSource, ParallelPassage, PassageSnapshot } from '../src/types';

const common = {
  url: 'https://example.org/parallel-fixture', revision: 'fixture-v1', content_sha256: 'a'.repeat(64),
  source_type: 'original_text',
};
// Neutral excerpts exercise the actual scripts and UI contract without making claims about an edition.
const hebrew: PassageSnapshot = {
  ...common, passage_id: 'hebrew', source_id: 'source-hebrew', source_title: 'Hebrew source fixture', edition_title: 'Hebrew fixture',
  reference: 'Genesis 1:1', quote: 'טֶקְסְט לְבְדִיקָה', language: 'hbo', collection_memberships: ['torah'],
};
const greek: PassageSnapshot = {
  ...common, passage_id: 'greek', source_id: 'source-greek', source_title: 'Greek source fixture', edition_title: 'Greek fixture',
  reference: 'John 1:1', quote: 'παράδειγμα κειμένου', language: 'grc', collection_memberships: ['bible'],
};
const arabic: PassageSnapshot = {
  ...common, passage_id: 'arabic', source_id: 'source-arabic', source_title: 'Arabic source fixture', edition_title: 'Arabic fixture',
  reference: 'Quran 1:1', quote: 'نَصٌّ لِلاِخْتِبَارِ', language: 'ar', collection_memberships: ['quran'],
  use_limits: { external_processing: true, rights_note: 'Preserve the fixture edition attribution.' },
  licence_url: 'https://example.org/fixture-licence',
};
const translation: ParallelPassage = {
  ...common, passage_id: 'translation', source_id: 'source-translation', source_title: 'English source fixture', edition_title: 'English fixture',
  reference: 'Genesis 1:1', quote: 'A neutral translation fixture.', language: 'en', collection_memberships: ['torah'],
  source_type: 'translation', alignment: 'same_reference', alignment_note: 'The fixtures share a reference.',
};
const uncertain: ParallelPassage = {
  ...translation, passage_id: 'uncertain', edition_title: 'Unverified edition fixture', reference: 'John 1:2',
  quote: 'An unverified comparison fixture.', alignment: 'compare_only', alignment_note: 'No verified verse mapping is available.',
};
const editions = [hebrew, greek, arabic, translation];
const sources: CorpusSource[] = editions.map(passage => ({
  id: passage.source_id, title: passage.source_title, source_type: passage.source_type!, url: passage.url, provenance: { test: true },
  use_limits: passage.use_limits ?? { external_processing: true },
  editions: [{ id: `edition-${passage.passage_id}`, title: passage.edition_title, language: passage.language, revision: passage.revision,
    passage_count: 1, collection_memberships: passage.collection_memberships }],
}));

test('library compares editions with the passage script, honest alignment and responsive layout', async ({ page }, testInfo) => {
  let greekAttempts = 0;
  const searches: URLSearchParams[] = [];
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace('/api/v1', '');
    let body: unknown = { items: [] };
    if (path === '/health') body = { status: 'ready', version: 'test', database: { ready: true, message: '' }, features: {} };
    else if (path === '/chat-settings') body = { local_only: true };
    else if (path === '/corpus') body = { items: sources };
    else if (path === '/corpus/search') {
      searches.push(url.searchParams);
      const matches = editions.filter(passage => passage.reference === url.searchParams.get('q'));
      const filter = url.searchParams.get('source_id');
      body = { items: filter ? matches.filter(passage => passage.source_id === filter) : matches };
    } else if (path === '/passages/hebrew/parallel') body = { anchor: hebrew, parallels: [uncertain, translation], warnings: [] };
    else if (path === '/passages/greek/parallel') {
      if (++greekAttempts === 1) {
        await route.fulfill({ status: 503, json: { error: { code: 'database_unavailable', message: 'Fixture retry.' } } });
        return;
      }
      body = { anchor: greek, parallels: [uncertain], warnings: [] };
    } else if (path === '/passages/arabic/parallel') body = { anchor: arabic, parallels: [], warnings: [] };
    await route.fulfill({ status: 200, json: body });
  });

  await page.goto('/');
  await page.locator('.sidebar').getByRole('button', { name: 'Sources', exact: true }).click();
  const query = page.getByRole('searchbox', { name: 'Reference or topic', exact: true });
  const search = page.getByRole('button', { name: 'Search passages', exact: true });
  const results = page.getByRole('group', { name: 'Matching passages', exact: true });
  const reader = page.getByRole('region', { name: 'Parallel passage reader', exact: true });
  await page.getByRole('combobox', { name: 'Collections', exact: true }).selectOption('torah');
  await page.getByRole('combobox', { name: 'Sources', exact: true }).selectOption('source-hebrew');
  await query.fill('Genesis 1:1');
  await search.click();
  await results.getByRole('button', { name: /Genesis 1:1.*Hebrew fixture/ }).click();
  expect(searches.at(-1)?.get('collection')).toBe('torah');
  expect(searches.at(-1)?.get('source_id')).toBe('source-hebrew');

  const hebrewQuote = reader.locator('blockquote').filter({ hasText: hebrew.quote });
  const translationQuote = reader.locator('blockquote').filter({ hasText: translation.quote });
  await expect(hebrewQuote).toHaveAttribute('lang', 'he');
  await expect(hebrewQuote).toHaveAttribute('dir', 'rtl');
  await expect(translationQuote).toHaveAttribute('dir', 'ltr');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  const [desktopOriginal, desktopTranslation] = await Promise.all([hebrewQuote.boundingBox(), translationQuote.boundingBox()]);
  expect(desktopTranslation!.x).toBeGreaterThan(desktopOriginal!.x + 100);
  await page.screenshot({ path: testInfo.outputPath('library-parallel-fixture.png'), fullPage: true });
  await reader.getByRole('combobox', { name: 'Parallel edition', exact: true }).selectOption('uncertain');
  await expect(reader.getByText('The relationship between these passages is unverified.', { exact: true })).toBeVisible();
  await expect(reader.getByText(translation.quote, { exact: true })).toHaveCount(0);
  await reader.getByRole('combobox', { name: 'Parallel edition', exact: true }).selectOption('translation');
  await page.setViewportSize({ width: 430, height: 900 });
  const [mobileOriginal, mobileTranslation] = await Promise.all([hebrewQuote.boundingBox(), translationQuote.boundingBox()]);
  expect(Math.abs(mobileTranslation!.x - mobileOriginal!.x)).toBeLessThan(2);
  expect(mobileTranslation!.y).toBeGreaterThan(mobileOriginal!.y + mobileOriginal!.height);

  await page.getByRole('combobox', { name: 'Collections', exact: true }).selectOption('');
  await page.getByRole('combobox', { name: 'Sources', exact: true }).selectOption('');
  await query.fill('John 1:1');
  await search.click();
  await results.getByRole('button', { name: /John 1:1.*Greek fixture/ }).click();
  const greekQuote = reader.locator('blockquote').filter({ hasText: greek.quote });
  await expect(greekQuote).toHaveAttribute('lang', 'grc');
  await expect(greekQuote).toHaveAttribute('dir', 'ltr');
  await expect(reader.getByRole('alert')).toContainText('Parallel passages could not be loaded');
  await reader.getByRole('button', { name: 'Retry loading passages', exact: true }).click();
  await expect(reader.getByText('Only comparison candidates are available for this passage.', { exact: true })).toBeVisible();

  await query.fill('Quran 1:1');
  await search.click();
  await results.getByRole('button', { name: /Quran 1:1.*Arabic fixture/ }).click();
  const arabicQuote = reader.locator('blockquote').filter({ hasText: arabic.quote });
  await expect(arabicQuote).toHaveAttribute('lang', 'ar');
  await expect(arabicQuote).toHaveAttribute('dir', 'rtl');
  await expect(reader.getByText(arabic.use_limits!.rights_note!, { exact: true })).toBeVisible();
  await expect(reader.getByRole('link', { name: /View licence/ })).toHaveAttribute('href', arabic.licence_url!);
  await expect(reader.getByText('No parallel passage was found among the imported editions.', { exact: true })).toBeVisible();

  await query.fill('unmatched topic');
  await search.click();
  await expect(page.getByText('No passages match this search.', { exact: false })).toBeVisible();
  expect(searches.at(-1)?.get('q')).toBe('unmatched topic');
});
