import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { copyFile, mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
const phase = process.argv.includes('--phase=W6') ? 'W6' : process.argv.includes('--phase=W5') ? 'W5' : process.argv.includes('--phase=W4') ? 'W4' : process.argv.includes('--phase=W3') ? 'W3' : process.argv.includes('--phase=W2') ? 'W2' : 'W1';
const require = createRequire(import.meta.url);
const semver = require(path.join(root, '.tooling/npm/node_modules/semver'));
const npmCli = path.join(root, '.tooling/npm/bin/npm-cli.js');
const readJson = async (relative) => JSON.parse(await readFile(path.join(root, relative), 'utf8'));
const hash = async (relative) => createHash('sha256').update(await readFile(path.join(root, relative))).digest('hex');
const pkg = await readJson('package.json');
const lock = await readJson('package-lock.json');
const metadata = await readJson('reports/npm_metadata.json');
const checks = [];
function check(name, passed, detail) {
  checks.push({ name, passed: Boolean(passed), detail });
}
check('Node meets the project engine', semver.satisfies(process.version, pkg.engines.node), process.version);
check('lockfile v3', lock.lockfileVersion === 3, lock.lockfileVersion);
const npmVersion = spawnSync(process.execPath, [npmCli, '--version'], { cwd: root, encoding: 'utf8' });
check('workspace npm pin', npmVersion.status === 0 && npmVersion.stdout.trim() === '12.2.1', npmVersion.stdout.trim());
const dependencyNotices = [];
const licenseCopies = [];
async function findLicenses(directory, prefix = '') {
  const found = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const relative = prefix ? path.join(prefix, entry.name) : entry.name;
    if (entry.isDirectory() && entry.name !== 'node_modules' && entry.name !== '.git') {
      found.push(...await findLicenses(path.join(directory, entry.name), relative));
    } else if (entry.isFile() && /^(licen[cs]e|copying|notice)(\.|$|-)/i.test(entry.name)) {
      found.push(relative);
    }
  }
  return found;
}
for (const [name, version] of Object.entries({ ...pkg.dependencies, ...pkg.devDependencies })) {
  const installed = await readJson(`node_modules/${name}/package.json`);
  const declared = metadata.packages.find((entry) => entry.name === name);
  check(`exact installed pin: ${name}`, version === installed.version && declared.version === version, version);
  check(`lock pin: ${name}`, lock.packages[`node_modules/${name}`].version === version, version);
  check(`compatible Node: ${name}`, !declared.engines?.node || semver.satisfies(process.version, declared.engines.node), declared.engines?.node ?? 'no Node engine constraint');
}
const npmTree = spawnSync(process.execPath, [npmCli, 'ls', '--all', '--json'], { cwd: root, encoding: 'utf8' });
check('resolved dependency tree has no missing or invalid packages', npmTree.status === 0, npmTree.stderr.trim() || 'npm ls --all exited 0');
for (const [relative, entry] of Object.entries(lock.packages)) {
  if (!relative) continue;
  const name = entry.name ?? relative.split('node_modules/').at(-1);
  const row = { name, version: entry.version, license: entry.license ?? null, optional: entry.optional === true, development: entry.dev === true, integrity: entry.integrity ?? null };
  dependencyNotices.push(row);
  let files;
  try { files = await findLicenses(path.join(root, relative)); }
  catch (error) { if (error.code === 'ENOENT') continue; throw error; }
  const licenseFiles = [];
  for (const file of files) {
    const directory = path.join(root, 'licenses/dependencies', `${name.replaceAll('@', '').replaceAll('/', '__')}@${entry.version}`, path.dirname(file));
    await mkdir(directory, { recursive: true });
    const target = path.join(directory, path.basename(file));
    await copyFile(path.join(root, relative, file), target);
    licenseFiles.push({ path: path.relative(root, target).replaceAll('\\', '/'), bytes: (await stat(target)).size, sha256: createHash('sha256').update(await readFile(target)).digest('hex') });
  }
  if (name.startsWith('@rolldown/binding-') && licenseFiles.length === 0) {
    const from = path.join(root, 'node_modules/rolldown/LICENSE');
    const directory = path.join(root, 'licenses/dependencies', `${name.replaceAll('@', '').replaceAll('/', '__')}@${entry.version}`);
    await mkdir(directory, { recursive: true });
    const target = path.join(directory, 'LICENSE');
    await copyFile(from, target);
    licenseFiles.push({ path: path.relative(root, target).replaceAll('\\', '/'), copied_from: 'same-version rolldown package LICENSE (native binding package declares MIT but omits its own file)', bytes: (await stat(target)).size, sha256: createHash('sha256').update(await readFile(target)).digest('hex') });
  }
  licenseCopies.push({ ...row, license_files: licenseFiles });
}
await writeFile(path.join(root, phase === 'W6' ? 'reports/W6_DEPENDENCY_LICENSES.json' : 'reports/dependency_licenses.json'), `${JSON.stringify({ source: 'package-lock.json', packages: dependencyNotices }, null, 2)}\n`);
await writeFile(path.join(root, phase === 'W6' ? 'reports/W6_INSTALLED_LICENSES.json' : 'reports/W1_DEPENDENCY_LICENSES.json'), `${JSON.stringify({ source: 'installed package tarballs as resolved by package-lock.json', installed_packages: licenseCopies.length, copied_license_files: licenseCopies.reduce((count, row) => count + row.license_files.length, 0), packages: licenseCopies }, null, 2)}\n`);

if (process.argv.includes('--audit')) {
  const audit = spawnSync(process.execPath, [npmCli, 'audit', '--json'], { cwd: root, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  let parsed;
  try { parsed = JSON.parse(audit.stdout); } catch { throw new Error(`npm audit did not return JSON: ${audit.stderr}`); }
  await writeFile(path.join(root, phase === 'W6' ? 'reports/W6_DEPENDENCY_AUDIT.json' : 'reports/dependency_audit.json'), `${JSON.stringify(parsed, null, 2)}\n`);
  if (parsed.error) throw new Error(`npm audit failed: ${JSON.stringify(parsed.error)}`);
}
let audit;
const auditRelative = phase === 'W6' && process.argv.includes('--audit') ? 'reports/W6_DEPENDENCY_AUDIT.json' : 'reports/dependency_audit.json';
try { audit = await readJson(auditRelative); } catch { audit = null; }
check('registry audit completed', Boolean(audit?.metadata?.vulnerabilities), audit?.metadata?.vulnerabilities ?? 'unavailable');
check('registry audit has zero reported vulnerabilities', audit?.metadata?.vulnerabilities?.total === 0, audit?.metadata?.vulnerabilities ?? 'unavailable');

const buildFiles = [];
async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) await walk(absolute);
    else buildFiles.push({ path: path.relative(path.join(root, 'dist'), absolute).replaceAll('\\', '/'), bytes: (await stat(absolute)).size, sha256: createHash('sha256').update(await readFile(absolute)).digest('hex') });
  }
}
await walk(path.join(root, 'dist'));
check('foundation JS chunks below 900 kB uncompressed', buildFiles.filter((f) => f.path.endsWith('.js')).every((f) => f.bytes < 900_000), buildFiles.filter((f) => f.path.endsWith('.js')));
const researchManifest = await readJson('public/research/manifest.json');
check('production copy has the active research manifest',
  await hash('dist/research/manifest.json') === await hash('public/research/manifest.json'), researchManifest.dataReleaseId);
for (const entry of researchManifest.files) {
  const built = buildFiles.find((file) => file.path === `research/${entry.path}`);
  check(`production research asset: ${entry.logicalName}`,
    built?.sha256 === entry.sha256 && built?.bytes === entry.bytes,
    { dataReleaseId: researchManifest.dataReleaseId, bytes: built?.bytes ?? null });
}
const expectedResearch = new Set(['research/manifest.json',
  `research/releases/${researchManifest.dataReleaseId}/manifest.json`,
  ...researchManifest.files.map((entry) => `research/${entry.path}`)]);
check('production research tree contains only this release',
  buildFiles.filter((file) => file.path.startsWith('research/')).every((file) => expectedResearch.has(file.path)),
  researchManifest.dataReleaseId);
check('production immutable manifest matches the discovery copy',
  await hash(`dist/research/releases/${researchManifest.dataReleaseId}/manifest.json`) === await hash('public/research/manifest.json'),
  researchManifest.dataReleaseId);
const viteCli = path.join(root, 'node_modules/vite/bin/vite.js');
const preview = spawn(process.execPath, [viteCli, 'preview', '--host', '127.0.0.1', '--port', '4177', '--strictPort'], { cwd: root, windowsHide: true, stdio: 'pipe' });
let previewErrors = '';
preview.stderr.on('data', (data) => { previewErrors += data; });
try {
  let response;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try { response = await fetch('http://127.0.0.1:4177/'); break; }
    catch { await new Promise((resolve) => setTimeout(resolve, 100)); }
  }
  if (!response) throw new Error(`Local preview did not start: ${previewErrors}`);
  const html = await response.text();
  check('built entry served over local HTTP', response.ok && html.includes('The Flamel Project'), response.status);
  const match = html.match(/<script[^>]+src="([^"]+)"/);
  check('entry references a built module', Boolean(match), match?.[1] ?? null);
  if (match) {
    const module = await fetch(new URL(match[1], 'http://127.0.0.1:4177/'));
    const text = await module.text();
    check('built module loads over local HTTP', module.ok && text.includes('The Flamel Project'), { status: module.status, bytes: Buffer.byteLength(text) });
  }
} finally {
  preview.kill();
  if (preview.exitCode === null) await new Promise((resolve) => preview.once('exit', resolve));
}

const output = {
  checked_utc: new Date().toISOString(),
  status: checks.every((entry) => entry.passed) ? 'passed' : 'failed',
  node_version: process.version,
  node_executable: process.execPath,
  npm_version: npmVersion.stdout.trim(),
  vite_engine: metadata.packages.find((entry) => entry.name === 'vite').engines.node,
  official_vite_requirements: 'https://vite.dev/guide/',
  direct_dependency_pins: { ...pkg.dependencies, ...pkg.devDependencies },
  package_json_sha256: await hash('package.json'),
  lockfile_sha256: await hash('package-lock.json'),
  installed_resolved_dependency_tree_ok: npmTree.status === 0,
  lockfile_dependency_entries: dependencyNotices.length,
  dependency_audit_vulnerabilities: audit?.metadata?.vulnerabilities ?? null,
  dependency_audit_evidence: { path: auditRelative, sha256: audit ? await hash(auditRelative) : null,
    queriedDuringThisRun: process.argv.includes('--audit'),
    scope: process.argv.includes('--audit') ? 'npm registry audit queried during this tooling run.' : 'Reuses the recorded registry audit for the unchanged locked dependency tree; no fresh security advisory lookup is claimed.' },
  phase,
  build_scope: phase === 'W6' ? 'W6 integrated local production release, guided tour and validation; W7 deployment remains separate.' : phase === 'W5' ? 'W5 generation/uncertainty findings, full DFT/reference ledger, claims/methods and displayed CSVs; W6-W7 remain separate.' : phase === 'W4' ? 'W4 interactive saved-structure viewer, catalog, comparison and CIF export; W5-W7 remain separate.' : phase === 'W3' ? 'W3 recorded acquisition replay, charts, batch teaching and CSV exports; W4-W7 remain separate.' : phase === 'W2' ? 'W2 six-view shell and real-data previews; W3-W7 interactions/release/deployment remain separate.' : 'W1 foundation smoke entry only; not the W2-W6 website or a deployed release.',
  data_release_id: researchManifest.dataReleaseId,
  data_manifest_sha256: await hash('public/research/manifest.json'),
  build_files: buildFiles,
  checks_passed: checks.filter((entry) => entry.passed).length,
  checks_total: checks.length,
  checks,
};
await writeFile(path.join(root, phase === 'W1' ? 'reports/runtime.json' : `reports/${phase}_TOOLING.json`), `${JSON.stringify(output, null, 2)}\n`);
console.log(JSON.stringify({ status: output.status, checks_passed: output.checks_passed, checks_total: output.checks_total, vulnerabilities: output.dependency_audit_vulnerabilities, build_files: output.build_files }, null, 2));
if (output.status !== 'passed') process.exit(1);
