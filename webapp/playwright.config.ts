import { defineConfig } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const webappDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: './e2e',
  timeout: 180_000,
  expect: { timeout: 45_000 },
  retries: process.env.CI ? 2 : 1,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:10900',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
  },
  webServer: {
    command:
      'powershell -NoProfile -ExecutionPolicy Bypass -File .\\e2e-start-all.ps1',
    cwd: webappDir,
    url: 'http://127.0.0.1:10900/',
    reuseExistingServer: true,
    timeout: 180_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
