import { defineConfig } from '@playwright/test'

// These checks deliberately target the running LangGraph and Vite services so
// navigation, catalog loading, and contract retrieval are validated together.
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173',
    browserName: 'chromium',
    channel: 'msedge',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  reporter: [['list']],
})
