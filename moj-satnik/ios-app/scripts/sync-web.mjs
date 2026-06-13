// Skopíruje webovú appku (jediný zdroj pravdy v ../) do www/, ktorú balí Capacitor.
// Spúšťa sa automaticky cez `npm run ios:sync` / `ios:add`.
import { mkdirSync, rmSync, cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");           // moj-satnik/ios-app
const src = join(root, "..");            // moj-satnik
const www = join(root, "www");

const FILES = ["index.html", "manifest.webmanifest", "service-worker.js"];
const DIRS = ["icons"];

rmSync(www, { recursive: true, force: true });
mkdirSync(www, { recursive: true });

for (const f of FILES) {
  const from = join(src, f);
  if (!existsSync(from)) throw new Error("Chýba zdrojový súbor: " + from);
  cpSync(from, join(www, f));
}
for (const d of DIRS) {
  const from = join(src, d);
  if (existsSync(from)) cpSync(from, join(www, d), { recursive: true });
}

console.log("✔ www/ pripravené pre Capacitor (z ../).");
