import { expect, test } from "@playwright/test";

import { bootStudio } from "./helpers";

test("loads mission control dashboard", async ({ page }) => {
  await bootStudio(page);

  await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();
  await expect(page.getByTestId("agent-card").first()).toBeVisible();
  await expect(page.locator("#widgetToolsOnline")).toHaveText(/\d+/);
  await expect(page.getByRole("heading", { name: "Active Runs" })).toBeVisible();
  await expect.poll(async () => page.locator("#jobsBody tr").count()).toBeGreaterThan(0);

  await page.getByRole("tab", { name: "Promising Drugs" }).click();
  await expect(page.getByRole("heading", { name: "Promising Drugs" })).toBeVisible();
});
