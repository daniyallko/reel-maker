import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE_URL = process.env.CUTLINE_URL || "http://127.0.0.1:3000";
const OUTPUT_DIR = process.env.TEST_OUTPUT_DIR || "test-results/rise-of-google-run2";
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

async function run() {
  console.log(`[E2E] Starting test with base URL: ${BASE_URL}`);
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const page = await context.newPage();
  const logs = [];

  page.on("console", (msg) => {
    const text = `[Browser Console ${msg.type()}] ${msg.text()}`;
    logs.push(text);
    console.log(text);
  });

  page.on("pageerror", (err) => {
    const text = `[Browser Error] ${err.message}`;
    logs.push(text);
    console.error(text);
  });

  try {
    console.log(`[E2E] Navigating to ${BASE_URL}...`);
    await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
    await page.getByLabel("Story, link, or description").waitFor({ timeout: 15000 });
    console.log("[E2E] Home page loaded.");

    // Fill topic
    const topic = "Rise of Google";
    await page.getByLabel("Story, link, or description").fill(topic);
    console.log(`[E2E] Entered topic: "${topic}"`);

    await page.screenshot({ path: path.join(OUTPUT_DIR, "01-home-filled.png") });

    // Submit the form
    console.log("[E2E] Submitting form...");
    const submitBtn = page.locator("button[type='submit']");
    await submitBtn.click();

    // Wait for navigation to /project/[id]
    console.log("[E2E] Waiting for navigation to project page...");
    await page.waitForURL(/\/project\/[a-f0-9]+/, { timeout: 15000 });
    const projectUrl = page.url();
    const projectId = projectUrl.split("/").pop();
    console.log(`[E2E] Project created: ${projectId} (${projectUrl})`);

    await page.screenshot({ path: path.join(OUTPUT_DIR, "02-project-screening.png") });

    // Monitor progress
    console.log(`[E2E] Tracking project ${projectId} events and steps...`);
    let lastEventCount = 0;
    let completed = false;
    let failed = false;
    let failureReason = "";
    const startTime = Date.now();
    const maxWaitMs = 12 * 60 * 1000; // 12 minutes max

    while (Date.now() - startTime < maxWaitMs) {
      // Query backend snapshot
      const res = await fetch(`http://127.0.0.1:8000/api/studio/projects/${projectId}`);
      if (!res.ok) {
        console.error(`[E2E] Failed to fetch project snapshot: HTTP ${res.status}`);
      } else {
        const snapshot = await res.json();
        const events = snapshot.events || [];

        // Log any new events
        if (events.length > lastEventCount) {
          for (let i = lastEventCount; i < events.length; i++) {
            const ev = events[i];
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            console.log(
              `[T+${elapsed}s] [Event #${ev.id}] [${ev.agent}] [${ev.status}] (${ev.progress}%): ${ev.message}`
            );
          }
          lastEventCount = events.length;

          // Take a screenshot when new milestone hit
          const latest = events[events.length - 1];
          if (latest.status === "complete" || latest.status === "failed") {
            const safeAgent = latest.agent.replace(/[^a-z0-9_-]/gi, "_");
            await page.screenshot({
              path: path.join(OUTPUT_DIR, `milestone-${latest.id}-${safeAgent}-${latest.status}.png`),
            });
          }
        }

        if (snapshot.status === "complete") {
          console.log("[E2E] Project completed successfully!");
          completed = true;
          await page.screenshot({ path: path.join(OUTPUT_DIR, "03-project-complete.png") });
          break;
        }

        if (snapshot.status === "failed") {
          console.log(`[E2E] Project failed: ${snapshot.error}`);
          failed = true;
          failureReason = snapshot.error || "Unknown error";
          await page.screenshot({ path: path.join(OUTPUT_DIR, "03-project-failed.png") });
          break;
        }
      }

      await page.waitForTimeout(4000);
    }

    const totalSeconds = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`[E2E] Run finished in ${totalSeconds}s. Completed: ${completed}, Failed: ${failed}`);
    if (failed) {
      console.log(`[E2E] Failure details: ${failureReason}`);
    }

    fs.writeFileSync(
      path.join(OUTPUT_DIR, "summary.json"),
      JSON.stringify(
        {
          projectId,
          completed,
          failed,
          failureReason,
          totalSeconds,
        },
        null,
        2
      )
    );
  } catch (err) {
    console.error("[E2E] Test encountered unexpected error:", err);
    await page.screenshot({ path: path.join(OUTPUT_DIR, "error.png") }).catch(() => {});
  } finally {
    await browser.close();
  }
}

run();
