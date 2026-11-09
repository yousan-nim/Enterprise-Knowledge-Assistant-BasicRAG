import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${process.env.FRONTEND_TEST_PORT || 3100}`,
    browserName: "chromium",
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `npm run dev -- --port ${process.env.FRONTEND_TEST_PORT || 3100}`,
    env: { BACKEND_URL: "http://127.0.0.1:18081" },
    url: `http://127.0.0.1:${process.env.FRONTEND_TEST_PORT || 3100}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
