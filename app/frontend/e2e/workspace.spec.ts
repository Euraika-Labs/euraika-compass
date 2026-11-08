import { expect, test } from '@playwright/test';

test('personal research preserves a draft, an original image and a manual reading', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.getByText('Research storage ready', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  await page.getByRole('textbox', { name: 'Research question', exact: true }).fill('Which visible letters can I identify?');
  await page.getByRole('button', { name: 'Research', exact: true }).click();
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Research question', exact: true })).toHaveValue('Which visible letters can I identify?');
  await page.getByRole('button', { name: 'Research', exact: true }).click();

  const title = `Skeleton browser check ${Date.now()}`;
  await page.getByRole('button', { name: /New research/ }).first().click();
  await page.getByLabel('Dossier title', { exact: true }).first().fill(title);
  await page.getByRole('button', { name: 'Create dossier', exact: true }).click();
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  // A tiny neutral PNG is a file-handling fixture, not manuscript evidence or a model reading.
  await page.locator('input[type="file"]').setInputFiles({
    name: 'fixture.png', mimeType: 'image/png',
    buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAIAAAAUMWhjAAAAM0lEQVR4nO3RwQ0AMAjDQMr+O6cjmE9+vgGCZF6Sadrq+njgwB8gEyETIRMhEyEToXqiDwu6Ay07tmdtAAAAAElFTkSuQmCC', 'base64'),
  });
  await expect(page.getByRole('img', { name: 'fixture.png' })).toBeVisible();
  const reading = 'Manual fixture note · αβγ · אבג · ابت';
  await page.getByRole('textbox', { name: 'Transcription', exact: true }).fill(reading);
  await page.getByRole('button', { name: 'Save manual reading', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save new revision', exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: title, exact: false }).click();
  await expect(page.getByRole('textbox', { name: 'Transcription', exact: true })).toHaveValue(reading);
  await page.screenshot({ path: testInfo.outputPath('research-workspace.png'), fullPage: true });
  await page.getByRole('combobox', { name: 'Interface language', exact: true }).selectOption('ar');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar');
  await page.screenshot({ path: testInfo.outputPath('research-arabic.png'), fullPage: true });
});
