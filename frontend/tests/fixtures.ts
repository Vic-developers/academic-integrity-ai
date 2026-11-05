import { test as base, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
export type { Page } from "@playwright/test";
export { expect };
export const test = base.extend<{ loginCounterIsolation: void }>({
  loginCounterIsolation: [
    async ({}, use) => {
      const python = process.env.E2E_TEST_PYTHON;
      const script = process.env.E2E_LOGIN_RESET_SCRIPT;
      const config = process.env.E2E_LOGIN_RESET_CONFIG;
      if (!python || !script || !config)
        throw new Error(
          "Ejecuta scripts/run_e2e.py para usar el perfil de pruebas aislado",
        );
      execFileSync(python, [script, config], { timeout: 10000, stdio: "pipe" });
      await use();
    },
    { auto: true },
  ],
});
