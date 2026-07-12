import { expect, test } from "@playwright/test";

const slowUnauthorizedAuth = async (route: import("@playwright/test").Route) => {
  await new Promise((resolve) => setTimeout(resolve, 3000));
  await route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({ detail: { code: "AUTH_REQUIRED", message: "Authentication required." } }),
  });
};

test("public pages render without waiting for slow auth bootstrap", async ({ page }) => {
  await page.route("**/api/auth/me", slowUnauthorizedAuth);
  await page.goto("/scan");

  await expect(page.getByRole("heading", { name: "Quét hoặc nhập mã vạch" })).toBeVisible({ timeout: 1000 });
  await expect(page.locator(".workspace-skeleton")).toHaveCount(0);
});

test("protected pages show a stable skeleton while auth is loading", async ({ page }) => {
  await page.route("**/api/auth/me", slowUnauthorizedAuth);
  await page.goto("/profile");

  await expect(page.locator(".workspace-skeleton")).toBeVisible({ timeout: 1000 });
  await expect(page.locator(".workspace-skeleton")).toHaveAttribute("aria-busy", "true");
});
