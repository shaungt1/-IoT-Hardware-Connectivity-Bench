import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const output = new URL("../artifacts/", import.meta.url);
await mkdir(fileURLToPath(output), { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => message.type() === "error" && errors.push(message.text()));

async function verifyHtml() {
  await page.goto("http://127.0.0.1:8765", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => !document.querySelector("#ports-body")?.textContent?.includes("Loading"));
  await page.locator("#ports-body tr", { hasText: "COM11" }).click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.waitForFunction(() => !["", "--"].includes(document.querySelector("#intelligence-model")?.textContent?.trim() || ""));
  await page.locator('[data-workspace-tab="pins"]').click();
  await page.locator("#runtime-probe:not([disabled])").waitFor({ timeout: 15_000 });
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#runtime-probe").click();
  await page.waitForFunction(() => document.querySelector("#pins-message")?.textContent?.includes("ESP8266EX"), null, { timeout: 30_000 });
  await page.waitForFunction(() => document.querySelector("#pin-count")?.textContent?.includes("23 pins"));
  await page.locator('[data-workspace-tab="device"]').click();
  await page.getByText("ESP8266EX", { exact: true }).first().waitFor();
  await page.getByText("4MB flash", { exact: true }).first().waitFor();
  await page.locator("#device-model-select").selectOption("NodeMCU ESP8266 development board (ESP-12E/F)");
  await page.locator("#device-model-form").getByRole("button", { name: /save model/i }).click();
  await page.waitForFunction(() => document.querySelector("#intelligence-model")?.textContent?.includes("NodeMCU ESP8266"));
  await page.locator('[data-workspace-tab="tests"]').click();
  if (!(await page.locator('[data-radio-tab="ble"]').isHidden())) throw new Error("HTML shows BLE control for Wi-Fi-only ESP8266");
  if (await page.locator('[data-radio-tab="wifi"]').isHidden()) throw new Error("HTML hides ESP8266 Wi-Fi control");
  const wifiTest = page.locator("#device-tests .test-row", { hasText: "Verify ESP8266 2.4 GHz Wi-Fi capability" });
  await wifiTest.getByRole("button", { name: /run test/i }).click();
  await wifiTest.getByText(/integrated 2.4 GHz Wi-Fi hardware/i).waitFor({ timeout: 15_000 });
  await page.screenshot({ path: fileURLToPath(new URL("html-esp8266-tests.png", output)), fullPage: true });
}

async function verifyReact() {
  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByText(/selectable interfaces found/i).waitFor();
  await page.getByRole("row", { name: /COM11 Silicon Labs CP210x/i }).click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.getByText("NodeMCU ESP8266 development board (ESP-12E/F)", { exact: true }).first().waitFor();
  await page.getByText("Target processor", { exact: true }).waitFor();
  await page.getByText("ESP8266EX", { exact: true }).first().waitFor();
  await page.locator(".workflow button", { hasText: "Pins & buses" }).click();
  await page.getByText("23 pins", { exact: true }).first().waitFor();
  if (await page.getByRole("button", { name: /run deep probe/i }).isDisabled()) throw new Error("React ESP ROM probe is disabled");
  await page.locator(".workflow button", { hasText: "Tests" }).click();
  const wifiTest = page.locator(".test-card", { hasText: "Verify ESP8266 2.4 GHz Wi-Fi capability" });
  await wifiTest.getByRole("button", { name: /^run$/i }).click();
  await wifiTest.getByText(/integrated 2.4 GHz Wi-Fi hardware/i).waitFor({ timeout: 15_000 });
  await page.screenshot({ path: fileURLToPath(new URL("react-esp8266-tests.png", output)), fullPage: true });
}

try {
  await verifyHtml();
  await verifyReact();
  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log("VERIFY_OK: ESP8266 bridge, target, board, pins, and Wi-Fi-only flow passed in both clients.");
} finally {
  await browser.close();
}
