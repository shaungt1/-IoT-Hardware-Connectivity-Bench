import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const output = new URL("../artifacts/", import.meta.url);
await mkdir(fileURLToPath(output), { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });

try {
  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByText(/selectable interfaces found/i).waitFor();
  const target = page.locator("tbody tr").filter({ hasText: /Espressif ESP32 USB JTAG\/serial family|Seeed Studio XIAO ESP32-S3 Sense/i }).first();
  await target.click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.getByRole("heading", { name: /device identity and capabilities/i }).waitFor();
  await page.getByRole("heading", { name: "Camera", exact: true }).waitFor();
  await page.getByRole("complementary", { name: /selected hardware live status/i }).waitFor();
  await page.waitForFunction(() => {
    const image = document.querySelector(".camera-viewport img");
    return image instanceof HTMLImageElement && image.complete && image.naturalWidth > 1 && image.naturalHeight > 1;
  }, null, { timeout: 15_000 });
  await page.locator(".feed-badge", { hasText: /DEVICE DIRECT|USB WEBSOCKET/ }).waitFor({ timeout: 5_000 });
  await page.waitForFunction(() => {
    const text = document.querySelector(".camera-metrics")?.textContent || "";
    const fps = Number(text.match(/([\d.]+)\s*FPS/)?.[1] || 0);
    return fps > 1;
  }, null, { timeout: 15_000 });
  await page.waitForTimeout(3500);
  const liveText = await page.locator(".live-device-grid").innerText();
  for (const expected of ["Bluetooth (BLE)", "Wi-Fi", "Compatible"]) {
    if (!liveText.includes(expected)) throw new Error(`Selected-device panel is missing ${expected}`);
  }
  await page.getByText("Seeed Studio XIAO ESP32-S3 Sense", { exact: true }).first().waitFor();
  const performanceText = await page.locator(".camera-metrics").innerText();
  const rates = await page.locator(".camera-metrics").evaluate((element) => {
    const text = element.textContent || "";
    return {
      browser: Number(text.match(/([\d.]+)\s*FPS/)?.[1] || 0),
      benchmark: element.querySelector(".camera-benchmark")?.textContent || "",
    };
  });
  if (rates.browser < 1) throw new Error(`Camera paint rate is below minimum: ${JSON.stringify(rates)}`);
  await page.getByRole("button", { name: "Camera image controls" }).click();
  const brightness = page.locator('[aria-label="Camera image controls"]').getByText("Brightness").locator("..").getByRole("slider");
  await brightness.fill("1");
  await page.waitForFunction(() => document.querySelector('[aria-label="Camera image controls"] input')?.value === "1", null, { timeout: 5_000 });
  await brightness.fill("0");
  await page.screenshot({ path: fileURLToPath(new URL("react-live-device.png", output)), fullPage: true });

  await page.locator('.workflow button[title^="Connections:"]').click();
  await page.getByRole("heading", { name: "Connections", exact: true }).waitFor();
  const blePower = page.getByRole("button", { name: /BLE broadcast/i }).first();
  if (await blePower.isDisabled()) throw new Error("BLE device control is disabled for the compatible live target");
  await page.getByRole("button", { name: /read nearby with computer/i }).click();
  await page.getByRole("button", { name: /scan with computer/i }).click();
  await page.getByText(/nearby BLE devices found|received at/i).waitFor({ timeout: 15_000 });
  await page.getByRole("button", { name: /^Wi-Fi$/i }).click();
  await page.getByRole("button", { name: /connect device to Wi-Fi/i }).click();
  await page.getByRole("button", { name: /scan computer/i }).click();
  await page.getByText(/networks found by this computer|Wi-Fi adapter is available/i).waitFor({ timeout: 15_000 });
  await page.screenshot({ path: fileURLToPath(new URL("react-wireless-controls.png", output)), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw new Error("Live device controls cause page-level horizontal overflow on mobile");
  await page.screenshot({ path: fileURLToPath(new URL("react-wireless-controls-mobile.png", output)), fullPage: true });
  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log(`VERIFY_OK: camera stream (${performanceText.replaceAll("\n", " | ")}), device telemetry, BLE controls, Wi-Fi controls, scans, and mobile layout passed.`);
} finally {
  await browser.close();
}
