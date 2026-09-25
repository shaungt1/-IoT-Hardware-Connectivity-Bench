import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const manifest = JSON.parse(await readFile(new URL("../dist/.vite/manifest.json", import.meta.url), "utf8"));
const entry = Object.values(manifest).find((item) => item.isEntry);
if (!entry?.file) throw new Error("Vite manifest has no application entry");
const entryBytes = (await stat(new URL(`../dist/${entry.file}`, import.meta.url))).size;
const prototype = Object.entries(manifest).find(([key]) => key.endsWith("src/PrototypeView.tsx"))?.[1];
if (!prototype?.file || !prototype.isDynamicEntry) {
  throw new Error("Prototype workspace is not emitted as a lazy dynamic entry");
}
const editor = Object.entries(manifest).find(([key]) => key.includes("@monaco-editor/react"))?.[1];
if (!editor?.file || !editor.isDynamicEntry) {
  throw new Error("Monaco editor is not emitted as a lazy dynamic entry");
}
const maximumEntryBytes = 500_000;
if (entryBytes > maximumEntryBytes) {
  throw new Error(`Initial JavaScript entry is ${entryBytes} bytes; budget is ${maximumEntryBytes}`);
}
console.log(
  `BUNDLE_OK: initial entry ${entryBytes} bytes; prototype ${prototype.file}; editor ${editor.file}; both lazy`,
);
