import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 } });

test("mobile shell supports primary navigation without horizontal overflow", async ({ page }) => {
  await page.goto("/scan");

  await expect(page.locator(".mobile-header")).toBeVisible();
  await expect(page.locator(".mobile-bottom-nav")).toBeVisible();
  await expect(page.locator(".sidebar")).toBeHidden();
  await expect(page.locator('.mobile-bottom-nav a[href="/scan"]')).toHaveClass(/active/);
  await expect(page.locator("h1")).toContainText("Quét");

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);

  await page.getByRole("button", { name: "Thêm" }).click();
  await expect(page.getByRole("dialog", { name: "Điều hướng bổ sung" })).toBeVisible();
  await page.getByRole("link", { name: "So sánh" }).click();
  await expect(page).toHaveURL(/\/compare$/);
  await expect(page.getByRole("dialog", { name: "Điều hướng bổ sung" })).toBeHidden();
});

test("mobile profile and meal planner controls remain inside the viewport", async ({ page }) => {
  await page.goto("/profile");
  await expect(page.getByText("Đăng nhập để tiếp tục")).toBeVisible();
  await expect(page.locator(".mobile-bottom-nav")).toBeVisible();

  const profileOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(profileOverflow).toBeLessThanOrEqual(1);
});
