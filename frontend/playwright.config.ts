import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3005',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 13'] },
    },
  ],

  webServer: [
    {
      command: 'cd /Users/elliottng/CascadeProjects/SigmaSight-BE/frontend && npm run dev',
      port: 3005,
      reuseExistingServer: true,
      timeout: 120 * 1000,
    },
    {
      command: 'cd /Users/elliottng/CascadeProjects/SigmaSight-BE/backend && uv run python run.py',
      port: 8000,
      reuseExistingServer: true,
      timeout: 120 * 1000,
    }
  ],
});