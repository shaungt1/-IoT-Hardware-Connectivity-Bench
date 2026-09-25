import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const output = new URL("../artifacts/", import.meta.url);
const outputPath = fileURLToPath(output);
await mkdir(outputPath, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});

async function verifyHtmlClient() {
  console.log("HTML: loading host inventory");
  await page.goto("http://127.0.0.1:8765", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => !document.querySelector("#usb-inventory-summary")?.textContent?.includes("Waiting"));
  const usbSummary = await page.locator("#usb-inventory-summary").textContent();
  const hostSummary = await page.locator("#host-inventory-summary").textContent();
  if (!usbSummary?.includes("physical USB devices")) throw new Error(`HTML USB inventory did not load: ${usbSummary}`);
  if (!hostSummary?.includes("active")) throw new Error(`HTML host inventory did not load: ${hostSummary}`);
  const featherRow = page.locator("#ports-body tr", { hasText: "Adafruit Feather M0 Express" });
  await featherRow.waitFor();
  await featherRow.click();
  await page.locator("#port-connect").click();
  await page.waitForFunction(() => document.querySelector("#intelligence-model")?.textContent?.includes("Feather M0 Express"));
  await page.waitForFunction(() => document.querySelector("#test-count")?.textContent?.includes("4 ready"));
  console.log("HTML inspection:", await page.locator("#intelligence-model").innerText(), "|", await page.locator("#device-tests").innerText());
  await page.locator('[data-workspace-tab="pins"]').click();
  await page.waitForFunction(() => document.querySelector("#pin-count")?.textContent?.includes("29 pins"));
  if (!(await page.locator("#runtime-firmware").innerText()).includes("CircuitPython 2.2.4")) throw new Error("HTML runtime telemetry did not render");
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#runtime-probe").click();
  await page.waitForFunction(() => document.querySelector("#pins-message")?.textContent?.includes("stable I2C"), null, { timeout: 20_000 });
  await page.screenshot({ path: fileURLToPath(new URL("html-feather-pins.png", output)), fullPage: true });
  await page.locator('[data-workspace-tab="tests"]').click();
  const htmlStorage = page.locator("#device-tests .test-row", { hasText: "CIRCUITPY storage" });
  const htmlTest = htmlStorage.getByRole("button", { name: /run test/i });
  try {
    await htmlTest.click({ timeout: 8_000 });
    await htmlStorage.getByText(/storage verified/i).waitFor({ timeout: 15_000 });
  } catch (error) {
    throw new Error(`HTML test action unavailable. Rendered panel: ${await page.locator("#device-tests").innerText()}. Browser errors: ${errors.join(" | ")}`, { cause: error });
  }
  await page.locator("#device-tests .test-result").waitFor();
  await page.locator('[data-workspace-tab="firmware"]').click();
  await page.waitForFunction(() => document.querySelector("#firmware-message")?.textContent?.includes("editable source"));
  await page.locator("#firmware-file-list button").first().click();
  await page.locator("#firmware-file-content:not([disabled])").waitFor();
  const htmlFlashButtons = page.locator(".firmware-operation", { hasText: "Flash" }).getByRole("button");
  if (await htmlFlashButtons.count() && !(await htmlFlashButtons.first().isDisabled())) throw new Error("HTML offered incompatible Feather firmware flash");
  await page.screenshot({ path: fileURLToPath(new URL("html-firmware.png", output)), fullPage: true });
  await page.locator('[data-workspace-tab="tools"]').click();
  await page.waitForFunction(() => document.querySelector("#provider-summary")?.textContent?.includes("ready"));
  await page.screenshot({ path: fileURLToPath(new URL("html-tools.png", output)) });
  console.log("HTML: host, Feather identity, pins, tests, firmware, and tools passed");
}

async function verifyReactClient() {
  console.log("React: loading host inventory");
  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByText(/selectable interfaces found/i).waitFor();
  await page.getByRole("row", { name: /COM12 Adafruit Feather M0 Express/i }).click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.getByRole("heading", { name: /device identity and capabilities/i }).waitFor();
  await page.locator(".workflow button", { hasText: "Pins & buses" }).click();
  await page.getByRole("heading", { name: /pins, buses and attached peripherals for adafruit feather m0 express/i }).waitFor();
  await page.getByText("29 pins", { exact: true }).first().waitFor();
  await page.getByText(/CircuitPython 2.2.4/).first().waitFor();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: /scan i2c bus/i }).click();
  await page.getByText(/stable responding address/i).waitFor({ timeout: 20_000 });
  await page.screenshot({ path: fileURLToPath(new URL("react-feather-pins.png", output)), fullPage: true });
  await page.locator(".workflow button", { hasText: "Tests" }).click();
  const reactStorage = page.locator(".test-card", { hasText: "CIRCUITPY storage" });
  await reactStorage.getByRole("button", { name: /^run$/i }).click();
  await reactStorage.getByText(/storage verified/i).waitFor({ timeout: 15_000 });
  await page.locator(".workflow button", { hasText: "Firmware & files" }).click();
  await page.getByRole("heading", { name: /firmware and files for adafruit feather m0 express/i }).waitFor();
  await page.locator(".file-root button").first().click();
  await page.locator(".code-editor textarea").waitFor();
  const reactFlash = page.locator(".operation-card", { hasText: "Flash" }).first().getByRole("button");
  if (!(await reactFlash.isDisabled())) throw new Error("React offered incompatible Feather firmware flash");
  await page.screenshot({ path: fileURLToPath(new URL("react-firmware.png", output)), fullPage: true });
  await page.locator(".workflow button", { hasText: "Tools & sources" }).click();
  await page.getByText(/metadata providers/i).waitFor();
  await page.screenshot({ path: fileURLToPath(new URL("react-tools.png", output)) });
  console.log("React: host, Feather identity, pins, tests, firmware, and tools passed");
}

async function verifyPrototype() {
  console.log("Prototype: loading a connected circuit target");
  await page.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await page.getByText(/selectable interfaces found/i).waitFor();
  const targetRow = page.locator("tbody tr").filter({ hasText: "Espressif ESP32 USB JTAG/serial family" }).first();
  await targetRow.waitFor();
  await targetRow.click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.getByRole("heading", { name: /device identity and capabilities/i }).waitFor();
  await page.locator(".workflow button", { hasText: "Prototype" }).click();
  await page.getByRole("heading", { name: /prototype/i }).waitFor();
  await page.locator(".prototype-canvas .react-flow").waitFor();
  if (!(await page.getByText("Virtual analog sensor", { exact: true }).count())) {
    await page.getByRole("button", { name: /analog sensor/i }).click();
    await page.locator(".prototype-inspector", { hasText: "Virtual analog sensor" }).waitFor();
  }
  if (!(await page.getByText("Virtual LED", { exact: true }).count())) {
    await page.getByRole("button", { name: /^led/i }).click();
    await page.locator(".prototype-inspector", { hasText: "Virtual LED" }).waitFor();
  }
  await page.getByRole("button", { name: /save prototype/i }).click();
  const savedStatus = page.getByText(/Saved \d+ component/i);
  await savedStatus.waitFor();
  const savedText = await savedStatus.innerText();
  const beforeReload = Number(savedText.match(/Saved (\d+) component/i)?.[1] || 0);
  if (beforeReload < 3) throw new Error(`Prototype did not add virtual parts: ${beforeReload} nodes`);
  await page.waitForTimeout(350);
  await page.screenshot({ path: fileURLToPath(new URL("react-prototype.png", output)), fullPage: true });

  await page.locator(".workflow button", { hasText: "Host & devices" }).click();
  await page.locator(".workflow button", { hasText: "Prototype" }).click();
  const loadedStatus = page.getByText(/\d+ component\(s\), \d+ connection/i);
  await loadedStatus.waitFor();
  const loadedText = await loadedStatus.innerText();
  const afterReload = Number(loadedText.match(/(\d+) component/i)?.[1] || 0);
  if (afterReload !== beforeReload) throw new Error(`Prototype persistence mismatch: ${beforeReload} before, ${afterReload} after`);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw new Error("Prototype has page-level horizontal overflow at mobile width");
  await page.screenshot({ path: fileURLToPath(new URL("react-prototype-mobile.png", output)) });
  console.log(`Prototype: ${afterReload} graph nodes saved and reopened`);
}

async function verifyMobileLayouts() {
  console.log("Mobile: checking both clients at 390x844");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [name, url] of [["html", "http://127.0.0.1:8765"], ["react", "http://127.0.0.1:5173"]]) {
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { name: /detected devices and interfaces/i }).waitFor();
    if (name === "html") await page.waitForFunction(() => !document.querySelector("#ports-body")?.textContent?.includes("Loading"));
    else await page.getByText(/selectable interfaces found/i).waitFor();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    if (overflow) throw new Error(`${name} client has page-level horizontal overflow at mobile width`);
    await page.screenshot({ path: fileURLToPath(new URL(`${name}-mobile.png`, output)) });
  }
  console.log("Mobile: both layouts passed");
}

try {
  const target = process.argv[2] || "all";
  if (target === "all" || target === "html") await verifyHtmlClient();
  if (target === "all" || target === "react") await verifyReactClient();
  if (target === "all" || target === "prototype") await verifyPrototype();
  if (target === "all" || target === "mobile") await verifyMobileLayouts();
  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log(`VERIFY_OK: ${target} client verification completed without browser errors.`);
} finally {
  await browser.close();
}
