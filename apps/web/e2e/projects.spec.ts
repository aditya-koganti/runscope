import { expect, test } from "@playwright/test";

test("researcher creates a project and experiment", async ({ page }) => {
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
});
