import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs";

const base = process.env.CUTLINE_URL ?? "http://127.0.0.1:3000";
fs.mkdirSync("test-results", { recursive: true });
const browser = await chromium.launch({ headless: true });
const pageErrors = [];
const failedMedia = [];

function watch(page) {
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    const errorText = request.failure()?.errorText ?? "";
    if (request.url().endsWith(".mp4") && !errorText.includes("ERR_ABORTED")) failedMedia.push(`${request.url()}: ${errorText}`);
  });
  page.on("response", (response) => {
    if (response.url().endsWith(".mp4") && response.status() >= 400) failedMedia.push(`${response.url()}: HTTP ${response.status()}`);
  });
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  watch(page);
  await page.goto(base, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2400);
  await page.waitForFunction(() => document.querySelector("h1")?.textContent?.includes("Weekend"), { timeout: 10000 });
  assert.match(await page.locator("h1").innerText(), /Weekend\s+In motion/);
  assert.match(await page.locator("h1").evaluate((node) => getComputedStyle(node).fontFamily), /Space Mono/);
  assert.equal(await page.locator("video").first().evaluate((video) => video.paused), true, "Hero starts paused");
  await page.screenshot({ path: "test-results/neon-home.png", fullPage: false });

  await page.waitForFunction(() => {
    const video = document.querySelector("video");
    return video && Number.isFinite(video.duration) && video.duration > 0;
  }, { timeout: 30000 });
  const beforeScrub = await page.locator("video").first().evaluate((video) => video.currentTime);
  await page.mouse.move(100, 260);
  await page.mouse.move(700, 260, { steps: 8 });
  await page.waitForTimeout(600);
  const afterScrub = await page.locator("video").first().evaluate((video) => video.currentTime);
  assert(afterScrub > beforeScrub, `Mouse scrub should advance video: ${beforeScrub} -> ${afterScrub}`);

  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Media", exact: true }).click();
  await page.waitForTimeout(300);
  assert.equal(await page.getByRole("button", { name: "Open navigation" }).count(), 1);

  const mobile = await browser.newPage({ viewport: { width: 375, height: 812 } });
  watch(mobile);
  await mobile.goto(base, { waitUntil: "domcontentloaded" });
  await mobile.waitForTimeout(1600);
  assert(await mobile.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "375px home has no horizontal overflow");
  await mobile.screenshot({ path: "test-results/neon-mobile-home.png", fullPage: false });
  await mobile.close();

  await page.goto(base, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /Load Sample Chaos Trip/i }).click();
  await page.waitForURL(/\/project\/[a-f0-9]+/, { timeout: 30000 });
  await page.getByText("THE PREMIERE PRESS KIT / FINAL CUT").waitFor({ timeout: 90000 });
  const projectUrl = page.url();
  const trailer = page.locator("video[aria-label$='vertical movie trailer']");
  await trailer.waitFor();
  await page.waitForFunction(() => {
    const video = document.querySelector("video[aria-label$='vertical movie trailer']");
    return video && video.readyState >= 1 && video.duration >= 20;
  }, { timeout: 30000 });
  const duration = await trailer.evaluate((video) => video.duration);
  assert(duration >= 20 && duration <= 25, `Sample duration ${duration}`);
  const poster = page.locator("img[alt^='Theatrical poster']");
  await page.waitForFunction(() => document.querySelector("img[alt^='Theatrical poster']")?.naturalWidth === 1080);
  assert.equal(await poster.evaluate((image) => image.naturalHeight), 1920);

  const firstCastAlt = await page.locator("section[aria-label='Meet the Cast character cards'] img").first().getAttribute("alt");
  await page.getByRole("button", { name: "Next cast member" }).click();
  await page.waitForTimeout(600);
  const nextCastAlt = await page.locator("section[aria-label='Meet the Cast character cards'] img").first().getAttribute("alt");
  assert.notEqual(firstCastAlt, nextCastAlt, "Cast carousel advances");

  const timelineButton = page.locator("button[aria-label^='Seek to']").nth(2);
  await timelineButton.click();
  assert(await trailer.evaluate((video) => video.currentTime) >= 4, "Timeline seeks trailer");
  await trailer.evaluate((video) => video.play());
  await page.waitForTimeout(700);
  await trailer.evaluate((video) => video.pause());

  await page.getByRole("button", { name: /Inspect full-resolution poster/ }).click();
  await page.getByRole("dialog", { name: "Theatrical one-sheet" }).waitFor();
  await page.getByRole("button", { name: "Close inspector" }).click();
  await page.getByRole("button", { name: /Inspect edit decision list/ }).click();
  await page.getByRole("dialog", { name: "Edit decision list" }).waitFor();
  await page.getByRole("button", { name: "Close inspector" }).click();

  const projectId = projectUrl.split("/").pop();
  const zip = await page.request.get(`${base}/api/projects/${projectId}/download`);
  assert.equal(zip.status(), 200);
  const zipBody = await zip.body();
  assert.equal(zipBody.subarray(0, 2).toString(), "PK", "Download is a ZIP");

  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("button", { name: "WhatsApp", exact: true }).click();
  const popup = await popupPromise;
  assert.match(popup.url(), /wa\.me|whatsapp\.com/);
  await popup.close();

  const downloadPromise = page.waitForEvent("download", { timeout: 10000 }).catch(() => null);
  await page.getByRole("button", { name: "Instagram", exact: true }).click();
  const instagramDownload = await downloadPromise;
  if (instagramDownload) assert.match(instagramDownload.suggestedFilename(), /cutline-trailer\.mp4/);

  await page.setViewportSize({ width: 375, height: 812 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "375px premiere has no horizontal overflow");
  await page.screenshot({ path: "test-results/neon-premiere-mobile.png", fullPage: false });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: "test-results/neon-premiere.png", fullPage: false });

  const reduced = await browser.newPage({ viewport: { width: 375, height: 812 }, reducedMotion: "reduce" });
  watch(reduced);
  await reduced.goto(base, { waitUntil: "domcontentloaded" });
  await reduced.waitForTimeout(800);
  assert.match(await reduced.locator("h1").innerText(), /Weekend\s+In motion/);
  assert(await reduced.locator("video").evaluateAll((videos) => videos.every((video) => video.paused)), "Reduced motion pauses all background videos");
  assert(await reduced.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "Reduced-motion mobile has no overflow");
  await reduced.close();

  assert.deepEqual(pageErrors, [], `Browser page errors: ${pageErrors.join(" | ")}`);
  assert.deepEqual(failedMedia, [], `Media request failures: ${failedMedia.join(" | ")}`);
  console.log(JSON.stringify({ status: "passed", duration, projectId, screenshots: fs.readdirSync("test-results").filter((name) => name.endsWith(".png")) }, null, 2));
} finally {
  await browser.close();
}
