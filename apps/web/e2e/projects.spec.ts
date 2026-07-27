import { expect, test } from "@playwright/test";

test("researcher creates a project, experiment, and real classification run", async ({
  page,
}) => {
  const suffix = Date.now().toString(36);
  const projectName = `E2E project ${suffix}`;

  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

  await page.getByRole("link", { name: "Projects" }).click();
  await page.getByRole("button", { name: "New project" }).click();
  await page.getByLabel("Project name").fill(projectName);
  await page.getByLabel("Description").fill("Playwright-managed project");
  await page.getByRole("button", { name: "Create project" }).click();
  await page.getByRole("link", { name: projectName }).click();

  await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
  await page.getByRole("button", { name: "New experiment" }).click();
  await page.getByLabel("Experiment name").fill("Browser baseline");
  await page.getByLabel("Description").fill("Created through the real API");
  await page.getByLabel("Tags").fill("e2e, baseline");
  await page.getByRole("button", { name: "Create experiment" }).click();

  await expect(page.getByRole("link", { name: "Browser baseline" })).toBeVisible();
  await page.getByRole("link", { name: "Browser baseline" }).click();
  await page.getByRole("link", { name: "Create run" }).click();
  await expect(page.getByRole("heading", { name: "Create run" })).toBeVisible();
  await page.getByLabel("N Estimators").fill("20");
  await page.getByRole("button", { name: "Create and execute run" }).click();

  await expect(page.locator(".status-badge", { hasText: "SUCCEEDED" })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByRole("heading", { name: "Metrics" })).toBeVisible();
  await expect(page.getByText("Loaded the built-in scikit-learn Iris dataset")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download" }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.(joblib|json|svg)$/);
});
