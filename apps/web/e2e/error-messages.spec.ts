import { expect, test } from "@playwright/test";

test("invalid login shows a safe localized message instead of a raw API error", async ({ page }) => {
  await page.goto("/auth");
  await page.getByLabel("Email").fill("unknown@example.com");
  await page.getByLabel("Mật khẩu").fill("wrong-password");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).last().click();

  const alert = page.locator('p.error[role="alert"]');
  await expect(alert).toHaveText("Email hoặc mật khẩu không đúng.");
  await expect(alert).not.toContainText("detail");
  await expect(alert).not.toContainText("Traceback");
  await expect(alert).not.toContainText("Internal Server Error");
});

test("validation errors are converted into field-level messages", async ({ page }) => {
  await page.goto("/auth");
  await page.getByRole("button", { name: "Tạo tài khoản", exact: true }).click();
  await page.getByLabel("Tên hiển thị").fill("A");
  await page.getByLabel("Email").fill("valid@example.com");
  await page.getByLabel("Mật khẩu").fill("strong-password");
  await page.getByRole("button", { name: "Tạo tài khoản", exact: true }).last().click();

  await expect(page.locator('p.error[role="alert"]')).toContainText("tên hiển thị chưa đủ độ dài yêu cầu");
});
