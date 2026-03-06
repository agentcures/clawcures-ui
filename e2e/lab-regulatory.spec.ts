import { expect, test } from "@playwright/test";

import { bootStudio, expectResultOutputContains, uniqueId } from "./helpers";

test("validates wetlab protocol and builds/verifies regulatory bundle", async ({ page }) => {
  await bootStudio(page);
  await page.locator("summary").filter({ hasText: "Advanced operations" }).click();

  await page.click("#validateWetlabProtocolButton");
  await expectResultOutputContains(page, "WetLab Protocol Validation");
  await expect(page.locator("#resultOutput")).toContainText('"valid"');

  // Avoid linking build requests to a program id that does not yet exist.
  await page.locator("#asyncToggle").uncheck();
  await page.fill("#programIdInput", "");

  const bundleDir = `.playwright-data/${uniqueId("bundle")}`;
  await page.fill("#regulatoryOutputDirInput", bundleDir);

  await page.click("#buildRegulatoryBundleButton");
  await expectResultOutputContains(page, "Regulatory Bundle Build");

  await page.click("#verifyRegulatoryBundleButton");
  await expectResultOutputContains(page, "Regulatory Bundle Verify");

  await page.click("#generateHandoffButton");
  await expectResultOutputContains(page, "ClawCures Handoff");
  await expect(page.locator("#clawcuresCommandOutput")).not.toContainText(
    "Generate a handoff to populate commands."
  );
});
