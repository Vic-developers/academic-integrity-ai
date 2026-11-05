import { test, expect } from "@playwright/test";
// Dedicated aid_test database; these are synthetic test credentials, never provisioned in development.
const password = "Test-only-password-2026!";
test("acceso real, selección institucional, gestión de usuarios, tema y cierre", async ({
  page,
}) => {
  const exceptions: string[] = [];
  page.on("pageerror", (e) => exceptions.push(e.message));
  await page.goto("/login");
  await expect(
    page.getByRole("heading", { name: "Bienvenido de nuevo" }),
  ).toBeVisible();
  await page.getByLabel("Correo electrónico").fill("admin@example.org");
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(
    page.getByRole("heading", { name: "Selecciona tu institución" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /Universidad B/ })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: /Universidad A/ }).click();
  await expect(
    page.getByRole("heading", { name: "Un punto de partida confiable." }),
  ).toBeVisible();
  await expect(page.getByText("Comparación literal disponible")).toBeVisible();
  await page.getByRole("link", { name: /Usuarios/ }).click();
  await expect(
    page.getByRole("cell", { name: "outsider@example.org" }),
  ).toHaveCount(0);
  await page
    .getByLabel("Nombre", { exact: true })
    .fill("Docente de prueba E2E");
  await page.getByLabel("Correo", { exact: true }).fill("e2e@example.org");
  await page.getByLabel("Contraseña inicial").fill(password);
  await page.getByRole("button", { name: "Crear usuario" }).click();
  await expect(
    page.getByRole("cell", { name: "e2e@example.org" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Modo oscuro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Salir", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Bienvenido de nuevo" }),
  ).toBeVisible();
  expect(exceptions).toEqual([]);
});

test("recuperación con cola Celery y SMTP reales, token de uso único", async ({
  page,
  request,
}) => {
  const before = await request.get(
    `${process.env.MAILPIT_URL ?? "http://localhost:8025"}/api/v1/messages`,
  );
  const oldIds = new Set(
    ((await before.json()).messages as { ID: string }[]).map((m) => m.ID),
  );
  await page.goto("/recuperar");
  await page.getByLabel("Correo electrónico").fill("teacher@example.org");
  await page.getByRole("button", { name: "Enviar instrucciones" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Si la cuenta está activa",
  );
  let messageId = "";
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `${process.env.MAILPIT_URL ?? "http://localhost:8025"}/api/v1/messages`,
        );
        const messages = (await response.json()).messages as {
          ID: string;
          To: { Address: string }[];
        }[];
        const mail = messages.find(
          (m) =>
            !oldIds.has(m.ID) &&
            m.To.some((t) => t.Address === "teacher@example.org"),
        );
        messageId = mail?.ID ?? "";
        return Boolean(messageId);
      },
      { timeout: 30000 },
    )
    .toBeTruthy();
  const response = await request.get(
    `${process.env.MAILPIT_URL ?? "http://localhost:8025"}/api/v1/message/${messageId}`,
  );
  const body = await response.json();
  const token = /token=([A-Za-z0-9_-]+)/.exec(body.Text)?.[1];
  expect(token).toBeTruthy();
  await page.goto(`/restablecer#token=${token}`);
  await page
    .getByLabel("Nueva contraseña")
    .fill("New-teacher-test-password-2026!");
  await page.getByRole("button", { name: "Actualizar contraseña" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Contraseña actualizada",
  );
  expect(page.url()).not.toContain("token=");
  await page.getByRole("link", { name: "Volver al inicio de sesión" }).click();
  await page.getByLabel("Correo electrónico").fill("teacher@example.org");
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill("New-teacher-test-password-2026!");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.getByRole("button", { name: /Universidad A/ }).click();
  await expect(
    page.getByRole("heading", { name: "Un punto de partida confiable." }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /Usuarios/ })).toHaveCount(0);
  await page.goto("/usuarios");
  await expect(page.getByRole("alert")).toContainText("No tienes permiso");
});
