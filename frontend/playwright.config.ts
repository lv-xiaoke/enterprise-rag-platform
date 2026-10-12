import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(directory, '..');
const localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.E2E_PYTHON || (existsSync(localPython) ? localPython : 'python');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5174',
    channel: process.env.E2E_BROWSER_CHANNEL || undefined,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `"${python}" -m uvicorn e2e_app:app --app-dir "${path.join(root, 'tests')}" --host 127.0.0.1 --port 8011`,
      url: 'http://127.0.0.1:8011/health',
      timeout: 90_000,
      reuseExistingServer: false,
      env: {
        PYTHONPATH: root,
        RAG_E2E_TESTING: '1',
        APP_ORIGIN: 'http://localhost:5174',
        AUTH_COOKIE_SECURE: 'false',
      },
    },
    {
      command: 'npm run dev -- --host localhost --port 5174 --strictPort',
      url: 'http://localhost:5174',
      timeout: 60_000,
      reuseExistingServer: false,
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8011' },
    },
  ],
});
