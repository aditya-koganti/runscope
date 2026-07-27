import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";
const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const outputDirectory = path.join(repositoryRoot, "docs", "assets");

await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});

try {
  await page.goto(`${baseURL}/sign-in`, { waitUntil: "networkidle" });
  await page.screenshot({
    path: path.join(outputDirectory, "runscope-sign-in.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: "Overview" }).waitFor();
  await page.getByText("API operational").waitFor();
  await page.waitForFunction(
    () =>
      !document.body.innerText.includes("No runs yet") &&
      !document.body.innerText.includes("0/0"),
  );
  await page.screenshot({
    path: path.join(outputDirectory, "runscope-overview.png"),
    fullPage: true,
  });

  const successfulRow = page
    .locator("tbody tr", { has: page.locator(".status-succeeded") })
    .first();
  await Promise.all([
    page.waitForURL(/\/runs\/[0-9a-f-]+$/),
    successfulRow.getByRole("link").click(),
  ]);
  await page.getByRole("heading", { name: "Metrics" }).waitFor();
  await page.waitForTimeout(1_200);
  await page.screenshot({
    path: path.join(outputDirectory, "runscope-run-detail.png"),
    fullPage: true,
  });

  await page.getByRole("link", { name: "Workers" }).click();
  await page.getByRole("heading", { name: "Workers" }).waitFor();
  await page.getByRole("link", { name: "worker-local-1" }).waitFor();
  await page.screenshot({
    path: path.join(outputDirectory, "runscope-workers.png"),
    fullPage: true,
  });

  await page.getByRole("link", { name: "Platform health" }).click();
  await page.getByRole("heading", { name: "Platform health" }).waitFor();
  await page.getByText("healthy", { exact: true }).first().waitFor();
  await page.screenshot({
    path: path.join(outputDirectory, "runscope-platform-health.png"),
    fullPage: true,
  });
} finally {
  await browser.close();
}

console.log(`Captured RunScope screenshots in ${outputDirectory}`);
