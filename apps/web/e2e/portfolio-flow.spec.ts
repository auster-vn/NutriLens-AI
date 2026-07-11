import { expect, test } from "@playwright/test";

test("demo user completes a personalized nutrition workflow", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Open demo workspace" }).click();
  await expect(page.getByRole("heading", { name: /Welcome back/ })).toBeVisible();

  await page.getByRole("link", { name: "Profile" }).click();
  await page.getByLabel("Goal").selectOption("high_protein");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Chat" }).click();
  await page.getByLabel("Question").fill("Protein trên nhãn dinh dưỡng có ý nghĩa gì?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByRole("heading", { name: "Citations" })).toBeVisible();
  await expect(page.getByText("Protein Basics", { exact: true }).first()).toBeVisible();
});
