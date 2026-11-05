/** Collect installed npm and optional Cargo dependency licenses for release bundles. */
import fs from 'node:fs';
import path from 'node:path';

const seen = new Set();
function report(name, version, license, directory) {
  const key = `${name}@${version}`;
  if (seen.has(key)) return;
  seen.add(key);
  console.log(`\n${key}\nLicense: ${typeof license === 'object' ? JSON.stringify(license) : license || 'See package source'}\n`);
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.isFile() && /^(licen[cs]e|copying|notice)([._-]|$)/i.test(entry.name)) {
      console.log(`--- ${entry.name} ---\n${fs.readFileSync(path.join(directory, entry.name), 'utf8')}`);
    }
  }
}

function packages(directory) {
  if (!fs.existsSync(directory)) return;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith('.')) continue;
    const target = path.join(directory, entry.name);
    if (entry.name.startsWith('@')) { packages(target); continue; }
    const manifest = path.join(target, 'package.json');
    if (!fs.existsSync(manifest)) continue;
    const data = JSON.parse(fs.readFileSync(manifest, 'utf8'));
    report(data.name, data.version, data.license || data.licenses, target);
    packages(path.join(target, 'node_modules'));
  }
}

console.log('NPM AND RUST DEPENDENCY NOTICES\nGenerated from installed build dependencies.');
packages(process.argv[2] || 'viewer/node_modules');
if (process.argv[3]) {
  const metadata = JSON.parse(fs.readFileSync(process.argv[3], 'utf8').replace(/^\uFEFF/, ''));
  for (const pkg of metadata.packages) {
    report(pkg.name, pkg.version, pkg.license, path.dirname(pkg.manifest_path));
  }
}
