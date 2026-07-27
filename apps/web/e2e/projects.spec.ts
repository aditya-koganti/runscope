import { expect, test } from "@playwright/test";

async function navigateInApp(
  page: import("@playwright/test").Page,
  path: string,
) {
  await page.evaluate((target) => {
    window.history.pushState({}, "", target);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
}

test("researcher completes the classification, cancellation, retry, and comparison flow", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const suffix = Date.now().toString(36);
  const projectName = `E2E project ${suffix}`;

  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({
    timeout: 15_000,
  });

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
  const experimentResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/experiments") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create experiment" }).click();
  const createdExperiment = (await (await experimentResponse).json()) as {
    id: string;
  };
  await navigateInApp(page, `/experiments/${createdExperiment.id}`);
  await expect(page.getByRole("heading", { name: "Browser baseline" })).toBeVisible();
  await page.getByRole("link", { name: "Create run" }).click();
  await expect(page.getByRole("heading", { name: "Create run" })).toBeVisible();
  await page.getByLabel("N Estimators").fill("20");
  await page.getByRole("button", { name: "Create and execute run" }).click();

  await expect(page.getByText("Live: connected")).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(".status-badge", { hasText: "SUCCEEDED" })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByRole("heading", { name: "Metrics" })).toBeVisible();
  await expect(page.getByText("Loaded the built-in scikit-learn Iris dataset")).toBeVisible();
  const downloadResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/artifacts/") &&
      response.url().endsWith("/download") &&
      response.request().method() === "GET",
  );
  await page.getByRole("button", { name: "Download" }).first().click();
  const artifactResponse = await downloadResponse;
  expect(artifactResponse.status()).toBe(200);
  expect(Number(artifactResponse.headers()["content-length"])).toBeGreaterThan(0);
  const classificationRunId = page.url().split("/").at(-1);
  expect(classificationRunId).toBeTruthy();

  await navigateInApp(page, `/experiments/${createdExperiment.id}/runs/new`);
  await page.getByLabel("Training template").selectOption("slow-demonstration");
  await page.getByLabel("Duration Seconds").fill("5");
  await page.getByLabel("Interval Seconds").fill("0.5");
  await page.getByRole("button", { name: "Create and execute run" }).click();
  await expect(page.getByRole("button", { name: "Cancel run" })).toBeVisible({
    timeout: 20_000,
  });
  await page.getByRole("button", { name: "Cancel run" }).click();
  await expect(page.locator(".status-badge", { hasText: "CANCELLED" })).toBeVisible({
    timeout: 20_000,
  });
  await expect(
    page.getByText("Cancellation acknowledged at a safe checkpoint"),
  ).toBeVisible();

  await navigateInApp(page, `/experiments/${createdExperiment.id}/runs/new`);
  await page.getByLabel("Training template").selectOption("slow-demonstration");
  await page.getByLabel("Duration Seconds").fill("2");
  await page.getByLabel("Interval Seconds").fill("0.25");
  await page.getByLabel("Fail Intentionally").selectOption("true");
  await page.getByRole("button", { name: "Create and execute run" }).click();
  await expect(page.locator(".status-badge", { hasText: "FAILED" })).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("The slow demonstration was configured to fail")).toBeVisible();
  await page.getByRole("button", { name: "Retry run" }).click();
  await expect(page.locator(".status-badge", { hasText: "SUCCEEDED" })).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText(/Retried from/)).toBeVisible();
  const retryRunId = page.url().split("/").at(-1);
  expect(retryRunId).toBeTruthy();

  await page.getByLabel("Notes").fill("Retry verified through Playwright");
  await page.getByLabel("Tags").fill("e2e, retry");
  const metadataResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/api/v1/runs/${retryRunId}/metadata`) &&
      response.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "Save metadata" }).click();
  expect((await metadataResponse).status()).toBe(200);

  await navigateInApp(page, "/runs/compare");
  await page
    .getByRole("checkbox", { name: new RegExp(classificationRunId!.slice(0, 8)) })
    .check();
  await page
    .getByRole("checkbox", { name: new RegExp(retryRunId!.slice(0, 8)) })
    .check();
  await page.getByRole("button", { name: "Compare 2 runs" }).click();
  await expect(page.getByRole("heading", { name: "Parameters" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Final metrics" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Metric overlay" })).toBeVisible();

  await navigateInApp(page, "/workers");
  await expect(page.getByRole("heading", { name: "Workers" })).toBeVisible();
  await expect(page.getByRole("link", { name: "worker-local-1" })).toBeVisible();
  await expect(page.getByRole("link", { name: "worker-local-2" })).toBeVisible();
});
