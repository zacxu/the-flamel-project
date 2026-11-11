/** Adversarial local fixtures for the actual publication guard; no hosting access. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { WEBSITE, describeFile, filesBelow, mimeType, sha256 } from '../../scripts/release-utils.mjs';
import { STABLE_URL, ACCEPTED_POLICY_SHA256, verifyPublication, stagePublication } from './prepare-publication.mjs';

const fixtureParent = await fs.mkdtemp(path.join(os.tmpdir(), 'flamel-publication-'));
const policyBytes = await fs.readFile(path.join(WEBSITE, 'deployment/cache-fix/.htaccess'));
const results = [];
async function check(name, action) { await action(); results.push(name); }
async function write(root, relative, bytes) {
  const target = path.join(root, relative);
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.writeFile(target, bytes);
}
async function fixture(name, digit) {
  const websiteRoot = path.join(fixtureParent, name);
  const identity = { uiBuildId: `ui-w6-${digit.repeat(20)}`, sourceFingerprint: digit.repeat(64), dataReleaseId: 'data-v1-fixture', exportManifestSha256: 'f'.repeat(64) };
  const js = `assets/index-${digit}.js`;
  const css = `assets/index-${digit}.css`;
  await write(websiteRoot, 'deployment/cache-fix/.htaccess', policyBytes);
  await write(websiteRoot, `dist/${js}`, `document.body.dataset.uiBuild = "${identity.uiBuildId}";\n`);
  await write(websiteRoot, `dist/${css}`, 'body{color:#213744}\n');
  await write(websiteRoot, 'dist/index.html', `<!doctype html><title>Fixture ${digit}</title><script type="module" src="./${js}"></script><link rel="stylesheet" href="./${css}">\n`);
  await write(websiteRoot, 'dist/research/manifest.json', `${JSON.stringify({ dataReleaseId: identity.dataReleaseId })}\n`);
  const dist = path.join(websiteRoot, 'dist');
  const runtime = await Promise.all((await filesBelow(dist)).map(relative => describeFile(dist, relative)));
  const quote = value => `"${String(value).replaceAll('"', '""')}"`;
  const csv = `path,bytes,sha256,media_type\n${runtime.map(row => [row.path, row.bytes, row.sha256, mimeType(row.path)].map(quote).join(',')).join('\n')}\n`;
  const inventoryPath = `release-manifests/${identity.uiBuildId}.files.csv`;
  await write(websiteRoot, `dist/${inventoryPath}`, csv);
  const manifestPath = `release-manifests/${identity.uiBuildId}.json`;
  const manifest = { ...identity, payloadInventory: inventoryPath, files: [...runtime, await describeFile(dist, inventoryPath)] };
  await write(websiteRoot, `dist/${manifestPath}`, `${JSON.stringify(manifest, null, 2)}\n`);
  const files = await Promise.all((await filesBelow(dist)).map(relative => describeFile(dist, relative)));
  const packageRelative = 'reports/release.json';
  const record = { ...identity, payload: 'dist/', manifestPath, manifestSha256: sha256(await fs.readFile(path.join(dist, manifestPath))), files, fileCount: files.length, totalBytes: files.reduce((sum, row) => sum + row.bytes, 0) };
  await write(websiteRoot, packageRelative, `${JSON.stringify(record, null, 2)}\n`);
  return { websiteRoot, identity, packageRelative, js, css, record };
}
try {
  const first = await fixture('release-one', 'a');
  const second = await fixture('release-two', 'b');
  let firstVerified;
  let secondVerified;
  await check('Two successive built releases pass the same publication gate', async () => {
    firstVerified = await verifyPublication(first);
    secondVerified = await verifyPublication(second);
    assert.equal(firstVerified.plan.stableUrl, STABLE_URL);
    assert.equal(secondVerified.plan.stableUrl, firstVerified.plan.stableUrl);
    assert.equal(firstVerified.plan.entryTarget, 'index.html');
    assert.equal(secondVerified.plan.entryTarget, firstVerified.plan.entryTarget);
    assert.ok(!firstVerified.entryBytes.equals(secondVerified.entryBytes));
    assert.ok(firstVerified.policyBytes.equals(secondVerified.policyBytes));
    assert.equal(sha256(secondVerified.policyBytes), ACCEPTED_POLICY_SHA256);
  });
  await check('Each staged release contains its own exact current entry behind the same stable link', async () => {
    for (const [current, verified] of [[first, firstVerified], [second, secondVerified]]) {
      const stage = await stagePublication(verified, current);
      assert.equal(stage.reused, false);
      assert.ok((await fs.readFile(path.join(current.websiteRoot, stage.path, 'entry-last/index.html'))).equals(verified.entryBytes));
      assert.ok((await fs.readFile(path.join(current.websiteRoot, stage.path, 'host/.htaccess'))).equals(policyBytes));
      const plan = JSON.parse(await fs.readFile(path.join(current.websiteRoot, stage.path, 'upload-plan.json'), 'utf8'));
      assert.equal(plan.uiBuildId, current.identity.uiBuildId);
      assert.equal(plan.stableUrl, STABLE_URL);
    }
  });
  await check('Research discovery pointers are mutable while versioned application assets remain immutable', async () => {
    assert.ok(secondVerified.plan.mutableFilesBeforeEntry.some(row => row.path === 'research/manifest.json'));
    assert.ok(!secondVerified.plan.immutableFiles.some(row => row.path === 'research/manifest.json'));
    assert.ok(secondVerified.plan.immutableFiles.some(row => row.path === second.js));
    assert.ok(secondVerified.plan.immutableFiles.some(row => row.path === second.css));
    assert.ok(!secondVerified.plan.mutableFilesBeforeEntry.some(row => row.path.startsWith('assets/')));
    assert.equal(secondVerified.plan.filesBeforeEntry.length, secondVerified.plan.immutableFiles.length + secondVerified.plan.mutableFilesBeforeEntry.length);
  });
  await check('An identical existing stage can be reused without replacement', async () => {
    assert.equal((await stagePublication(secondVerified, second)).reused, true);
  });
  await check('A changed existing stage is rejected and is not overwritten', async () => {
    const stagePath = path.join(second.websiteRoot, 'deployment/latest-link/staged', second.identity.uiBuildId, 'entry-last/index.html');
    await fs.writeFile(stagePath, 'unrelated existing file');
    await assert.rejects(() => stagePublication(secondVerified, second), /Existing stage differs/);
    assert.equal(await fs.readFile(stagePath, 'utf8'), 'unrelated existing file');
  });
  await check('A previous UI package cannot be published against a newer prepared identity', async () => {
    await assert.rejects(() => verifyPublication({ ...first, identity: second.identity }), /Package UI is stale/);
  });
  await check('An older copied entry is rejected', async () => {
    const current = await fixture('old-entry', 'c');
    await fs.writeFile(path.join(current.websiteRoot, 'dist/index.html'), firstVerified.entryBytes);
    await assert.rejects(() => verifyPublication(current), /Current dist versus package\/index\.html/);
  });
  await check('A missing entry asset is rejected', async () => {
    const current = await fixture('missing-asset', 'd');
    await fs.unlink(path.join(current.websiteRoot, 'dist', current.js));
    await assert.rejects(() => verifyPublication(current), /Current dist versus package: file count differs/);
  });
  await check('Same-size altered asset bytes are rejected by hash', async () => {
    const current = await fixture('altered-asset', 'e');
    const file = path.join(current.websiteRoot, 'dist', current.css);
    const old = await fs.readFile(file);
    await fs.writeFile(file, Buffer.from(old.toString('utf8').replace('#213744', '#213745')));
    assert.equal((await fs.stat(file)).size, old.length);
    await assert.rejects(() => verifyPublication(current), /hash differs/);
  });
  await check('The historical 230-byte image-only policy is rejected', async () => {
    const current = await fixture('old-policy', '1');
    const old = await fs.readFile(path.join(WEBSITE, 'deployment/root-image-adapter/.htaccess'));
    assert.equal(old.length, 230);
    await fs.writeFile(path.join(current.websiteRoot, 'deployment/cache-fix/.htaccess'), old);
    await assert.rejects(() => verifyPublication(current), /Root configuration differs/);
  });
  await check('Repackaging old JavaScript with new metadata still fails the built identity check', async () => {
    const current = await fixture('old-javascript', '2');
    const wrongText = `document.body.dataset.uiBuild = "${first.identity.uiBuildId}";\n`;
    await fs.writeFile(path.join(current.websiteRoot, 'dist', current.js), wrongText);
    // Rebind all inventories as a packager might, while leaving the wrong built code.
    const dist = path.join(current.websiteRoot, 'dist');
    const runtime = await Promise.all((await filesBelow(dist)).filter(file => !file.startsWith('release-manifests/')).map(file => describeFile(dist, file)));
    const inventoryPath = `release-manifests/${current.identity.uiBuildId}.files.csv`;
    const quote = value => `"${String(value).replaceAll('"', '""')}"`;
    await fs.writeFile(path.join(dist, inventoryPath), `path,bytes,sha256,media_type\n${runtime.map(row => [row.path, row.bytes, row.sha256, mimeType(row.path)].map(quote).join(',')).join('\n')}\n`);
    const manifest = { ...current.identity, payloadInventory: inventoryPath, files: [...runtime, await describeFile(dist, inventoryPath)] };
    await fs.writeFile(path.join(dist, current.record.manifestPath), `${JSON.stringify(manifest, null, 2)}\n`);
    const files = await Promise.all((await filesBelow(dist)).map(file => describeFile(dist, file)));
    const record = { ...current.record, files, totalBytes: files.reduce((sum, row) => sum + row.bytes, 0), manifestSha256: sha256(await fs.readFile(path.join(dist, current.record.manifestPath))) };
    await fs.writeFile(path.join(current.websiteRoot, current.packageRelative), JSON.stringify(record));
    await assert.rejects(() => verifyPublication(current), /Entry JavaScript does not contain the prepared UI identity/);
  });
  console.log(JSON.stringify({ status: 'passed', scenarios: results.length, results, scope: 'Actual guard functions with temporary filesystem fixtures; no claim of Apache or browser cache simulation.' }, null, 2));
} finally {
  // The only recursive deletion is this exact newly-created test directory inside os.tmpdir().
  const resolved = path.resolve(fixtureParent);
  const allowedParent = `${path.resolve(os.tmpdir())}${path.sep}`;
  assert.ok(resolved.startsWith(allowedParent) && path.basename(resolved).startsWith('flamel-publication-'), 'Refuse cleanup outside this test fixture');
  await fs.rm(resolved, { recursive: true, force: true });
}
