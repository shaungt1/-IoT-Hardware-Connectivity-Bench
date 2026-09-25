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
  await page.locator("tbody tr").filter({ hasText: /(Seeed Studio XIAO ESP32-S3 Sense|Espressif ESP32 USB JTAG\/serial family)/i }).first().click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.getByRole("heading", { name: /device identity and capabilities/i }).waitFor();
  await page.locator(".workflow button", { hasText: "Prototype" }).click();
  await page.getByRole("heading", { name: /prototype/i }).waitFor();
  await page.getByText("Wokwi Elements ready", { exact: true }).waitFor();
  await page.getByText("ngspice installed", { exact: true }).waitFor();
  await page.getByText("Renode installed; platform required", { exact: true }).waitFor();
  await page.getByRole("button", { name: /Run SPICE/i }).waitFor();
  await page.locator('[data-board-model="seeed-xiao-esp32s3-sense"]').first().waitFor();
  const boardRendered = await page.locator('[data-board-model="seeed-xiao-esp32s3-sense"] img').first().evaluate((element) => {
    const box = element.getBoundingClientRect();
    return box.width > 40 && box.height > 40;
  });
  if (!boardRendered) throw new Error("The exact XIAO ESP32-S3 Sense visual did not render meaningful pixels");
  const catalogParts = await page.locator(".catalog-group > button[data-component-id]").count();
  if (catalogParts !== 51) throw new Error(`Expected the exact XIAO visual plus all 50 installed Wokwi elements, found ${catalogParts} parts`);
  const wokwiCatalogParts = await page.locator('.catalog-group > button[data-component-id^="wokwi-"]').count();
  if (wokwiCatalogParts !== 50) throw new Error(`Expected all 50 installed Wokwi element tags, found ${wokwiCatalogParts}`);
  if (await page.locator(".prototype-canvas wokwi-dht22").count() === 0) {
    await page.getByRole("button", { name: /DHT22/i }).click();
  }
  if (await page.locator(".prototype-canvas wokwi-led").count() === 0) {
    await page.locator('.catalog-group > button[data-component-id="wokwi-led"]').click();
  }
  await page.locator(".prototype-canvas wokwi-dht22").first().waitFor();
  await page.locator(".prototype-canvas wokwi-led").last().waitFor();
  const pinCount = await page.locator('.prototype-node.mode-physical[data-component-id="seeed_xiao_esp32s3_sense"] .react-flow__handle').count();
  if (pinCount !== 14) throw new Error(`Expected the exact 14-pad XIAO pin map, found ${pinCount} handles`);
  if (await page.getByText(/representative esp32/i).count()) throw new Error("A representative ESP32 fallback is still being shown for the inspected XIAO board");
  const existingEdges = await page.locator(".react-flow__edge").count();
  if (existingEdges === 0) {
    const source = page.locator('[data-id="selected-controller"] [data-handleid="D4"]').first();
    const target = page.locator('[data-id^="wokwi-dht22-"] [data-handleid="SDA/DATA"]').first();
    const sourceBox = await source.boundingBox();
    const targetBox = await target.boundingBox();
    if (!sourceBox || !targetBox) throw new Error("Could not locate the XIAO D4 and DHT22 data connection handles");
    await page.mouse.move(sourceBox.x + sourceBox.width / 2, sourceBox.y + sourceBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, { steps: 12 });
    await page.mouse.up();
    await page.locator(".react-flow__edge").first().waitFor();
  }
  await page.getByRole("button", { name: /save circuit/i }).click();
  await page.getByText(/Saved \d+ part\(s\)/i).waitFor();
  await page.screenshot({ path: fileURLToPath(new URL("react-prototype-studio.png", output)), fullPage: true });

  // Exercise a controlled simulated path before filling the canvas for the catalog audit.
  await page.getByRole("button", { name: /DHT22/i }).click();
  await page.locator('.catalog-group > button[data-component-id="wokwi-led"]').click();
  const simulatedSensor = page.locator('[data-id^="wokwi-dht22-"]').last();
  const simulatedLed = page.locator('[data-id^="wokwi-led-"]').last();
  const sensorHandle = simulatedSensor.locator('[data-handleid="SDA"]').first();
  const ledHandle = simulatedLed.locator('[data-handleid="A"]').first();
  await sensorHandle.waitFor();
  await ledHandle.waitFor();
  await page.waitForTimeout(300);
  const sensorBox = await sensorHandle.boundingBox();
  const ledBox = await ledHandle.boundingBox();
  if (!sensorBox || !ledBox) throw new Error("Could not locate simulated sensor and LED terminals");
  const edgeCount = await page.locator(".react-flow__edge").count();
  await page.mouse.move(sensorBox.x + sensorBox.width / 2, sensorBox.y + sensorBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(ledBox.x + ledBox.width / 2, ledBox.y + ledBox.height / 2, { steps: 12 });
  await page.mouse.up();
  await page.waitForFunction((count) => document.querySelectorAll(".react-flow__edge").length > count, edgeCount);
  await simulatedSensor.getByRole("slider").fill("75");
  await page.getByText(/propagated to [1-9]\d* connected simulated part/i).waitFor();
  await simulatedLed.locator(".prototype-node").click({ force: true });
  await page.getByText("Simulated output", { exact: true }).waitFor();
  await page.getByText("On", { exact: true }).last().waitFor();

  const terminalAudit = [];
  for (const button of await page.locator(".catalog-group > button[data-component-id]").all()) {
    const componentId = await button.getAttribute("data-component-id");
    await button.click();
    const node = page.locator(`.prototype-node[data-component-id="${componentId}"]`).last();
    await node.waitFor();
    await page.waitForFunction((id) => {
      const item = [...document.querySelectorAll(`.prototype-node[data-component-id="${id}"]`)].at(-1);
      const expected = Number(item?.getAttribute("data-schema-terminal-count") || 0);
      return Boolean(item && item.querySelectorAll(".react-flow__handle").length === expected);
    }, componentId, { timeout: 5_000 });
    const expected = Number(await node.getAttribute("data-schema-terminal-count"));
    const actual = await node.locator(".react-flow__handle").count();
    terminalAudit.push(`${componentId}:${actual}/${expected}`);
    if (actual !== expected) throw new Error(`${componentId} exposes ${actual} connection points for ${expected} schema terminals`);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw new Error("Prototype Studio causes page-level horizontal overflow on mobile");
  await page.screenshot({ path: fileURLToPath(new URL("react-prototype-studio-mobile.png", output)), fullPage: true });
  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log(`VERIFY_OK: ${catalogParts} packaged electronics parts, every catalog terminal (${terminalAudit.join(", ")}), exact XIAO Sense visual, real sensor wiring, persistence, ngspice/Renode controls, and mobile layout passed.`);
} catch (error) {
  console.error("VERIFY_FAILURE", error.message, errors.join(" | "));
  console.error((await page.locator("body").innerText()).slice(0, 5000));
  await page.screenshot({ path: fileURLToPath(new URL("react-prototype-studio-error.png", output)), fullPage: true });
  throw error;
} finally {
  await browser.close();
}
