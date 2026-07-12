import { expect, test } from "@playwright/test";
import { resolve } from "node:path";

test("missing product can be recovered from a package label review", async ({ page }) => {
  let confirmed = false;
  await page.route("**/api/products/scan", async (route) => {
    if (!confirmed) {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Product not found." }) });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        product: { barcode: "737628064502", name: "Sữa yến mạch", brand: "Test", categories: [], allergens: ["milk"], additives: [], nutriments: { proteins_100g: 4 }, source: "package_ocr_user_confirmed" },
        score: { score: 65, label: "Khá", risk_level: "low", warnings: [], good_points: [], missing_data: [], disclaimer: "Test" },
      }),
    });
  });
  await page.route("**/api/products/label-extractions", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: "extract-1", barcode: "737628064502", status: "needs_review", raw_text: "Thành phần: yến mạch, sữa", ingredients_text: "yến mạch, sữa", allergens: ["milk"], additives: [], nutriments: { proteins_100g: 4 }, confidence: 0.88, validation_issues: [], ocr_provider: "tesseract", extractor_version: "label-rules-v1" }),
    });
  });
  await page.route("**/api/products/label-extractions/extract-1/confirm", async (route) => {
    confirmed = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ barcode: "737628064502", name: "Sữa yến mạch", categories: [], allergens: ["milk"], additives: [], nutriments: {}, source: "package_ocr_user_confirmed" }) });
  });

  await page.goto("/scan");
  await page.getByRole("button", { name: "Tra cứu" }).click();
  await expect(page.getByRole("heading", { name: "Đọc thành phần từ nhãn bao bì" })).toBeVisible();
  await page.locator('.label-recovery input[type="file"]').setInputFiles(resolve(process.cwd(), "e2e/fixtures/gs1-digital-link.png"));
  await expect(page.getByText("Độ tin cậy 88%"),).toBeVisible();
  await page.getByLabel("Tên sản phẩm *").fill("Sữa yến mạch");
  await page.getByLabel("Thương hiệu").fill("Test");
  await page.getByRole("button", { name: "Xác nhận dữ liệu sản phẩm" }).click();
  await expect(page.getByRole("heading", { name: "Sữa yến mạch" })).toBeVisible();
});
