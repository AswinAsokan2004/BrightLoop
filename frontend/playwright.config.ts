import { defineConfig } from "@playwright/test"
import { existsSync } from "node:fs"
import { fileURLToPath } from "node:url"

const candidates = [
  process.env.BRIGHTLOOP_TEST_PYTHON,
  fileURLToPath(new URL("../.venv/bin/python", import.meta.url)),
  fileURLToPath(new URL("../../analysis-venv/bin/python", import.meta.url)),
].filter((candidate): candidate is string => !!candidate)
const python = candidates.find(candidate => existsSync(candidate)) || "python3"
const shellQuote = (value: string) => "'" + value.replaceAll("'", "'\\''") + "'"

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5174",
    headless: true,
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : {},
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `cd .. && ${shellQuote(python)} -m tests.browser_api`,
      url: "http://127.0.0.1:8100/__test__/health",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      env: { API_PROXY_TARGET: "http://127.0.0.1:8100" },
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
    },
  ],
})
