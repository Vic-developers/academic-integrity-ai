import { test, expect } from "./fixtures";
import { join } from "node:path";
test("bibliografía local real, duplicados, cobertura sin proveedor y exportación", async ({
  page,
}) => {
  test.setTimeout(90000);
  const fixtures = process.env.E2E_FIXTURES_DIR;
  if (!fixtures) throw new Error("Faltan fixtures documentales");
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
    .setInputFiles(join(fixtures, "bibliografia-real-prueba.txt"));
  await page.getByRole("button", { name: "Cargar documentos" }).click();
  await expect(page.getByRole("status")).toContainText(
    "1 archivo(s) recibido(s)",
  );
  await page
    .getByRole("link", { name: "bibliografia-real-prueba.txt", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "bibliografia-real-prueba.txt",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Extracción completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await page
    .getByRole("link", { name: "Revisar bibliografía", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Verificación bibliográfica",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Autorizar consulta externa de los DOI extraídos"),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Revisar bibliografía", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Resultado bibliográfico", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Revisión completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await expect(page.locator(".bibliography-reference")).toHaveCount(3);
  await expect(
    page.getByText("Posible duplicado de la referencia 1; requiere revisión.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Referencias con metadatos recuperados: 0", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Intentos de consulta: 0", { exact: true }),
  ).toBeVisible();
  const href = await page
    .getByRole("link", { name: "Exportar evidencia bibliográfica JSON" })
    .getAttribute("href");
  const exported = await (await page.request.get(href!)).json();
  expect(exported.summary.references).toBe(3);
  expect(exported.summary.duplicate_candidates).toBe(1);
  expect(exported.summary.unmatched_citation_candidates).toBe(1);
  expect(exported.summary.metadata_retrieved_references).toBe(0);
  expect(exported.result.references[0].spans[0].span_sha256).toMatch(
    /^[a-f0-9]{64}$/,
  );
  expect(
    exported.result.references.every(
      (r: { verification_state: string }) =>
        r.verification_state === "not_requested",
    ),
  ).toBe(true);
  await page.reload();
  await expect(page.locator(".bibliography-reference")).toHaveCount(3);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
