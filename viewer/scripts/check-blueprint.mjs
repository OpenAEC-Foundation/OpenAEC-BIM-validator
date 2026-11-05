import { readFileSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
const root = fileURLToPath(new URL("../../", import.meta.url));
const manifest = JSON.parse(readFileSync(resolve(root, "viewer/vendor/blueprint-source.json"), "utf8"));
for (const [name, expected] of Object.entries({ ...manifest.files, ...manifest.generatedFiles })) {
  const actual = createHash("sha256").update(readFileSync(resolve(root, name))).digest("hex");
  if (actual !== expected) throw new Error(`Blueprint source changed without provenance update: ${name}`);
}
const tokens = readFileSync(resolve(root, "viewer/vendor/openaec-web/openaec-tokens.css"), "utf8");
const defined = new Set(Array.from(tokens.matchAll(/(--oa-[\w-]+)\s*:/g), match => match[1]));
function check(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) { check(path); continue; }
    if (!/\.(css|tsx?|json)$/.test(path)) continue;
    const source = readFileSync(path, "utf8");
    if (/var\(--(?:theme|color)-/.test(source)) throw new Error(`Legacy design tokens: ${path}`);
    for (const [, token] of source.matchAll(/var\((--oa-[\w-]+)/g)) if (!defined.has(token)) throw new Error(`Unknown Blueprint token ${token}: ${path}`);
  }
}
check(resolve(root, "viewer/src"));
console.log(`Blueprint ${manifest.revision}: sources, generated sprite and design tokens verified.`);
