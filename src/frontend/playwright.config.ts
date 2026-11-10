import { defineConfig, devices } from "@playwright/test";

/**
 * Configuracao do Playwright para testes End-to-End no SecretarIA.
 * 
 * Regras estritas:
 * - Porta web: 5173 (Frontend Vite)
 * - Proxy de API: 8000 (Backend FastAPI)
 * - Modo Headless por padrao para automacao sem interferencia
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // Sequencial para garantir isolamento de fluxo
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
