import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

const python = process.env.CI ? "python" : ".venv/bin/python";
const repoRoot = resolve(process.cwd(), "../..");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3010",
    trace: "on-first-retry"
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `env NUTRILENS_DATABASE_URL=sqlite+aiosqlite:// NUTRILENS_CORS_ORIGINS=http://127.0.0.1:3010 ${python} -m uvicorn app.main:app --app-dir apps/api --port 8010`,
      url: "http://127.0.0.1:8010/health/ready",
      reuseExistingServer: false,
      timeout: 120_000,
      cwd: repoRoot
    },
    {
      command:
        "env NEXT_DIST_DIR=.next-e2e NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010 npm --workspace apps/web run build && env NEXT_DIST_DIR=.next-e2e NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010 npm --workspace apps/web run start -- --port 3010",
      url: "http://127.0.0.1:3010",
      reuseExistingServer: false,
      timeout: 120_000,
      cwd: repoRoot
    }
  ]
});
