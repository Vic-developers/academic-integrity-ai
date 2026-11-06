import { test, expect } from "./fixtures";
import type { Page } from "./fixtures";
async function login(page: Page, user: string) {
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill(user + "@example.org");
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill("Test-only-password-2026!");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.getByRole("button", { name: /Universidad A/ }).click();
  await expect(
    page.getByRole("heading", { name: "Un punto de partida confiable." }),
  ).toBeVisible();
}
test("forense original, autorización de estilo, comparación y revocación reales", async ({
  page,
}) => {
  test.setTimeout(150000);
  await login(page, "student");
  const ids: string[] = [];
  for (let i = 0; i < 3; i++) {
    await page.goto("/documentos");
    const text =
      (i === 0 ? "🧭 pala\u200bbra aа ﬁnal. " : "") +
      Array.from({ length: 110 + i }, (_, k) => `palabra${i}tema${k}`).join(
        " ",
      ) +
      ".";
    await page.getByLabel("Seleccionar o arrastrar documentos").setInputFiles({
      name: `estilo-forense-${i}.txt`,
      mimeType: "text/plain",
      buffer: Buffer.from(text),
    });
    await page.getByRole("button", { name: "Cargar documentos" }).click();
    await expect(page.getByRole("status")).toContainText(
      "1 archivo(s) recibido(s)",
    );
    await page
      .getByRole("link", { name: `estilo-forense-${i}.txt`, exact: true })
      .click();
    await expect(
      page.getByText("Extracción completada", { exact: true }),
    ).toBeVisible({ timeout: 60000 });
    ids.push(new URL(page.url()).pathname.split("/").pop()!);
  }
  await page.getByRole("button", { name: "Salir", exact: true }).click();
  await login(page, "admin");
  for (let i = 0; i < 3; i++) {
    await page.goto("/forense/" + ids[i]);
    await expect(
      page.getByRole("heading", {
        name: `estilo-forense-${i}.txt`,
        exact: true,
      }),
    ).toBeVisible();
    if (i === 0) {
      await expect(
        page.getByText("Carácter de formato o control", { exact: true }),
      ).toBeVisible();
      await expect(page.getByText("\\u200B", { exact: true })).toBeVisible();
      const raw = await (
        await page.request.get("/api/v1/forensics/documents/" + ids[0])
      ).json();
      expect(raw.observation.authorship_probability).toBeNull();
      expect(
        raw.observation.flags.some(
          (x: { span: { text: string } }) => x.span.text === "\u200b",
        ),
      ).toBe(true);
    }
    await page
      .getByText("Autorización y procedencia para comparar estilo", {
        exact: true,
      })
      .click();
    await page
      .getByLabel("Autorización activa de uso para esta comparación")
      .check();
    if (i !== 0)
      await page
        .getByLabel("Muestra anterior de escritura verificada por el evaluador")
        .check();
    await page
      .getByLabel("Referencia de autorización")
      .fill("Autorización técnica de prueba para esta comparación");
    await page
      .getByLabel("Registro de procedencia")
      .fill("Documento de prueba verificado por el evaluador técnico");
    await page.getByLabel("Dominio comparable").fill("ensayo");
    await page.getByLabel("Género comparable").fill("prosa");
    await page
      .getByLabel("Fecha documentada de la muestra")
      .fill(i === 0 ? "2025-01-01" : "2024-01-01");
    await page
      .getByLabel("Motivo del registro")
      .fill("Registrar autorización y procedencia para una prueba técnica.");
    await page
      .getByRole("button", { name: "Guardar autorización", exact: true })
      .click();
    await expect(
      page.getByText("Revisión del borrador: 1. Actual: 1."),
    ).toBeVisible();
  }
  await page.goto("/forense/" + ids[0]);
  await expect(
    page.getByRole("heading", { name: "estilo-forense-0.txt", exact: true }),
  ).toBeVisible();
  await page
    .getByText("Comparar con muestras anteriores autorizadas", { exact: true })
    .click();
  for (let i = 1; i < 3; i++)
    await page.getByLabel(new RegExp(`estilo-forense-${i}\\.txt`)).check();
  await page
    .getByRole("button", {
      name: "Comparar estilo descriptivamente",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Comparación descriptiva, sin conclusión de autoría",
    }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const csrf = (await page.context().cookies()).find(
    (c) => c.name === "aid_csrf",
  )!.value;
  const endpoint = `/api/v1/forensics/documents/${ids[1]}/attestation`;
  const record = await (await page.request.get(endpoint)).json();
  const revoked = await page.request.post(endpoint, {
    headers: {
      Origin: "http://localhost:5173",
      "X-Requested-With": "AcademicIntegrityAI",
      "X-CSRF-Token": csrf,
    },
    data: {
      ...record.details,
      expected_revision: record.revision,
      active: false,
    },
  });
  expect(revoked.ok()).toBe(true);
  await page
    .getByRole("button", {
      name: "Comparar estilo descriptivamente",
      exact: true,
    })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Falta autorización activa",
  );
  await expect(
    page.getByRole("heading", {
      name: "Comparación descriptiva, sin conclusión de autoría",
    }),
  ).toHaveCount(0);
});
