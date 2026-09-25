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
  const target = page.locator("tbody tr").filter({ hasText: /Great Scott Gadgets HackRF One/i }).first();
  await target.waitFor({ timeout: 15_000 });
  await target.click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.getByRole("heading", { name: /device identity and capabilities/i }).waitFor({ timeout: 20_000 });

  const selectedPanel = page.getByRole("complementary", { name: /selected hardware live status/i });
  await selectedPanel.waitFor();
  const unsupportedRadios = selectedPanel.locator('.radio-channel[aria-disabled="true"]');
  if (await unsupportedRadios.count() !== 2) throw new Error("Unsupported BLE and Wi-Fi states were not both disabled");
  await selectedPanel.getByText("Unavailable on selected hardware", { exact: true }).first().waitFor();
  await page.getByText("No camera detected for selected hardware", { exact: true }).waitFor();

  await page.locator('.workflow button[title^="Pins & buses:"]').click();
  await page.getByRole("heading", { name: "Probe coverage", exact: true }).waitFor();
  await page.getByText("86 pins", { exact: true }).first().waitFor();
  await page.getByRole("button", { name: "Record attachment", exact: true }).first().click();
  await page.getByRole("dialog", { name: /Attachment on /i }).waitFor();
  await page.getByText(/never presented as an automatic electrical detection/i).waitFor();
  await page.getByRole("button", { name: "Close attachment editor", exact: true }).click();

  await page.locator('.workflow button[title^="Connections:"]').click();
  await page.getByRole("heading", { name: "Connections", exact: true }).waitFor();
  await page.getByText("No wireless capability was identified", { exact: true }).waitFor();
  const radioButtons = page.getByRole("tablist", { name: "Wireless connection" }).getByRole("button");
  if (await radioButtons.count() !== 2 || !(await radioButtons.nth(0).isDisabled()) || !(await radioButtons.nth(1).isDisabled())) {
    throw new Error("Unsupported wireless controls were interactive");
  }

  await page.getByRole("button", { name: /Diagnostic console/i }).click();
  const profile = page.getByLabel("Read-only target diagnostic profile");
  await profile.waitFor();
  if (await profile.isDisabled()) throw new Error("Safe diagnostic profiles were not available for the connected target");
  await page.getByRole("button", { name: "Run profile", exact: true }).click();
  await page.locator('.console-output [class="ok"]').last().waitFor({ timeout: 15_000 });

  await page.screenshot({ path: fileURLToPath(new URL("react-phase-one-hackrf.png", output)), fullPage: true });
  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log("VERIFY_OK: live HackRF inspection, unavailable camera/radios, disabled wireless controls, mapped pins, declared-evidence form, and safe diagnostic profile passed.");
} finally {
  await browser.close();
}
