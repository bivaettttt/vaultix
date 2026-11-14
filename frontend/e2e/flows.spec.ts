import { expect, test, type Page } from "@playwright/test";

export async function login(page: Page, username: string) {
  await page.goto("/");
  await page.getByLabel("Логин").fill(username);
  await page
    .getByLabel("Пароль")
    .fill(process.env.DEMO_PASSWORD ?? "Vaultix-demo-local");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Выйти", exact: true }),
  ).toBeVisible();
}

test("customer posts and reads the real journal", async ({
  page,
  browser,
  baseURL,
}) => {
  const staff = await browser.newPage({ baseURL });
  await login(staff, "operator");
  const accounts = await (await staff.request.get("/api/accounts")).json();
  const recipient = accounts.find(
    (a: { name: string }) => a.name === "Расчётный счёт",
  );
  await staff.close();
  await login(page, "demo");
  await expect(
    page.getByRole("heading", { name: "Обзор счетов" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Новый перевод", exact: true })
    .last()
    .click();
  const source = accounts.find(
    (a: { name: string }) => a.name === "Основной счёт",
  );
  await page.getByLabel("Счёт списания").selectOption(source.id);
  await page.getByLabel("ID счёта получателя").fill(recipient.id);
  await page.getByLabel("Сумма, ₽").fill("37,20");
  await page.getByRole("button", { name: "Выполнить перевод" }).click();
  await expect(page.getByText("Проведено")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Дебет" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Кредит" })).toBeVisible();
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Вход в Vaultix" }),
  ).toBeVisible();
});

test("mobile operator opens authorized management views", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "operator");
  await page.getByRole("link", { name: "Операционная панель" }).click();
  await expect(
    page.getByRole("heading", { name: "Статусы счетов" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Заблокировать" }).first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "Аудит", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Журнал аудита" }),
  ).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBe(390);
});
