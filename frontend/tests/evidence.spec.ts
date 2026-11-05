import { test, expect, type Page } from "@playwright/test";
import { join } from "node:path";
async function login(page: Page) {
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
}
async function compare(page: Page, names: string[]) {
  const fixtures = process.env.E2E_FIXTURES_DIR;
  if (!fixtures) throw new Error("Faltan fixtures reales");
  await page.getByRole("link", { name: /Documentos/ }).click();
  await page
    .getByLabel("Seleccionar o arrastrar documentos")
    .setInputFiles(names.map((f) => join(fixtures, f)));
  await page.getByRole("button", { name: "Cargar documentos" }).click();
  await expect(page.getByRole("status")).toContainText(
    `${names.length} archivo(s) recibido(s)`,
  );
  const docs = await (
    await page.request.get("/api/v1/documents?limit=100")
  ).json();
  const chosen = names.map((name) =>
    docs.items.find((d: { name: string }) => d.name === name),
  );
  await expect
    .poll(
      async () => {
        const states = await Promise.all(
          chosen.map(
            async (d: { id: string }) =>
              (
                await (
                  await page.request.get(`/api/v1/documents/${d.id}`)
                ).json()
              ).state,
          ),
        );
        return states.every((s) => s === "completed" || s === "partial");
      },
      { timeout: 60000 },
    )
    .toBe(true);
  const csrf = (await page.context().cookies()).find(
    (c) => c.name === "aid_csrf",
  )!.value;
  const response = await page.request.post("/api/v1/audits", {
    data: {
      document_id: chosen[0].id,
      source_document_ids: chosen.slice(1).map((d) => d.id),
    },
    headers: {
      "X-CSRF-Token": csrf,
      "X-Requested-With": "AcademicIntegrityAI",
      Origin: "http://localhost:5173",
    },
  });
  expect(response.status()).toBe(202);
  const audit = await response.json();
  await expect
    .poll(
      async () =>
        (await (await page.request.get(`/api/v1/audits/${audit.id}`)).json())
          .state,
      { timeout: 60000 },
    )
    .toMatch(/completed|partial/);
  const findings = await (
    await page.request.get(`/api/v1/audits/${audit.id}/findings?limit=100`)
  ).json();
  expect(findings.items.length).toBeGreaterThan(0);
  await page.goto(
    `/auditorias/${audit.id}/evidencias?finding=${findings.items[0].id}`,
  );
  return { audit, findings: findings.items };
}

test("rangos Unicode originales, solapamientos, DOCX, filtros y revisión humana persistida", async ({
  page,
}) => {
  test.setTimeout(90000);
  await login(page);
  const { audit, findings } = await compare(page, [
    "visor-unicode.txt",
    "visor-unicode-fuente.txt",
    "visor-unicode.docx",
  ]);
  const main = page.getByRole("region", {
    name: "Documento principal con resaltado",
    exact: true,
  });
  await expect(main.locator("mark").first()).toHaveText(
    "Árbol ß ﬁ uno dos tres cuatro cinco seis siete ocho",
  );
  await expect(main.locator(".original-context")).toHaveText(
    "🧭 Preámbulo propio. Árbol ß ﬁ uno dos tres cuatro cinco seis siete ocho",
  );
  expect(
    (await main
      .locator("mark")
      .first()
      .getAttribute("data-finding-ids"))!.split(","),
  ).toHaveLength(2);
  await main.getByRole("button", { name: "Fragmento siguiente" }).click();
  await expect(main.locator("mark").first()).toHaveText(
    "Nueve diez once doce trece catorce quince dieciséis",
  );
  await expect(main.getByText(/Fragmento 2 de 2/)).toBeVisible();
  await page.getByRole("button", { name: "Coincidencia siguiente" }).click();
  await expect(
    main.getByText("Fragmento 1 de 2", { exact: true }),
  ).toBeVisible();
  const docxFinding = findings.find(
    (f: { source_id: string }) => f.source_id !== findings[0].source_id,
  );
  expect(docxFinding).toBeTruthy();
  await page.getByRole("button", { name: /Marcar coincidencia/ }).click();
  await page.getByLabel("Filtrar revisión").selectOption("bookmarked");
  await expect(
    page.getByText("1 de 1 coincidencias", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Estado de revisión", exact: true })
    .selectOption("justified");
  await page.getByLabel("Valoración de la citación").selectOption("correct");
  await page
    .getByLabel("Motivo de la revisión")
    .fill("Cita revisada manualmente con contexto suficiente.");
  await page.getByRole("button", { name: "Guardar revisión humana" }).click();
  await expect(main.locator("mark.justified")).toHaveCount(1);
  await expect(page.getByText("Estado humano:")).toContainText("Justificado");
  await page.reload();
  await expect(page.getByText("Estado humano:")).toContainText("Justificado");
  await page.getByText("Historial de revisión (1)", { exact: true }).click();
  await expect(
    page.getByText("Cita revisada manualmente con contexto suficiente.", {
      exact: true,
    }),
  ).toBeVisible();
  // A second tab commits while this form still edits revision 1.
  const selectedId = new URL(page.url()).searchParams.get("finding")!;
  const csrf = (await page.context().cookies()).find(
    (c) => c.name === "aid_csrf",
  )!.value;
  const otherReview = await page.request.post(
    `/api/v1/audits/${audit.id}/findings/${selectedId}/review`,
    {
      headers: {
        "X-CSRF-Token": csrf,
        "X-Requested-With": "AcademicIntegrityAI",
        Origin: "http://localhost:5173",
      },
      data: {
        expected_revision: 1,
        state: "reviewed",
        citation: "incomplete",
        reason: "Revisión desde otra pestaña para comprobar el conflicto.",
      },
    },
  );
  expect(otherReview.status()).toBe(200);
  const draft = "Mi borrador debe conservarse ante un cambio concurrente.";
  await page.getByLabel("Motivo de la revisión").fill(draft);
  await page.getByRole("button", { name: "Guardar revisión humana" }).click();
  await expect(
    page.getByText(/Otra revisión modificó el hallazgo/),
  ).toBeVisible();
  await expect(page.getByLabel("Motivo de la revisión")).toHaveValue(draft);
  await page.getByRole("button", { name: "Cargar revisión actual" }).click();
  await expect(page.getByLabel("Motivo de la revisión")).toHaveValue(draft);
  const meta = await (
    await page.request.get(`/api/v1/audits/${audit.id}`)
  ).json();
  const docxSource = meta.sources.find(
    (s: { name: string }) => s.name === "visor-unicode.docx",
  );
  await page.getByLabel("Filtrar fuente").selectOption(docxSource.id);
  await expect(page.getByText(/Vista estructurada del DOCX/)).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(main.locator("mark").first()).toBeVisible();
});

test("PDF real: cajas sobre glifos, zoom y recuperación de resaltado entre páginas", async ({
  page,
}) => {
  test.setTimeout(90000);
  await login(page);
  await compare(page, ["visor.pdf", "visor-pdf-fuente.txt"]);
  const main = page.getByRole("region", {
    name: "Documento principal con resaltado",
    exact: true,
  });
  await expect(main.locator(".pdf-highlights rect").first()).toBeVisible();
  const originalBox = await main
    .locator(".pdf-highlights rect")
    .first()
    .boundingBox();
  const originalCanvas = await main.locator("canvas").boundingBox();
  expect(originalBox!.x - originalCanvas!.x).toBeGreaterThan(40);
  // At least one dark rendered pixel must be inside each of most highlighted glyph boxes.
  const ratio = await main.evaluate((el) => {
    const canvas = el.querySelector("canvas")!;
    const cb = canvas.getBoundingClientRect();
    const context = canvas.getContext("2d")!;
    const rects = Array.from(el.querySelectorAll(".pdf-highlights rect"));
    return (
      rects.filter((rect) => {
        const b = rect.getBoundingClientRect();
        const x = Math.max(
          0,
          Math.floor(((b.x - cb.x) * canvas.width) / cb.width),
        );
        const y = Math.max(
          0,
          Math.floor(((b.y - cb.y) * canvas.height) / cb.height),
        );
        const width = Math.max(
          1,
          Math.ceil((b.width * canvas.width) / cb.width),
        );
        const height = Math.max(
          1,
          Math.ceil((b.height * canvas.height) / cb.height),
        );
        const data = context.getImageData(x, y, width, height).data;
        for (let i = 0; i < data.length; i += 4)
          if (data[i] < 150 && data[i + 3] > 0) return true;
        return false;
      }).length / rects.length
    );
  });
  expect(ratio).toBeGreaterThan(0.85);
  await main
    .getByRole("combobox", { name: "Zoom", exact: true })
    .selectOption("1.5");
  await expect
    .poll(async () => (await main.locator("canvas").boundingBox())!.width)
    .toBeGreaterThan(originalCanvas!.width);
  const zoomBox = await main
    .locator(".pdf-highlights rect")
    .first()
    .boundingBox();
  expect(zoomBox!.width / originalBox!.width).toBeCloseTo(1.5, 1);
  await main
    .getByRole("button", { name: "Página siguiente", exact: true })
    .click();
  await expect(main.getByText("Página 2 de 2", { exact: true })).toBeVisible();
  await expect(main.locator(".pdf-highlights rect")).toHaveCount(0);
  await main
    .getByRole("button", { name: "Volver a la página de coincidencia" })
    .click();
  await expect(main.locator(".pdf-highlights rect").first()).toBeVisible();
  await main.getByRole("button", { name: "Fragmento siguiente" }).click();
  await expect(main.getByText("Página 2 de 2", { exact: true })).toBeVisible();
  await expect(main.locator("mark").first()).toHaveText(
    "con palabras finales que permiten comparar tambien la segunda pagina",
  );
  await expect(main.locator(".pdf-highlights rect").first()).toBeVisible();
});

test("PDF rechaza geometría incoherente y mapas alterados", async ({
  page,
}) => {
  test.setTimeout(90000);
  await login(page);
  const { audit, findings } = await compare(page, [
    "visor.pdf",
    "visor-pdf-fuente.txt",
  ]);
  const main = page.getByRole("region", {
    name: "Documento principal con resaltado",
    exact: true,
  });
  await page.route(
    `**/api/v1/audits/${audit.id}/findings/${findings[0].id}/view?side=target*`,
    async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.page_geometry.rotation = 45;
      await route.fulfill({ response, json: body });
    },
  );
  await page.reload();
  await expect(
    main.getByText(/No se pudo verificar la referencia geométrica/),
  ).toBeVisible();
  await expect(main.locator(".pdf-highlights rect")).toHaveCount(0);
  await expect(main.locator("mark").first()).toBeVisible();
  await page.route(
    `**/api/v1/audits/${audit.id}/findings/${findings[0].id}/view?side=target*`,
    async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.fragment.original = "Contenido alterado en tránsito";
      await route.fulfill({ response, json: body });
    },
  );
  await page.reload();
  await expect(
    page.getByText(/No se pudo verificar el mapa de posiciones/),
  ).toBeVisible();
  await expect(
    page.getByRole("region", {
      name: "Documento principal con resaltado",
      exact: true,
    }),
  ).toHaveCount(0);
});

test("PDF con cuatro rotaciones, CropBox, origen desplazado y UserUnit alinea glifos", async ({
  page,
}) => {
  test.setTimeout(240000);
  await login(page);
  for (const rotation of [0, 90, 180, 270])
    for (const crop of [false, true]) {
      const name = `geometria-${rotation}-${crop ? "crop" : "media"}`;
      await compare(page, [`${name}.pdf`, `${name}-fuente.pdf`]);
      const main = page.getByRole("region", {
        name: "Documento principal con resaltado",
        exact: true,
      });
      await expect(
        main.locator(".pdf-highlights rect").first(),
        name,
      ).toBeVisible();
      async function inkRatio() {
        return main.evaluate((el) => {
          const canvas = el.querySelector("canvas")!;
          const bounds = canvas.getBoundingClientRect();
          const ctx = canvas.getContext("2d")!;
          const boxes = Array.from(el.querySelectorAll(".pdf-highlights rect"));
          return (
            boxes.filter((box) => {
              const b = box.getBoundingClientRect();
              const x = Math.max(
                0,
                Math.floor(((b.x - bounds.x) * canvas.width) / bounds.width),
              );
              const y = Math.max(
                0,
                Math.floor(((b.y - bounds.y) * canvas.height) / bounds.height),
              );
              const w = Math.min(
                  canvas.width - x,
                  Math.max(
                    1,
                    Math.ceil((b.width * canvas.width) / bounds.width),
                  ),
                ),
                h = Math.min(
                  canvas.height - y,
                  Math.max(
                    1,
                    Math.ceil((b.height * canvas.height) / bounds.height),
                  ),
                );
              const data = ctx.getImageData(x, y, w, h).data;
              for (let i = 0; i < data.length; i += 4)
                if (data[i] < 150 && data[i + 3] > 0) return true;
              return false;
            }).length / boxes.length
          );
        });
      }
      expect(await inkRatio(), name).toBeGreaterThan(0.85);
      await main
        .getByRole("combobox", { name: "Zoom", exact: true })
        .selectOption("1.5");
      await expect
        .poll(inkRatio, { message: `zoom ${name}` })
        .toBeGreaterThan(0.85);
    }
});
