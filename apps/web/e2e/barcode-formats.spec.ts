import { expect, test } from "@playwright/test";
import { resolve } from "node:path";

test("scanner decodes a GS1 Digital Link QR image and sends its symbology", async ({ page }) => {
  let scanPayload: Record<string, unknown> | null = null;
  await page.route("**/api/products/scan", async (route) => {
    scanPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        product: {
          barcode: "09506000134352",
          name: "GS1 Test Product",
          brand: "NutriLens Test",
          categories: [],
          allergens: [],
          additives: [],
          nutriments: {},
          source: "open_food_facts",
          completeness_score: 25,
        },
        score: {
          score: 50,
          label: "Cần thêm dữ liệu",
          risk_level: "medium",
          warnings: [],
          good_points: [],
          missing_data: ["nutriments"],
          disclaimer: "Test response",
        },
      }),
    });
  });

  await page.goto("/scan");
  await page.locator('input[type="file"]').setInputFiles(
    resolve(process.cwd(), "e2e/fixtures/gs1-digital-link.png"),
  );

  await expect(page.getByText("Đã nhận diện: QR-CODE")).toBeVisible();
  await expect(page.getByRole("heading", { name: "GS1 Test Product" })).toBeVisible();
  expect(scanPayload).toMatchObject({
    barcode: "https://id.gs1.org/01/09506000134352/10/ABC123",
    barcode_format: "QR_CODE",
  });
});
