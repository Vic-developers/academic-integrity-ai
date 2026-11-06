import { test, expect } from "./fixtures";

test("observaciones reales sin probabilidad de autoría ni entrenamiento documental", async ({
  page,
}) => {
  test.setTimeout(90000);
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
  await page.goto("/documentos");
  await page.getByLabel("Seleccionar o arrastrar documentos").setInputFiles({
    name: "observaciones-e2e.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("🧭 uno dos tres uno dos tres."),
  });
  await page.getByRole("button", { name: "Cargar documentos" }).click();
  await expect(page.getByRole("status")).toContainText(
    "1 archivo(s) recibido(s)",
  );
  await page
    .getByRole("link", { name: "observaciones-e2e.txt", exact: true })
    .click();
  await expect(
    page.getByText("Extracción completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  const documentId = new URL(page.url()).pathname.split("/").pop()!;
  await page.getByRole("link", { name: /Observaciones lingüísticas/ }).click();
  await expect(
    page.getByRole("heading", {
      name: "Observaciones lingüísticas",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "observaciones-e2e.txt", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "observaciones-e2e.txt", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Resultado no concluyente" }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Texto corto");
  await expect(
    page
      .getByRole("row")
      .filter({ hasText: "Repetición de secuencias de tres tokens" }),
  ).toContainText("0,25");
  const response = await page.request.get(
    `/api/v1/experimental-ai/documents/${documentId}`,
  );
  const result = await response.json();
  expect(result.observation.counts.tokens).toBe(6);
  expect(result.observation.values.mattr_50).toBe(0.5);
  expect(result.observation.authorship_probability).toBeNull();
  expect(result.observation.assessment).toBe("not_conclusive");
  expect(result.trained_on_this_document).toBe(false);
  expect(result.model).toBeNull();
  await page.getByText("Procedencia y límites", { exact: true }).click();
  await expect(
    page.getByText("SHA-256 del texto medido:", { exact: false }),
  ).toContainText(result.observation.text_sha256);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Resultado no concluyente" }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("link", { name: "Consultar original", exact: true })
    .click();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Eliminar documento", exact: true })
    .click();
  await expect(page).toHaveURL(/\/documentos$/);
  await page.goto(`/indicios-ia/${documentId}`);
  await expect(page.getByRole("alert")).toContainText(
    "Documento no disponible",
  );
  await expect(page.getByRole("table")).toHaveCount(0);
});
