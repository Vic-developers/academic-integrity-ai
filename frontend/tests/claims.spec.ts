import { test, expect } from "./fixtures";

test("afirmaciones locales, evidencia real y decisión humana con control de revisión", async ({
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
  const fact =
    "🧭 El estudio sintético indica que la lectura aumenta el rendimiento en 12.5 puntos.";
  const source =
    "El estudio sintético no indica que la lectura aumenta el rendimiento en 12.5 puntos.";
  for (const [name, content] of [
    ["afirmacion-e2e.txt", fact],
    ["fuente-afirmacion-e2e.txt", source],
  ]) {
    await page.goto("/documentos");
    await page.getByLabel("Seleccionar o arrastrar documentos").setInputFiles({
      name,
      mimeType: "text/plain",
      buffer: Buffer.from(content),
    });
    await page.getByRole("button", { name: "Cargar documentos" }).click();
    await expect(page.getByRole("status")).toContainText(
      "1 archivo(s) recibido(s)",
    );
    await page.getByRole("link", { name, exact: true }).click();
    await expect(
      page.getByText("Extracción completada", { exact: true }),
    ).toBeVisible({ timeout: 60000 });
  }
  await page.goto("/afirmaciones");
  await page
    .getByLabel("Principal: afirmacion-e2e.txt", { exact: true })
    .check();
  await page
    .getByLabel("Fuente: fuente-afirmacion-e2e.txt", { exact: true })
    .check();
  await page.getByRole("button", { name: "Preparar afirmaciones" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Revisión de afirmaciones",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Estado: Completado", {
    timeout: 60000,
  });
  const card = page.getByRole("article").first();
  await expect(card.getByRole("blockquote").first()).toHaveText(fact);
  await expect(
    card.getByText("Sin evaluar · Candidata heurística"),
  ).toBeVisible();
  await card.getByLabel("Clasificación").selectOption("contradicted");
  await card
    .getByLabel("Motivo")
    .fill(
      "La negación está presente, evaluación contextual sintética por una persona.",
    );
  await card.getByRole("button", { name: "Guardar evaluación humana" }).click();
  await expect(card.getByRole("alert")).toContainText(
    "requiere al menos un pasaje",
  );
  await card.getByRole("button", { name: "Adjuntar sugerencia 1" }).click();
  await card.getByRole("button", { name: "Guardar evaluación humana" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Evaluadas por personas: 1",
  );
  const exportUrl = await page
    .getByRole("link", { name: "Exportar evidencia JSON" })
    .getAttribute("href");
  const exported = await (await page.request.get(exportUrl!)).json();
  expect(exported.run.summary.automatic_assessments).toBe(0);
  expect(exported.claims[0].evidence.automatic_verdict).toBe("not_assessed");
  expect(exported.claims[0].review_log[0].passages[0].span.text).toBe(source);
  expect(exported.claims[0].review_log[0].passages[0].span.span_sha256).toMatch(
    /^[a-f0-9]{64}$/,
  );
  // A second reviewer changes the revision while the first keeps an unsaved draft.
  await card
    .getByLabel("Motivo")
    .fill("Este borrador debe conservarse cuando aparece un conflicto.");
  const review = exported.claims[0];
  const csrf = (await page.context().cookies()).find(
    (c) => c.name === "aid_csrf",
  )!.value;
  const apiPath = exportUrl!.replace("/export", `/items/${review.id}/review`);
  const concurrent = await page.request.post(apiPath, {
    headers: {
      Origin: "http://localhost:5173",
      "X-Requested-With": "AcademicIntegrityAI",
      "X-CSRF-Token": csrf,
    },
    data: {
      expected_revision: 1,
      state: "not_verifiable",
      reason: "Otra revisión humana de prueba con incertidumbre.",
    },
  });
  expect(concurrent.ok()).toBe(true);
  await card.getByRole("button", { name: "Guardar evaluación humana" }).click();
  await expect(card.getByRole("alert")).toContainText("Otra revisión modificó");
  await expect(card.getByLabel("Motivo")).toHaveValue(
    "Este borrador debe conservarse cuando aparece un conflicto.",
  );
  await page.reload();
  await expect(
    page
      .getByRole("article")
      .first()
      .getByText("No verificable · Candidata heurística"),
  ).toBeVisible();
  await page.getByText("Añadir afirmación omitida", { exact: true }).click();
  const picker = page.locator("details").filter({
    has: page.locator("summary", { hasText: "Añadir afirmación omitida" }),
  });
  await picker.getByLabel("Fragmento original").selectOption({ index: 1 });
  await picker.getByLabel("Fin", { exact: true }).fill("10");
  await picker.getByRole("button", { name: "Usar este pasaje" }).click();
  await expect(
    page.getByRole("heading", { name: "Afirmación 2", exact: true }),
  ).toBeVisible();
  const manual = await (await page.request.get(exportUrl!)).json();
  expect(manual.claims[1].evidence.span.text).toBe(
    Array.from(fact).slice(0, 10).join(""),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
