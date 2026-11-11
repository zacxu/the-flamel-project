/** Exercise the actual browser data loader against an ephemeral local server.
 * This checks the cache/integrity boundary, not UI interactions scheduled later.
 */
const phase = process.argv.includes('--phase=W6') ? 'W6' : 'W1';

import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Node 24 executes the erasable TypeScript directly, so this exercises the
// shipped loader source without a second compiler or a test copy.
const { ResearchRelease } = await import(pathToFileURL(path.join(website, 'src', 'data', 'loadRelease.ts')));
const manifest = JSON.parse(await fs.readFile(path.join(website, 'public', 'research', 'manifest.json')));
let mode = 'valid';
let mutableRequests = 0;
const checks = [];
function check(name, passed) { assert.ok(passed, name); checks.push({ check: name, passed: true }); }
const server = http.createServer(async (request, response) => {
  try {
    const pathname = new URL(request.url, 'http://127.0.0.1').pathname.replace(/^\/nested\//, '/');
    if (pathname === '/research/manifest.json') {
      mutableRequests++;
      response.writeHead(500); response.end('Mutable pointer must never be fetched'); return;
    }
    const publicRoot = path.join(website, 'public');
    const target = path.resolve(publicRoot, '.' + pathname);
    if (!target.startsWith(publicRoot + path.sep)) throw new Error('Out of root');
    let bytes = await fs.readFile(target);
    if ((mode === 'corrupt-manifest' && pathname.endsWith('/manifest.json')) ||
        (mode === 'corrupt-data' && pathname.includes('/summary.'))) {
      bytes = Buffer.from(bytes); bytes[bytes.length - 2] ^= 1;
    }
    response.writeHead(200); response.end(bytes);
  } catch {
    response.writeHead(404); response.end('Unavailable');
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
try {
  const address = server.address();
  const base = new URL(`http://127.0.0.1:${address.port}/nested/`);
  const release = new ResearchRelease(base);
  check('Pinned immutable manifest loads under a nested static base',
    (await release.manifest()).dataReleaseId === manifest.dataReleaseId);
  const summary = await release.dataset('summary.json');
  check('Actual summary identity and closed-study flag load', summary.studyId === manifest.studyId &&
    summary.newStableMaterialEstablished === false);
  check('Dataset request is cached within this pinned instance',
    await release.dataset('summary.json') === summary);
  const png = await release.asset('figures/structures.png');
  check('Actual PNG bytes pass the loader hash check', png.type === 'image/png' && png.size > 1000);
  const figure = manifest.files.find((entry) => entry.logicalName === 'figures/structures.png');
  check('Loaded PNG hash matches offline manifest', crypto.createHash('sha256')
    .update(Buffer.from(await png.arrayBuffer())).digest('hex') === figure.sha256);
  await assert.rejects(release.dataset('unavailable.json'), /unavailable/);
  check('Missing data fails with an explicit unavailable error', true);
  await assert.rejects(release.dataset('figures/structures.png'), /not a JSON/);
  check('A binary asset cannot be treated as a JSON dataset', true);
  mode = 'corrupt-manifest';
  await assert.rejects(new ResearchRelease(base).manifest(), /integrity mismatch/);
  check('A modified immutable manifest fails closed', true);
  mode = 'corrupt-data';
  await assert.rejects(new ResearchRelease(base).dataset('summary.json'), /integrity mismatch/);
  check('A same-length modified data shard fails closed', true);
  check('Mutable discovery pointer was never requested', mutableRequests === 0);
} finally {
  await new Promise((resolve) => server.close(resolve));
}
const report = { phase, status: 'passed', generatedAt: new Date().toISOString(),
  dataReleaseId: manifest.dataReleaseId, checksPassed: checks.length, checks,
  scope: 'Actual loader through local HTTP; six-view browser/accessibility QA belongs to W2-W6.' };
await fs.writeFile(path.join(website, 'reports', `${phase}_LOADER_VALIDATION.json`), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ status: report.status, checksPassed: checks.length,
  dataReleaseId: manifest.dataReleaseId }));
