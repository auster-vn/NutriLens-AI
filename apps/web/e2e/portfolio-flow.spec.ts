import { expect, test } from "@playwright/test";

test("demo user completes a personalized nutrition workflow", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Mở demo workspace" }).click();
  await expect(page.getByRole("heading", { name: /Chào lại/ })).toBeVisible();

  await page.getByRole("link", { name: "Hồ sơ" }).click();
  await page.getByLabel("Mục tiêu dinh dưỡng").selectOption("high_protein");
  await page.getByRole("button", { name: "Lưu vào hồ sơ" }).click();
  await expect(page.getByText("Đã lưu hồ sơ", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Chat AI" }).click();
  await page.getByLabel("Câu hỏi của bạn").fill("Protein trên nhãn dinh dưỡng có ý nghĩa gì?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(page.getByRole("heading", { name: "Nguồn trích dẫn" })).toBeVisible();
  await expect(page.getByText("Protein Basics", { exact: true }).first()).toBeVisible();
});
