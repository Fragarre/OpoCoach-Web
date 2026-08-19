import { expect, Page, test } from "@playwright/test";

const EMAIL = process.env.OPOCOACH_E2E_EMAIL;
const PASSWORD = process.env.OPOCOACH_E2E_PASSWORD;

async function iniciarSesion(page: Page) {
  if (!EMAIL || !PASSWORD) {
    throw new Error(
      "Define OPOCOACH_E2E_EMAIL y OPOCOACH_E2E_PASSWORD antes de ejecutar las pruebas."
    );
  }

  await page.goto("/");

  const nav = page.getByRole("navigation", { name: "Navegación principal" });
  if (await nav.isVisible().catch(() => false)) return;

  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.locator("#email").fill(EMAIL);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(nav).toBeVisible({ timeout: 15_000 });
}

test.describe("OpoCoach — ciclo de vida E2E con escritura controlada", () => {
  test("crear, guardar, recuperar, calificar y eliminar un test E2E", async ({
    page,
    request,
  }) => {
    test.setTimeout(90_000);

    let testId: number | null = null;
    let numeroTest: number | null = null;
    let authorization: string | null = null;

    await iniciarSesion(page);

    try {
      const nav = page.getByRole("navigation", { name: "Navegación principal" });
      await nav.getByRole("button", { name: "Tests" }).click();
      await expect(page.getByRole("heading", { name: "Construir test" })).toBeVisible();

      const constructor = page
        .locator("section.card")
        .filter({ has: page.getByRole("heading", { name: "Construir test" }) });

      // Test mínimo: 1 pregunta, primer tema disponible y fuentes actuales.
      await constructor.locator('input[type="number"]').fill("1");

      const primerTema = constructor.locator(".selection-list .selection-item").first();
      await expect(primerTema).toBeVisible({ timeout: 15_000 });
      await primerTema.locator('input[type="checkbox"]').check();

      const respuestaCreacion = page.waitForResponse(
        (response) =>
          response.url().includes("/api/backend/api/v1/tests") &&
          response.request().method() === "POST"
      );

      await constructor.getByRole("button", { name: "Crear test" }).click();

      const creacion = await respuestaCreacion;
      expect(creacion.status()).toBe(201);

      authorization = creacion.request().headers()["authorization"] ?? null;
      const creado = await creacion.json();

      testId = Number(creado.id);
      numeroTest = Number(creado.numero);

      expect(Number.isInteger(testId) && testId > 0).toBeTruthy();
      expect(Number.isInteger(numeroTest) && numeroTest > 0).toBeTruthy();
      expect(authorization).toMatch(/^Bearer\s+\S+/);

      await expect(page.getByText(new RegExp(`^Test nº ${numeroTest} creado con`))).toBeVisible({
        timeout: 15_000,
      });
      await expect(page.getByRole("button", { name: "Calificar test" }).first()).toBeVisible();

      // Evita que la respuesta requiera además seleccionar nivel de seguridad.
      const evaluarSeguridad = page.getByLabel("Evaluar seguridad en las respuestas");
      if (await evaluarSeguridad.isChecked()) {
        await evaluarSeguridad.uncheck();
      }

      // Contesta A en la primera y única pregunta.
      const pregunta = page.locator("article.question").first();
      await expect(pregunta).toBeVisible();
      await pregunta.locator('input[type="radio"]').first().check();

      // Guarda.
      await page.getByRole("button", { name: "Guardar respuestas" }).first().click();
      await expect(page.getByText("Respuestas guardadas correctamente.", { exact: true })).toBeVisible({
        timeout: 15_000,
      });

      // Sale y comprueba que el test aparece pendiente.
      await page.getByRole("button", { name: "Volver a mis tests" }).first().click();
      await expect(page.getByRole("heading", { name: "Mis tests" })).toBeVisible();

      const fila = page
        .locator(".saved-list .saved-row")
        .filter({ hasText: `Nº ${numeroTest} ·` })
        .first();

      await expect(fila).toBeVisible();
      await expect(fila.getByText("Pendiente", { exact: true })).toBeVisible();

      // Recupera y verifica que la respuesta A continúa marcada.
      await fila.getByRole("button", { name: "Continuar" }).click();
      const preguntaRecuperada = page.locator("article.question").first();
      await expect(preguntaRecuperada.locator('input[type="radio"]').first()).toBeChecked();

      // Califica.
      await page.getByRole("button", { name: "Calificar test" }).first().click();

      await expect(
        page.getByRole("heading", { name: "Resultado", exact: true })
      ).toBeVisible({ timeout: 20_000 });
      await expect(page.getByRole("heading", { name: "Corrección" })).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Volver a mis tests" }).first()
      ).toBeVisible();

      // Vuelve al listado y comprueba el estado finalizado.
      await page.getByRole("button", { name: "Volver a mis tests" }).first().click();
      await expect(page.getByRole("heading", { name: "Mis tests" })).toBeVisible();

      const filaFinal = page
        .locator(".saved-list .saved-row")
        .filter({ hasText: `Nº ${numeroTest} ·` })
        .first();

      await expect(filaFinal.getByText("Corregido", { exact: true })).toBeVisible();
      await expect(filaFinal.getByRole("button", { name: "Ver corrección" })).toBeVisible();
    } finally {
      // Limpieza estricta: únicamente el ID creado por ESTA ejecución.
      if (testId !== null && authorization) {
        const borrado = await request.delete(
          `http://localhost:3000/api/backend/api/v1/simulacros/${testId}`,
          { headers: { Authorization: authorization } }
        );

        expect(
          borrado.status(),
          `No se pudo eliminar el test E2E ${testId}. Respuesta: ${await borrado.text()}`
        ).toBe(204);
      }
    }
  });
});
