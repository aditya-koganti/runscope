import { mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";
const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const outputDirectory = path.join(repositoryRoot, "demo-output");
const outputPath = path.join(outputDirectory, "runscope-demo.webm");

await mkdir(outputDirectory, { recursive: true });
await rm(outputPath, { force: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: {
    dir: outputDirectory,
    size: { width: 1440, height: 900 },
  },
});
const page = await context.newPage();
const video = page.video();

page.setDefaultTimeout(20_000);
page.setDefaultNavigationTimeout(30_000);

async function navigateInApp(targetPath) {
  await page.evaluate((target) => {
    window.history.pushState({}, "", target);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, targetPath);
}

async function installPresentationLayer() {
  await page.evaluate(() => {
    const style = document.createElement("style");
    style.textContent = `
      #runscope-demo-caption {
        position: fixed;
        z-index: 2147483647;
        left: 50%;
        bottom: 28px;
        width: min(900px, calc(100vw - 64px));
        transform: translateX(-50%);
        padding: 16px 22px;
        border: 1px solid rgba(91, 196, 255, 0.55);
        border-radius: 14px;
        background: rgba(8, 17, 29, 0.94);
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.38);
        color: #f8fbff;
        font: 600 20px/1.4 Inter, ui-sans-serif, system-ui, sans-serif;
        letter-spacing: 0.01em;
        text-align: center;
        pointer-events: none;
        opacity: 0;
        transition: opacity 180ms ease;
      }
      #runscope-demo-caption[data-visible="true"] {
        opacity: 1;
      }
      #runscope-demo-cursor {
        position: fixed;
        z-index: 2147483646;
        width: 24px;
        height: 24px;
        margin: -12px 0 0 -12px;
        border: 3px solid #5bc4ff;
        border-radius: 999px;
        background: rgba(91, 196, 255, 0.16);
        box-shadow: 0 0 0 5px rgba(91, 196, 255, 0.12);
        pointer-events: none;
        transition: transform 100ms ease;
      }
    `;
    document.head.append(style);

    const caption = document.createElement("div");
    caption.id = "runscope-demo-caption";
    document.body.append(caption);

    const cursor = document.createElement("div");
    cursor.id = "runscope-demo-cursor";
    cursor.style.left = "50%";
    cursor.style.top = "50%";
    document.body.append(cursor);

    document.addEventListener(
      "mousemove",
      (event) => {
        cursor.style.left = `${event.clientX}px`;
        cursor.style.top = `${event.clientY}px`;
      },
      { passive: true },
    );
    document.addEventListener(
      "mousedown",
      () => {
        cursor.style.transform = "scale(0.72)";
      },
      { passive: true },
    );
    document.addEventListener(
      "mouseup",
      () => {
        cursor.style.transform = "scale(1)";
      },
      { passive: true },
    );
  });
}

async function caption(message, duration = 2_000) {
  await page.evaluate((text) => {
    const element = document.querySelector("#runscope-demo-caption");
    if (!(element instanceof HTMLElement)) {
      throw new Error("Demo caption layer is unavailable");
    }
    element.textContent = text;
    element.dataset.visible = "true";
  }, message);
  await page.waitForTimeout(duration);
  await page.evaluate(() => {
    const element = document.querySelector("#runscope-demo-caption");
    if (element instanceof HTMLElement) {
      element.dataset.visible = "false";
    }
  });
  await page.waitForTimeout(250);
}

async function settle(duration = 650) {
  await page.waitForTimeout(duration);
}

try {
  const suffix = Date.now().toString(36);
  const projectName = `Portfolio demo ${suffix}`;

  await page.goto(`${baseURL}/sign-in`, { waitUntil: "networkidle" });
  await installPresentationLayer();
  await caption(
    "RunScope: a trusted CPU machine-learning control plane, demonstrated end to end",
    2_800,
  );

  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "Overview" }).waitFor();
  await page.getByText("API operational").waitFor();
  await caption(
    "The overview combines durable run state, live updates, queue depth, and worker capacity",
  );

  await page.getByRole("link", { name: "Projects" }).click();
  await settle();
  await page.getByRole("button", { name: "New project" }).click();
  await page.getByLabel("Project name").fill(projectName);
  await page
    .getByLabel("Description")
    .fill("A reproducible portfolio walkthrough using the real API");
  await caption("Researchers organize approved work into projects and experiments", 1_500);
  await page.getByRole("button", { name: "Create project" }).click();
  await page.getByRole("link", { name: projectName }).click();

  await page.getByRole("heading", { name: projectName }).waitFor();
  await page.getByRole("button", { name: "New experiment" }).click();
  await page.getByLabel("Experiment name").fill("Iris model selection");
  await page
    .getByLabel("Description")
    .fill("Compare registered CPU training templates");
  await page.getByLabel("Tags").fill("portfolio, iris");
  const experimentResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/experiments") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create experiment" }).click();
  const createdExperiment = await (await experimentResponse).json();
  await navigateInApp(`/experiments/${createdExperiment.id}`);

  await page.getByRole("heading", { name: "Iris model selection" }).waitFor();
  await page.getByRole("link", { name: "Create run" }).click();
  await page.getByRole("heading", { name: "Create run" }).waitFor();
  await page.getByLabel("N Estimators").fill("40");
  await caption(
    "Users select a versioned template and validated parameters, never arbitrary code",
    2_200,
  );
  await page.getByRole("button", { name: "Create and execute run" }).click();

  await page.getByText("Live: connected").waitFor();
  await caption(
    "PostgreSQL commits the run, the outbox publishes it, and the scheduler reserves capacity",
    2_800,
  );
  await page.locator(".status-badge", { hasText: "SUCCEEDED" }).waitFor({
    timeout: 30_000,
  });
  await page.getByRole("heading", { name: "Metrics" }).scrollIntoViewIfNeeded();
  await caption(
    "A trusted worker produced real scikit-learn metrics, logs, lifecycle events, and artifacts",
    2_800,
  );
  const classificationRunId = page.url().split("/").at(-1);
  if (!classificationRunId) {
    throw new Error("Could not determine the classification run ID");
  }

  await navigateInApp(`/experiments/${createdExperiment.id}/runs/new`);
  await page.getByLabel("Training template").selectOption("slow-demonstration");
  await page.getByLabel("Duration Seconds").fill("6");
  await page.getByLabel("Interval Seconds").fill("0.5");
  await page.getByRole("button", { name: "Create and execute run" }).click();
  await page.getByRole("button", { name: "Cancel run" }).waitFor();
  await caption(
    "Cancellation is a durable command that workers acknowledge only at a safe checkpoint",
    2_200,
  );
  await page.getByRole("button", { name: "Cancel run" }).click();
  await page.locator(".status-badge", { hasText: "CANCELLED" }).waitFor();
  await caption("The state machine records cancellation without losing the run history", 1_800);

  await navigateInApp(`/experiments/${createdExperiment.id}/runs/new`);
  await page.getByLabel("Training template").selectOption("slow-demonstration");
  await page.getByLabel("Duration Seconds").fill("2");
  await page.getByLabel("Interval Seconds").fill("0.25");
  await page.getByLabel("Fail Intentionally").selectOption("true");
  await page.getByRole("button", { name: "Create and execute run" }).click();
  await page.locator(".status-badge", { hasText: "FAILED" }).waitFor();
  await caption("Controlled failures remain durable and can be retried with lineage", 1_800);
  await page.getByRole("button", { name: "Retry run" }).click();
  await page.locator(".status-badge", { hasText: "SUCCEEDED" }).waitFor();
  const retryRunId = page.url().split("/").at(-1);
  if (!retryRunId) {
    throw new Error("Could not determine the retry run ID");
  }
  await caption("The child run succeeded while preserving its link to the failed parent", 2_000);

  await navigateInApp("/runs/compare");
  await page
    .getByRole("checkbox", {
      name: new RegExp(classificationRunId.slice(0, 8)),
    })
    .check();
  await page
    .getByRole("checkbox", { name: new RegExp(retryRunId.slice(0, 8)) })
    .check();
  await page.getByRole("button", { name: "Compare 2 runs" }).click();
  await page.getByRole("heading", { name: "Metric overlay" }).waitFor();
  await caption(
    "Completed runs can be compared across parameters, final metrics, and metric series",
    2_300,
  );

  await navigateInApp("/workers");
  await page.getByRole("heading", { name: "Workers" }).waitFor();
  await page.getByRole("link", { name: "worker-local-1" }).waitFor();
  await caption(
    "Two heartbeating workers expose reserved and available CPU and memory",
    2_100,
  );

  await navigateInApp("/platform-health");
  await page.getByRole("heading", { name: "Platform health" }).waitFor();
  await page.getByText("healthy", { exact: true }).first().waitFor();
  await caption(
    "Dependency probes, scheduler health, capacity, and backlog make operations visible",
    2_500,
  );
  await caption(
    "RunScope demonstrates the reliability boundaries of a small ML platform without overclaiming scale",
    3_000,
  );
} finally {
  await context.close();
  if (video) {
    await video.saveAs(outputPath);
  }
  await browser.close();
}

console.log(`Captured RunScope demo video at ${outputPath}`);
