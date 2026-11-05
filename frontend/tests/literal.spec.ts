import { test, expect } from "./fixtures";
import { join } from "node:path";

test("comparación literal real con fuentes explícitas y cobertura web honesta", async ({
  page,
}) => {
  const fixtures = process.env.E2E_FIXTURES_DIR;
  if (!fixtures) throw new Error("Faltan documentos sintéticos de prueba");
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill("admin@example.org");
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill("Test-only-password-2026!");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.getByRole("button", { name: /Universidad A/ }).click();
  await expect(
    page.getByRole("heading", { name: "Un punto de partida confiable." }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Documentos/ }).click();
  await page
    .getByLabel("Seleccionar o arrastrar documentos")
    .setInputFiles(
      [
        "literal-principal.txt",
        "literal-fuente.txt",
        "literal-distinto.txt",
      ].map((f) => join(fixtures, f)),
    );
  await page.getByRole("button", { name: "Cargar documentos" }).click();
  await expect(page.getByRole("status")).toContainText(
    "3 archivo(s) recibido(s)",
  );
  await page
    .getByRole("link", { name: "literal-principal.txt", exact: true })
    .click();
  await expect(
    page.getByText("Extracción completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await page
    .getByRole("link", { name: "Comparar con fuentes autorizadas" })
    .click();
  await expect(
    page.getByLabel("Principal: literal-principal.txt", { exact: true }),
  ).toBeChecked();
  await page.getByLabel("Fuente: literal-fuente.txt", { exact: true }).check();
  await page
    .getByLabel("Fuente: literal-distinto.txt", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Iniciar comparación", exact: true })
    .click();
  await expect(page).toHaveURL(/\/auditorias\/[0-9a-f-]+$/);
  await expect(
    page.getByText("Comparación completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await expect(
    page.getByText("Una coincidencia no demuestra plagio.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Coincidencia literal normalizada", { exact: true }),
  ).toHaveCount(1);
  await expect(page.locator(".metric")).toContainText("10");
  await expect(
    page.getByText(
      "Institucionales comparadas por completo: 2 de 2 seleccionadas.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.locator("blockquote")).toHaveCount(2);
  await expect(page.locator("blockquote").first()).toHaveText(
    "La investigación académica exige evidencia verificable y revisión humana responsable",
  );
  await expect(page.locator("blockquote").last()).toHaveText(
    "La investigación académica exige evidencia verificable y revisión humana responsable",
  );
  await page
    .getByRole("link", { name: "← Comparaciones", exact: true })
    .click();
  await page
    .getByLabel("Principal: literal-principal.txt", { exact: true })
    .check();
  await page.getByLabel("Fuente: literal-fuente.txt", { exact: true }).check();
  await page.getByLabel("Solicitar búsqueda web", { exact: true }).check();
  await page
    .getByRole("button", { name: "Iniciar comparación", exact: true })
    .click();
  await expect(page).toHaveURL(/\/auditorias\/[0-9a-f-]+$/);
  await expect(
    page.getByText("Resultado parcial", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await expect(
    page.getByText("Web: no disponible", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Consultas enviadas: 0. Fuentes web verificadas: 0./),
  ).toBeVisible();
  await expect(
    page.getByText("Coincidencia literal normalizada", { exact: true }),
  ).toHaveCount(1);
  const meta = await page.request.get(
    page.url().replace("/auditorias/", "/api/v1/audits/"),
  );
  const result = await meta.json();
  expect(result.coverage.web.sources_verified).toBe(0);
  expect(result.summary.matched_words).toBe(10);
  expect(result.sources[0].sha256).toMatch(/^[a-f0-9]{64}$/);
});
