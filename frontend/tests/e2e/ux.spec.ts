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
  if (await nav.isVisible().catch(() => false)) {
    return;
  }

  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.locator("#email").fill(EMAIL);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(nav).toBeVisible({ timeout: 15_000 });
}

async function primeraFilaPendiente(page: Page) {
  const filas = page.locator(".saved-list .saved-row").filter({
    has: page.getByText("Pendiente", { exact: true }),
  });

  if ((await filas.count()) === 0) {
    return null;
  }

  return filas.first();
}

test.describe("OpoCoach — regresión UX de solo lectura", () => {
  test("un test pendiente mantiene terminología de Test", async ({ page }) => {
    await iniciarSesion(page);

    const nav = page.getByRole("navigation", { name: "Navegación principal" });
    await nav.getByRole("button", { name: "Tests" }).click();
    await expect(page.getByRole("heading", { name: "Mis tests" })).toBeVisible();

    const fila = await primeraFilaPendiente(page);
    if (!fila) {
      test.skip(true, "No existe ningún test pendiente.");
    }

    await fila!.getByRole("button", { name: "Continuar" }).click();

    await expect(page.getByRole("button", { name: "Calificar test" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole("button", { name: "Calificar simulacro" })
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Volver a mis tests" }).first()
    ).toBeVisible();

    await page.getByRole("button", { name: "Volver a mis tests" }).first().click();
    await expect(page.getByRole("heading", { name: "Mis tests" })).toBeVisible();
  });

  test("un simulacro pendiente mantiene terminología de Simulacro", async ({ page }) => {
    await iniciarSesion(page);

    const nav = page.getByRole("navigation", { name: "Navegación principal" });
    await nav.getByRole("button", { name: "Simulacros" }).click();
    await expect(page.getByRole("heading", { name: "Mis simulacros" })).toBeVisible();

    const fila = await primeraFilaPendiente(page);
    if (!fila) {
      test.skip(true, "No existe ningún simulacro pendiente.");
    }

    await fila!.getByRole("button", { name: "Continuar" }).click();

    await expect(
      page.getByRole("button", { name: "Calificar simulacro" })
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Calificar test" })).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Volver a mis simulacros" }).first()
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Volver a mis simulacros" })
      .first()
      .click();
    await expect(page.getByRole("heading", { name: "Mis simulacros" })).toBeVisible();
  });

  test("Plan activo abre otra pestaña y muestra feedback de carga", async ({
    page,
  }) => {
    await iniciarSesion(page);

    const plan = page.getByRole("button", {
      name: /^(Plan activo|Plan activo · baja programada|Pago pendiente)$/,
    });

    if ((await plan.count()) === 0) {
      test.skip(true, "La cuenta E2E no tiene un plan activo.");
    }

    await page.route("**/api/backend/api/v1/billing/portal", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 700));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          url: "http://localhost:3000/?portal-e2e=1",
        }),
      });
    });

    const urlOriginal = page.url();
    const popupPromise = page.waitForEvent("popup");

    await plan.click();

    const popup = await popupPromise;

    await expect(
      page.getByText("Abriendo gestión de suscripción...", { exact: true })
    ).toBeVisible();
    await expect(page.locator(".loading-spinner")).toBeVisible();
    await expect(page).toHaveURL(urlOriginal);

    await popup.waitForURL("http://localhost:3000/?portal-e2e=1", {
      timeout: 10_000,
    });

    await expect(page).toHaveURL(urlOriginal);
    await expect(
      page.getByText(
        "La gestión de suscripción se ha abierto en una nueva pestaña.",
        { exact: true }
      )
    ).toBeVisible();
    await expect(
      page.getByText("Abriendo gestión de suscripción...", { exact: true })
    ).toHaveCount(0);

    await popup.close();
  });
});
