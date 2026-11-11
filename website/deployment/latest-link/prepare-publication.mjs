/** Read-only publication gate by default. Does not build, upload or access hosting. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WEBSITE, assertPrepared, describeFile, filesBelow, mimeType, sha256 } from '../../scripts/release-utils.mjs';

export const STABLE_URL = 'https://theflamelproject.42web.io/refresh';
export const ACCEPTED_POLICY_SHA256 = 'cfec2cddb8cbbf215fbe2ee17593a20f8b470d80071648ddb6d79004a8bbd149';
const POLICY_PATH = 'deployment/cache-fix/.htaccess';

function inside(root, relative) {
  assert.equal(typeof relative, 'string', 'A document-root-relative path is required');
  assert.ok(relative.length > 0 && !relative.includes('\\') && !path.isAbsolute(relative), `Unsafe relative path: ${relative}`);
  assert.ok(!relative.split('/').some(part => !part || part === '.' || part === '..'), `Unsafe relative path: ${relative}`);
  const resolved = path.resolve(root, relative);
  assert.ok(resolved.startsWith(`${path.resolve(root)}${path.sep}`), `Path escapes its root: ${relative}`);
  return resolved;
}
function inventory(rows, label) {
  assert.ok(Array.isArray(rows), `${label} must be a file inventory`);
  const result = new Map();
  for (const row of rows) {
    inside(WEBSITE, row.path);
    assert.ok(!result.has(row.path), `${label} duplicates ${row.path}`);
    assert.ok(Number.isSafeInteger(row.bytes) && row.bytes >= 0 && /^[a-f0-9]{64}$/.test(row.sha256), `${label} has invalid metadata: ${row.path}`);
    result.set(row.path, row);
  }
  return result;
}
function sameFile(actual, expected, label) {
  assert.ok(expected, `${label}: file is not inventoried`);
  assert.equal(actual.bytes, expected.bytes, `${label}: byte count differs`);
  assert.equal(actual.sha256, expected.sha256, `${label}: hash differs`);
}
function compareInventory(actual, expected, label) {
  assert.equal(actual.size, expected.size, `${label}: file count differs`);
  for (const [name, row] of actual) sameFile(row, expected.get(name), `${label}/${name}`);
}
export function stableEntryTarget(policyBytes) {
  assert.equal(sha256(policyBytes), ACCEPTED_POLICY_SHA256, 'Root configuration differs from the accepted latest-link/cache/image policy');
  const target = policyBytes.toString('utf8').match(/^RewriteRule \^refresh\$ ([^\s]+) \[L\]$/m)?.[1];
  assert.equal(target, 'index.html', 'The stable URL must target the mutable current entry');
  return target;
}

/** identity must come from assertPrepared() in production; fixtures supply their own built identity. */
export async function verifyPublication({ websiteRoot = WEBSITE, identity, packageRelative }) {
  assert.ok(identity && /^ui-w6-[a-f0-9]{20}$/.test(identity.uiBuildId), 'A valid prepared UI identity is required');
  const packagePath = inside(websiteRoot, packageRelative);
  const packageBytes = await fs.readFile(packagePath);
  const record = JSON.parse(packageBytes);
  assert.equal(record.uiBuildId, identity.uiBuildId, 'Package UI is stale relative to the prepared source');
  assert.equal(record.sourceFingerprint, identity.sourceFingerprint, 'Package fingerprint differs from the prepared source');
  assert.equal(record.dataReleaseId, identity.dataReleaseId, 'Package data release differs from the prepared source');
  assert.equal(record.exportManifestSha256, identity.exportManifestSha256, 'Package research manifest differs from the prepared source');
  assert.equal(record.payload, 'dist/', 'Only the current dist/ payload is publishable');
  const dist = inside(websiteRoot, 'dist');
  const names = await filesBelow(dist);
  const rows = await Promise.all(names.map(relative => describeFile(dist, relative)));
  const actual = inventory(rows, 'Current dist');
  const packaged = inventory(record.files, 'Package');
  compareInventory(actual, packaged, 'Current dist versus package');
  assert.equal(record.fileCount, rows.length, 'Package total file count differs');
  assert.equal(record.totalBytes, rows.reduce((sum, row) => sum + row.bytes, 0), 'Package total bytes differ');
  assert.equal(record.manifestPath, `release-manifests/${identity.uiBuildId}.json`, 'Release manifest path is not the prepared UI');
  const manifestBytes = await fs.readFile(inside(dist, record.manifestPath));
  assert.equal(sha256(manifestBytes), record.manifestSha256, 'Release manifest is not bound to the package');
  const manifest = JSON.parse(manifestBytes);
  for (const key of ['uiBuildId', 'sourceFingerprint', 'dataReleaseId', 'exportManifestSha256']) {
    assert.equal(manifest[key], identity[key], `Manifest ${key} differs from the prepared source`);
  }
  const payload = inventory(manifest.files, 'Manifest');
  compareInventory(new Map([...actual].filter(([name]) => name !== record.manifestPath)), payload, 'Dist versus manifest');
  assert.equal(manifest.payloadInventory, `release-manifests/${identity.uiBuildId}.files.csv`, 'Runtime inventory is not the prepared UI');
  assert.deepEqual(names.filter(name => name.startsWith('release-manifests/')).sort(), [manifest.payloadInventory, record.manifestPath].sort(), 'Only this release manifest and runtime inventory may be present');
  const runtime = rows.filter(row => !row.path.startsWith('release-manifests/'));
  const quote = value => `"${String(value).replaceAll('"', '""')}"`;
  const expectedCsv = `path,bytes,sha256,media_type\n${runtime.map(row => [row.path, row.bytes, row.sha256, mimeType(row.path)].map(quote).join(',')).join('\n')}\n`;
  assert.equal(await fs.readFile(inside(dist, manifest.payloadInventory), 'utf8'), expectedCsv, 'Runtime CSV does not inventory the exact current payload');
  const policyBytes = await fs.readFile(inside(websiteRoot, POLICY_PATH));
  const entryTarget = stableEntryTarget(policyBytes);
  const entryBytes = await fs.readFile(inside(dist, entryTarget));
  const entryText = entryBytes.toString('utf8');
  const entryAssets = [...entryText.matchAll(/(?:src|href)=["']\.\/((?:assets\/)[^"'?#]+\.(?:js|css))["']/g)].map(match => match[1]);
  assert.ok(entryAssets.some(name => name.endsWith('.js')) && entryAssets.some(name => name.endsWith('.css')), 'Entry must reference local built JavaScript and CSS');
  for (const name of entryAssets) assert.ok(actual.has(name), `Entry references a missing asset: ${name}`);
  const directJavaScript = await Promise.all(entryAssets.filter(name => name.endsWith('.js')).map(name => fs.readFile(inside(dist, name), 'utf8')));
  assert.ok(directJavaScript.some(text => text.includes(identity.uiBuildId)), 'Entry JavaScript does not contain the prepared UI identity');
  // Follow the same emitted local JS/CSS path forms used by the release integrity gate.
  let emittedReferences = 0;
  for (const row of runtime.filter(file => /\.(?:html|js|css)$/.test(file.path))) {
    const text = await fs.readFile(inside(dist, row.path), 'utf8');
    for (const match of text.matchAll(/(?:["'(])((?:\.\/?)*(?:assets\/)?[A-Za-z0-9_-]+\.(?:js|css))(?:["')])/g)) {
      const raw = match[1];
      let target = raw.startsWith('assets/') || raw.startsWith('./assets/') ? raw.replace(/^\.\//, '') : path.posix.normalize(path.posix.join(path.posix.dirname(row.path), raw));
      if (!actual.has(target) && actual.has(`assets/${raw.replace(/^\.\//, '')}`)) target = `assets/${raw.replace(/^\.\//, '')}`;
      assert.ok(actual.has(target), `Emitted asset reference is missing: ${row.path} -> ${target}`);
      emittedReferences += 1;
    }
  }
  const beforeEntry = rows.filter(row => row.path !== entryTarget);
  const immutablePath = name => /^(?:assets\/|release-manifests\/|research\/releases\/|ui\/figures\/)/.test(name);
  const plan = {
    schemaVersion: 1, status: 'verified_for_manual_publication', stableUrl: STABLE_URL,
    uiBuildId: identity.uiBuildId, sourceFingerprint: identity.sourceFingerprint,
    dataReleaseId: identity.dataReleaseId, packagePath: packageRelative, packageSha256: sha256(packageBytes),
    targetDocumentRoot: '/htdocs', entryTarget,
    policy: { canonicalSource: POLICY_PATH, stagedSource: 'host/.htaccess', remotePath: '/htdocs/.htaccess', bytes: policyBytes.length, sha256: ACCEPTED_POLICY_SHA256 },
    entry: { stagedSource: 'entry-last/index.html', remotePath: '/htdocs/index.html', ...actual.get(entryTarget) },
    manifest: { path: record.manifestPath, sha256: record.manifestSha256 },
    filesBeforeEntry: beforeEntry,
    immutableFiles: beforeEntry.filter(row => immutablePath(row.path)),
    mutableFilesBeforeEntry: beforeEntry.filter(row => !immutablePath(row.path)),
    uploadOrder: [
      'Confirm the authenticated account/domain and /htdocs; preserve current entry, configuration and unknown files.',
      'Verify existing immutableFiles paths and upload only new/missing immutable files from dist. Never replace a versioned path with different bytes. Retain all predecessor assets and research releases.',
      'Publish any changed mutableFilesBeforeEntry pointers (including research/manifest.json) from the verified dist before the entry. Do not skip a changed mutable pointer merely because its path already exists.',
      'Preserve original images and image .bin sidecars/child configuration. Use the accepted image adapter for any genuinely new image; do not re-encode existing scientific images.',
      'Confirm staged host/.htaccess is installed as /htdocs/.htaccess before publishing the entry. Do not restore the historical image-only root policy.',
      'Publish exact staged entry-last/index.html as /htdocs/index.html LAST. Its filename must remain index.html. Do not upload a nested dist directory.',
      `Open ${STABLE_URL} from the actual submission. Verify its live UI identity matches this plan and its entry response is no-store. Confirm the published manifest hash and the browser interface.`,
    ],
    checks: { exactPayloadFiles: rows.length, exactPayloadBytes: record.totalBytes, entryAssets: entryAssets.length, emittedReferences },
    limitation: 'Local integrity gate and staging only. This does not upload, verify current remote bytes/headers, refresh an already-open tab or replace live publication verification.',
  };
  return { plan, entryBytes, policyBytes };
}

export async function stagePublication(verified, { websiteRoot = WEBSITE } = {}) {
  const relative = `deployment/latest-link/staged/${verified.plan.uiBuildId}`;
  const target = inside(websiteRoot, relative);
  const expected = new Map([
    ['host/.htaccess', verified.policyBytes], ['entry-last/index.html', verified.entryBytes],
    ['upload-plan.json', Buffer.from(`${JSON.stringify(verified.plan, null, 2)}\n`)],
  ]);
  await fs.mkdir(path.dirname(target), { recursive: true });
  let created = false;
  try { await fs.mkdir(target); created = true; }
  catch (error) { if (error.code !== 'EEXIST') throw error; }
  if (created) {
    for (const [name, bytes] of expected) {
      await fs.mkdir(path.dirname(path.join(target, name)), { recursive: true });
      await fs.writeFile(path.join(target, name), bytes, { flag: 'wx' });
    }
  } else {
    const found = await filesBelow(target);
    assert.deepEqual(found, [...expected.keys()].sort(), 'Existing stage differs; it will not be overwritten');
    for (const [name, bytes] of expected) assert.ok((await fs.readFile(path.join(target, name))).equals(bytes), `Existing stage differs: ${name}; it will not be overwritten`);
  }
  return { path: relative, reused: !created };
}

async function main() {
  const args = process.argv.slice(2);
  assert.ok(args.every(arg => arg === '--stage' || arg.startsWith('--package=')), 'Usage: node deployment/latest-link/prepare-publication.mjs --package=reports/<current-package>.json [--stage]');
  const packages = args.filter(arg => arg.startsWith('--package='));
  assert.equal(packages.length, 1, 'Pass exactly one explicit --package=reports/<current-package>.json');
  assert.ok(args.filter(arg => arg === '--stage').length <= 1, 'Pass --stage at most once');
  const { identity } = await assertPrepared();
  const result = await verifyPublication({ identity, packageRelative: packages[0].slice('--package='.length) });
  const stage = args.includes('--stage') ? await stagePublication(result) : null;
  console.log(JSON.stringify({ status: 'passed', mode: stage ? 'staged' : 'read_only', uiBuildId: identity.uiBuildId, stableUrl: STABLE_URL, ...result.plan.checks, ...(stage ? { stage } : {}) }, null, 2));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(`Publication guard rejected: ${error.message}`); process.exitCode = 1; });
}
