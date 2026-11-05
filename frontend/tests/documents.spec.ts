import { test, expect } from "@playwright/test";
import { join } from "node:path";
import { readFile } from "node:fs/promises";

test("lote real PDF DOCX TXT, visualizador, normalización y OCR no disponible", async ({
  page,
}) => {
  const fixtures = process.env.E2E_FIXTURES_DIR;
  if (!fixtures)
    throw new Error(
      "Ejecuta scripts/run_e2e.py para generar documentos reales de prueba",
    );
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
      ["evidencia.txt", "evidencia.pdf", "evidencia.docx", "escaneado.pdf"].map(
        (f) => join(fixtures, f),
      ),
    );
  await page.getByRole("button", { name: "Cargar documentos" }).click();
  await expect(page.getByRole("status")).toContainText(
    "4 archivo(s) recibido(s)",
  );
  await page.getByRole("link", { name: "evidencia.pdf", exact: true }).click();
  await expect(page).toHaveURL(/\/documentos\/[0-9a-f-]+$/);
  await expect(
    page.getByRole("heading", { name: "evidencia.pdf", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Extracción completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("Página 1 de 2", { exact: true })).toBeVisible();
  await expect
    .poll(() =>
      page.locator("canvas").evaluate((canvas) => {
        const element = canvas as HTMLCanvasElement;
        const data = element
          .getContext("2d")
          ?.getImageData(0, 0, element.width, element.height).data;
        if (!data) return false;
        for (let n = 0; n < data.length; n += 4)
          if (data[n] < 150 && data[n + 3] > 0) return true;
        return false;
      }),
    )
    .toBeTruthy();
  await page.getByRole("button", { name: "Página siguiente" }).click();
  await expect(page.getByText("Página 2 de 2", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Evidence on page 2. Academic document.", { exact: true }),
  ).toBeVisible();
  const before = await page
    .locator("canvas")
    .evaluate((c) => (c as HTMLCanvasElement).width);
  await page.getByLabel("Zoom").selectOption("1.5");
  await expect
    .poll(() =>
      page.locator("canvas").evaluate((c) => (c as HTMLCanvasElement).width),
    )
    .toBeGreaterThan(before);
  const pdfUrl = await page
    .getByRole("link", { name: "Descargar original" })
    .getAttribute("href");
  const response = await page.request.get(pdfUrl!);
  expect(
    (await response.body()).equals(
      await readFile(join(fixtures, "evidencia.pdf")),
    ),
  ).toBeTruthy();
  await page.getByRole("link", { name: "← Documentos", exact: true }).click();
  await page.getByRole("link", { name: "evidencia.docx", exact: true }).click();
  await expect(page).toHaveURL(/\/documentos\/[0-9a-f-]+$/);
  await expect(
    page.getByRole("heading", { name: "evidencia.docx", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Extracción completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await expect(
    page.getByText("Contenido de tabla", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Encabezado autorizado", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "← Documentos", exact: true }).click();
  await page.getByRole("link", { name: "escaneado.pdf", exact: true }).click();
  await expect(page).toHaveURL(/\/documentos\/[0-9a-f-]+$/);
  await expect(
    page.getByRole("heading", { name: "escaneado.pdf", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Extracción parcial", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await expect(
    page.getByText("Página 1 sin texto extraíble. OCR no disponible.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "← Documentos", exact: true }).click();
  await page.getByRole("link", { name: "evidencia.txt", exact: true }).click();
  await expect(page).toHaveURL(/\/documentos\/[0-9a-f-]+$/);
  await expect(
    page.getByRole("heading", { name: "evidencia.txt", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Extracción completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await page.getByLabel("Ver normalizado").check();
  await expect(
    page.getByText("árbol, ss y fi. evidencia documental verificable.", {
      exact: true,
    }),
  ).toBeVisible();
  page.once("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: "Eliminar documento" }).click();
  await expect(
    page.getByRole("heading", { name: "Documentos", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "evidencia.txt", exact: true }),
  ).toHaveCount(0);
});

test("asignatura, matrícula y entrega autorizada de estudiante", async ({
  page,
}) => {
  const fixtures = process.env.E2E_FIXTURES_DIR;
  if (!fixtures) throw new Error("Faltan fixtures de prueba");
  async function login(email: string) {
    await page.goto("/login");
    await page.getByLabel("Correo electrónico").fill(email);
    await page
      .getByLabel("Contraseña", { exact: true })
      .fill("Test-only-password-2026!");
    await page.getByRole("button", { name: "Iniciar sesión" }).click();
    await page.getByRole("button", { name: /Universidad A/ }).click();
    await expect(
      page.getByRole("heading", { name: "Un punto de partida confiable." }),
    ).toBeVisible();
  }
  await login("admin@example.org");
  await page.getByRole("link", { name: /Asignaturas/ }).click();
  await page
    .getByLabel("Nombre de la asignatura")
    .fill("Métodos científicos E2E");
  await page.getByRole("button", { name: "Crear asignatura" }).click();
  await expect(page.getByRole("status")).toContainText("Cambios guardados");
  await page
    .getByLabel("Asignatura seleccionada")
    .selectOption({ label: "Métodos científicos E2E" });
  await page.getByLabel("Nueva actividad").fill("Ensayo argumentado");
  await page.getByRole("button", { name: "Crear actividad" }).click();
  await expect(
    page.getByText("Ensayo argumentado", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Matricular a Student", exact: true })
    .click();
  await expect(page.getByText("Matriculado", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: /Documentos/ }).click();
  await page
    .getByLabel("Seleccionar o arrastrar documentos")
    .setInputFiles(join(fixtures, "evidencia.txt"));
  await page
    .getByLabel("Actividad opcional")
    .selectOption({ label: "Métodos científicos E2E · Ensayo argumentado" });
  await page.getByLabel("Entrega de").selectOption({ label: "Student" });
  await page.getByRole("button", { name: "Cargar documentos" }).click();
  await expect(page.getByRole("status")).toContainText(
    "1 archivo(s) recibido(s)",
  );
  await page.getByRole("button", { name: "Salir", exact: true }).click();
  await login("student@example.org");
  await page.getByRole("link", { name: /Documentos/ }).click();
  await expect(
    page.getByRole("link", { name: "evidencia.txt", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "evidencia.pdf", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "evidencia.txt", exact: true }).click();
  await expect(page).toHaveURL(/\/documentos\/[0-9a-f-]+$/);
  await expect(
    page.getByRole("heading", { name: "evidencia.txt", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Extracción completada", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
});
