import { chromium } from "@playwright/test";
import { execFile } from "node:child_process";
import { access, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const run = promisify(execFile);

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
  const workflowLabels = await page.locator(".workflow button strong").allTextContents();
  const expectedWorkflow = ["Host & devices", "Selected device", "Pins & buses", "Connections", "Tests", "Firmware & files", "Prototype", "Tools & sources"];
  if (JSON.stringify(workflowLabels) !== JSON.stringify(expectedWorkflow)) {
    throw new Error(`Workflow order mismatch: ${workflowLabels.join(" > ")}`);
  }
  await page.locator("tbody tr").filter({ hasText: /(Seeed Studio XIAO ESP32-S3 Sense|Espressif ESP32 USB JTAG\/serial family)/i }).first().click();
  await page.getByRole("button", { name: /inspect iot device/i }).click();
  await page.getByRole("heading", { name: /device identity and capabilities/i }).waitFor();
  await page.getByRole("button", { name: /Progressive identification coverage/i }).click();
  await page.getByText(/Discover, identify, decompose, trace, enrich, and verify remain separate/i).waitFor();
  await page.getByText("Decompose", { exact: true }).waitFor();
  await page.getByRole("button", { name: /Hardware trace coverage/i }).click();
  await page.getByText("Processor / MCU / SoC", { exact: true }).waitFor();
  await page.getByText(/USB alone cannot reveal unexposed passives/i).waitFor();
  const ocrImage = join(tmpdir(), "iot-bench-browser-ocr-board.png");
  const python = fileURLToPath(new URL("../../.venv/Scripts/python.exe", import.meta.url));
  await run(python, ["-c", "from PIL import Image,ImageDraw,ImageFont; import sys; im=Image.new('RGB',(1000,320),'white'); d=ImageDraw.Draw(im); f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',100); d.text((25,45),'ESP32-S3',(0,0,0),font=f); d.text((25,175),'SILABS CP2102',(0,0,0),font=f); im.save(sys.argv[1])", ocrImage]);
  await page.locator('input[type="file"][accept*="image/jpeg"]').setInputFiles(ocrImage);
  await page.getByText("ESP32-S3", { exact: true }).last().waitFor({ timeout: 20_000 });
  await page.getByText(/No image bytes were saved/i).waitFor();
  await page.getByRole("button", { name: /MCU, board and design definitions/i }).click();
  await page.getByText("esp32s3.svd", { exact: true }).waitFor();

  await page.locator('.workflow button[title^="Pins & buses:"]').click();
  await page.getByRole("heading", { name: "Probe coverage" }).waitFor();
  await page.getByText("I2C addressed-device scan", { exact: true }).waitFor();
  await page.getByText("Logic-analyzer capture", { exact: true }).waitFor();
  await page.getByText(/Unknown pins and buses are not driven/i).waitFor();
  await page.getByText(/3\.6 V absolute max \| not 5 V tolerant/i).first().waitFor();

  await page.locator('.workflow button[title^="Tools & sources:"]').click();
  await page.getByRole("heading", { name: "Tools and metadata sources" }).waitFor();
  await page.getByText("CircuitPython USB runtime", { exact: true }).waitFor();
  await page.getByText("Espressif ROM target probe", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Scan fixtures", exact: true }).click();
  await page.getByRole("heading", { name: "Connected bench fixtures" }).waitFor();
  await page.getByText(/target wiring not confirmed/i).first().waitFor();
  await page.getByRole("button", { name: "Diagnose ngspice", exact: true }).click();
  await page.getByText("ngspice 46", { exact: true }).waitFor();

  await page.locator('.workflow button[title^="Firmware & files:"]').click();
  await page.getByRole("heading", { name: /Firmware and files for/i }).waitFor();
  await page.getByRole("heading", { name: /Inspect a binary without executing it/i }).waitFor();
  const firmwareInput = page.locator('input[type="file"][accept*=".elf"]');
  await firmwareInput.setInputFiles({
    name: "browser-fixture.bin",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("IOT_BENCH_BROWSER_FIXTURE\0https://example.invalid/firmware"),
  });
  await page.getByText("Never executed", { exact: true }).waitFor();
  await page.getByRole("heading", { name: /Verified virtual board platforms/i }).waitFor();
  await page.getByRole("button", { name: /Verify platform/i }).click();
  await page.getByText(/peripherals loaded/i).waitFor({ timeout: 20_000 });
  const gcc = join(process.env.USERPROFILE || "", ".platformio", "packages", "toolchain-gccarmnoneeabi", "bin", "arm-none-eabi-gcc.exe");
  const guestElf = join(tmpdir(), "iot-bench-browser-cortex-m-guest.elf");
  await access(gcc);
  await run(gcc, [
    "-mcpu=cortex-m4", "-mthumb", "-nostdlib", "-Wl,--build-id=none",
    `-Wl,-T,${fileURLToPath(new URL("../../ai-api/tests/fixtures/cortex_m_guest.ld", import.meta.url))}`,
    "-o", guestElf,
    fileURLToPath(new URL("../../ai-api/tests/fixtures/cortex_m_guest.c", import.meta.url)),
  ]);
  await page.getByLabel("Renode platform").selectOption("arduino_nano_33_ble");
  await firmwareInput.setInputFiles(guestElf);
  await page.getByText("ARM", { exact: true }).waitFor();
  await page.getByRole("button", { name: /Run ELF/i }).click();
  await page.getByText(/guest run complete/i).waitFor({ timeout: 30_000 });
  const started = Date.now();
  await page.getByRole("button", { name: /src\/main.cpp/i }).first().click();
  await page.locator(".monaco-editor").waitFor({ timeout: 10_000 });
  const openMs = Date.now() - started;
  const editorText = await page.locator(".monaco-editor").getAttribute("data-uri");
  await page.screenshot({ path: fileURLToPath(new URL("react-firmware-workspace.png", output)), fullPage: true });

  await page.locator('.workflow button[title^="Tests:"]').click();
  await page.getByRole("heading", { name: /^Tests for /i }).waitFor();
  if (await page.getByRole("heading", { name: "Connections", exact: true }).count()) throw new Error("Wireless controls are still duplicated in Tests");
  const presenceCard = page.locator(".test-card").filter({ hasText: "Verify host connection" });
  await presenceCard.getByRole("button", { name: "Run", exact: true }).click();
  await presenceCard.getByText(/is present at/i).waitFor();
  await page.getByRole("heading", { name: "Recorded test results", exact: true }).waitFor();
  await page.getByText("Passed", { exact: true }).first().waitFor();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON", exact: true }).click();
  const download = await downloadPromise;
  if (!download.suggestedFilename().endsWith("-history.json")) throw new Error("History export filename is not deterministic");
  const persistedIdentifier = await page.evaluate(() => window.localStorage.getItem("iot-bench.selected-id"));
  if (!persistedIdentifier) throw new Error("Selected hardware identifier was not persisted");
  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /^Tests for /i }).waitFor({ timeout: 20_000 });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) throw new Error("Firmware/tests workspace causes page-level horizontal overflow on mobile");
  if (errors.length) throw new Error(`Browser errors: ${errors.join(" | ")}`);
  console.log(`VERIFY_OK: local board-photo OCR, SVD evidence, safe probe matrix, adapter registry, non-executing firmware analysis, browser-driven bounded Renode ELF execution, Monaco source editor, selected-device reload recovery, dedicated Tests stage, and mobile layout passed; firmware open ${openMs} ms${editorText ? ` (${editorText})` : ""}.`);
} finally {
  await browser.close();
}
