import { expect, test } from "@playwright/test";

test("admin OCR dashboard exposes evaluation and model readiness", async ({ page }) => {
  await page.route("**/api/admin/label-ocr/dashboard", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        latest_evaluation: {
          metrics: {
            field_f1: 0.91,
            numeric_accuracy: 0.96,
            allergen_recall: 1,
            provider_cer: { tesseract: 0.08, paddleocr: 0.04 },
          },
          readiness: {
            layoutlm_or_ner_ready: false,
            labeled_case_count: 42,
            required_case_count: 200,
          },
          case_results: [],
        },
        production: {
          extraction_count: 18,
          confirmed_count: 12,
          mean_confidence: 0.87,
          provider_successes: { tesseract: 18, paddleocr: 14 },
        },
      }),
    });
  });

  await page.goto("/admin");
  await page.getByRole("button", { name: "OCR Evaluation" }).click();

  await expect(page.getByText("18", { exact: true })).toBeVisible();
  await expect(page.getByText("91%", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Collect more labeled data" })).toBeVisible();
  await expect(page.getByText(/paddleocr/).first()).toBeVisible();
});
