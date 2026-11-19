import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs";

const base = process.env.CUTLINE_URL ?? "http://127.0.0.1:3000";
fs.mkdirSync("test-results", { recursive: true });
const browser = await chromium.launch({ headless: true });
const errors = [];

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(base, { waitUntil: "domcontentloaded" });
  await page.getByLabel("Story, link, or description").waitFor({ timeout: 15000 });
  await page.getByRole("heading", { name: "Your story. Cut like a film." }).waitFor();
  await page.getByLabel("Story, link, or description").fill("https://example.com");
  await page.getByLabel("Cinematic style").selectOption("tech_launch");
  await page.getByLabel("Narration voice").selectOption("Aoede");
  await page.getByLabel("Add source files").setInputFiles({ name: "evidence.txt", mimeType: "text/plain", buffer: Buffer.from("Portfolio evidence") });
  await page.getByText("evidence.txt").waitFor();
  await page.getByRole("button", { name: "Remove evidence.txt" }).click();
  await page.screenshot({ path: "test-results/link2reel-home.png" });

  await page.getByRole("button", { name: "Watch portfolio demo" }).click();
  await page.waitForURL(/\/project\/[a-f0-9]+/);
  await page.getByRole("heading", { name: "Script + cited sources" }).waitFor({ timeout: 90000 });
  const trailer = page.locator("video[aria-label$='vertical motion video']");
  await page.waitForFunction(() => {
    const video = document.querySelector("video[aria-label$='vertical motion video']");
    return video && video.readyState >= 1 && video.duration >= 30;
  }, { timeout: 30000 });
  const duration = await trailer.evaluate((video) => video.duration);
  assert(duration >= 30 && duration <= 40, `Sample duration ${duration}`);
  assert.equal(await page.locator("ol li").count() >= 2, true, "Cited sources render");
  assert.match(await page.locator("main").innerText(), /Mohd Daniyal/);
  assert.match(await page.locator("main").innerText(), /100,000 users/);
  assert.match(await page.locator("main").innerText(), /500 milliseconds/);
  assert.match(await page.locator("main").innerText(), /99.9 percent uptime/);
  await page.getByRole("button", { name: /Seek to 12.0s/ }).click();
  assert(await trailer.evaluate((video) => video.currentTime) >= 12);
  await page.getByRole("button", { name: "Copy script" }).click();
  await page.getByRole("status").waitFor();

  const projectId = page.url().split("/").pop();
  const zip = await page.request.get(`${base}/api/studio/projects/${projectId}/download`);
  assert.equal(zip.status(), 200);
  assert.equal((await zip.body()).subarray(0, 2).toString(), "PK");
  await page.screenshot({ path: "test-results/link2reel-premiere.png" });
  await page.setViewportSize({ width: 375, height: 812 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "375px premiere has no overflow");
  await page.screenshot({ path: "test-results/link2reel-mobile-premiere.png" });

  const reduced = await browser.newPage({ viewport: { width: 375, height: 812 }, reducedMotion: "reduce" });
  await reduced.goto(base, { waitUntil: "domcontentloaded" });
  await reduced.waitForTimeout(800);
  assert(await reduced.locator("video").evaluateAll((videos) => videos.every((video) => video.paused)), "Reduced motion pauses videos");
  assert(await reduced.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "Reduced mobile has no overflow");
  await reduced.close();
  assert.deepEqual(errors, [], errors.join(" | "));
  console.log(JSON.stringify({ status: "passed", duration, projectId }, null, 2));
} finally {
  await browser.close();
}
