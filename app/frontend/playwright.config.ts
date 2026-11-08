import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  use: {
    baseURL: process.env.COMPASS_BASE_URL ?? 'http://127.0.0.1:8000',
    browserName: 'chromium',
    channel: process.env.COMPASS_BROWSER_CHANNEL ?? 'chrome',
    viewport: { width: 1500, height: 1050 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});
