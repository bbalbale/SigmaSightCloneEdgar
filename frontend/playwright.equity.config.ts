import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:3005',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'npm run dev',
      cwd: './',
      port: 3005,
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: 'uv run python run.py',
      cwd: '../backend',
      port: 8000,
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
});
