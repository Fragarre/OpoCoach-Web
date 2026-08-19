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

  // Si existe una sesión previa en el navegador de pruebas, no repetimos login.
  const nav = page.getByRole("navigation", { name: "Navegación principal" });
  if (await nav.isVisible().catch(() => false)) {
    return;
  }

  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();

  await page.locator("#email").fill(EMAIL);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(nav).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(EMAIL, { exact: true })).toBeVisible();
}

test.describe("OpoCoach — smoke funcional de solo lectura", () => {
  test("landing pública carga correctamente", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("OpoCoach", { exact: true }).first()).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Entrena como te examinan. Corrige como necesitas aprender.",
      })
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
  });

  test("login y navegación principal", async ({ page }) => {
    await iniciarSesion(page);

    const nav = page.getByRole("navigation", { name: "Navegación principal" });

    await nav.getByRole("button", { name: "Inicio" }).click();
    await expect(
      page.getByRole("heading", {
        name: "Prepárate con criterio, no sólo con más preguntas.",
      })
    ).toBeVisible();

    await nav.getByRole("button", { name: "Tests" }).click();
    await expect(page.getByRole("heading", { name: "Mis tests" })).toBeVisible();

    await nav.getByRole("button", { name: "Simulacros" }).click();
    await expect(page.getByRole("heading", { name: "Mis simulacros" })).toBeVisible();

    await nav.getByRole("button", { name: "Chat" }).click();
    await expect(page.getByRole("heading", { name: "Chat" })).toBeVisible();
  });

  test("una corrección de test permite volver a Mis tests", async ({ page }) => {
    await iniciarSesion(page);

    const nav = page.getByRole("navigation", { name: "Navegación principal" });
    await nav.getByRole("button", { name: "Tests" }).click();
    await expect(page.getByRole("heading", { name: "Mis tests" })).toBeVisible();

    const lista = page.locator(".saved-list");
    const filasCorregidas = lista.locator(".saved-row").filter({
      has: page.getByText("Corregido", { exact: true }),
    });

    if ((await filasCorregidas.count()) === 0) {
      test.skip(true, "No existe ningún test corregido para comprobar la navegación.");
    }

    const fila = filasCorregidas.first();
    await fila.getByRole("button", { name: "Ver corrección" }).click();

    await expect(page.getByRole("heading", { name: "Resultado", exact: true })).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole("button", { name: "Volver a mis tests" }).first()
    ).toBeVisible();

    await page.getByRole("button", { name: "Volver a mis tests" }).first().click();
    await expect(page.getByRole("heading", { name: "Mis tests" })).toBeVisible();
  });

  test("una corrección de simulacro permite volver a Mis simulacros", async ({ page }) => {
    await iniciarSesion(page);

    const nav = page.getByRole("navigation", { name: "Navegación principal" });
    await nav.getByRole("button", { name: "Simulacros" }).click();
    await expect(page.getByRole("heading", { name: "Mis simulacros" })).toBeVisible();

    const lista = page.locator(".saved-list");
    const filasCorregidas = lista.locator(".saved-row").filter({
      has: page.getByText("Corregido", { exact: true }),
    });

    if ((await filasCorregidas.count()) === 0) {
      test.skip(
        true,
        "No existe ningún simulacro corregido para comprobar la navegación."
      );
    }

    const fila = filasCorregidas.first();
    await fila.getByRole("button", { name: "Ver corrección" }).click();

    await expect(page.getByRole("heading", { name: "Resultado", exact: true })).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole("button", { name: "Volver a mis simulacros" }).first()
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Volver a mis simulacros" })
      .first()
      .click();
    await expect(page.getByRole("heading", { name: "Mis simulacros" })).toBeVisible();
  });
});
