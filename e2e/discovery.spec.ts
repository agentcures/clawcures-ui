import { expect, test } from "@playwright/test";

import { bootStudio, seedPromisingDrugJob } from "./helpers";

test("renders promising drug report cards and supports score filtering", async ({ page }) => {
  seedPromisingDrugJob();
  await bootStudio(page);

  await page.getByRole("tab", { name: "Promising Drugs" }).click();

  await expect.poll(async () => page.getByTestId("drug-report-card").count()).toBe(2);
  await expect(page.getByTestId("drug-report-grade").first()).toBeVisible();
  await expect(page.locator("#cureDetailHeader")).toContainText("KRAS Prime");
  await expect(page.locator("#cureReportCard")).toContainText("Report Card");
  await expect(page.locator("#cureReportCard")).toContainText("Strengths");
  await expect(page.locator("#cureReportCard")).toContainText("Risks To Watch");
  await expect(page.locator("#cureReportCard")).toContainText("Binding");
  await expect(page.locator("#cureReportCard")).toContainText("ADMET");
  await expect(page.locator("#candidateClinicalContext")).toContainText("Suggested trial ID");

  await page.locator("#drugPortfolioCards [data-testid='drug-report-card']").nth(1).click();
  await expect(page.locator("#cureDetailHeader")).toContainText("EGFR Shield");
  await expect(page.locator("#candidateClinicalContext")).toContainText("EGFR Shield");
  await expect(page.locator("#drugPortfolioDetail")).toContainText(
    '"candidate_id": "refua_affinity:egfr-shield"'
  );

  await page.fill("#drugMinScoreInput", "90");
  await page.click("#refreshDrugPortfolioButton");
  await expect.poll(async () => page.getByTestId("drug-report-card").count()).toBe(1);
  await expect(page.locator("#drugPortfolioCards")).toContainText("KRAS Prime");
  await expect(page.locator("#drugPortfolioCards")).not.toContainText("EGFR Shield");
});
