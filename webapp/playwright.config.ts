import { defineConfig, devices } from '@playwright/test';

/**
 * Tier 3 end-to-end config. No specs exist yet — they arrive in Phase 1 once
 * there is a working journey to drive.
 *
 * All three engines are targeted from the start because "all modern browsers"
 * is a locked decision (CLAUDE.md section 10.1), and WebKit is the one most
 * likely to behave differently. Finding that out in Phase 3 would be too late.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: 'list',

  use: {
    baseURL: 'http://127.0.0.1:5173/studio/',
    trace: 'on-first-retry',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:5173/studio/',
    reuseExistingServer: !process.env.CI,
  },
});
