/** W6 static release, size, integrity and predecessor cache-coherence gate.
 * Starts one ephemeral loopback HTTP server, verifies real responses, and stops it.
 * Does not use a browser, access hosting, mutate research, or run any experiment.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { once } from 'node:events';
import { gzipSync } from 'node:zlib';
import { spawnSync } from 'node:child_process';
import { WEBSITE, STUDY, assertPrepared, describeFile, filesBelow, mimeType, readJson, sha256, writeJson } from './release-utils.mjs';

if (process.argv.length > 2) throw new Error('Usage: node scripts/verify-release.mjs');
const checks = [];
function check(name, passed, detail) { checks.push({ name, passed: Boolean(passed), detail }); }
const { identity, inputs } = await assertPrepared();
const baseline = await readJson('reports/W6_BASELINE.json');
const packageRecord = await readJson('reports/W6_RELEASE_PACKAGE.json');
const dist = path.join(WEBSITE, 'dist');
const names = await filesBelow(dist);
const publicResearchNames = await filesBelow(path.join(WEBSITE, 'public/research'));
const manifest = await readJson(`dist/${packageRecord.manifestPath}`);
const manifestEntries = new Map(manifest.files.map((file) => [file.path, file]));
const records = await Promise.all(names.map((file) => describeFile(dist, file)));
const research = await readJson('public/research/manifest.json');
const immutableManifest = `research/releases/${identity.dataReleaseId}/manifest.json`;
const researchManifestPaths = ['manifest.json', `releases/${identity.dataReleaseId}/manifest.json`];
check('Package identity is the prepared current source identity', packageRecord.uiBuildId === identity.uiBuildId && packageRecord.sourceFingerprint === inputs.fingerprint, identity.uiBuildId);
check('Release manifest UI, study and data identities are pinned', manifest.uiBuildId === identity.uiBuildId && manifest.sourceFingerprint === identity.sourceFingerprint && manifest.dataReleaseId === baseline.dataReleaseId && manifest.studyId === identity.studyId && manifest.exportManifestSha256 === baseline.manifestSha256 && manifest.sourceInventorySha256 === research.sourceInventorySha256, identity);
check('Release manifest hash is bound outside the public manifest', sha256(await fs.readFile(path.join(dist, packageRecord.manifestPath))) === packageRecord.manifestSha256, packageRecord.manifestSha256);
check('Self hash is explicitly excluded rather than circular', !manifestEntries.has(packageRecord.manifestPath) && manifest.selfExclusion.includes('excludes its own hash'), manifest.selfExclusion);
check('Exactly one versioned manifest and inventory are present', names.filter((file) => file.startsWith('release-manifests/')).length === 2 && packageRecord.manifestPath.includes(identity.uiBuildId), names.filter((file) => file.startsWith('release-manifests/')));
check('Manifest inventories every other public payload file', names.length === manifestEntries.size + 1 && names.every((file) => file === packageRecord.manifestPath || manifestEntries.has(file)), { files: names.length, manifestEntries: manifestEntries.size });
check('Package record inventories exact complete payload', records.length === packageRecord.files.length && records.every((row) => packageRecord.files.some((saved) => saved.path === row.path && saved.bytes === row.bytes && saved.sha256 === row.sha256)), records.length);
check('No new scientific run occurred in this phase', baseline.newScientificExperiments === 0, baseline.newScientificExperiments);

for (const [relative, expected] of Object.entries({ ...baseline.baseline, ...baseline.sourceHashes })) {
  check(`Frozen source unchanged: ${relative}`, sha256(await fs.readFile(path.join(STUDY, relative))) === expected, expected);
}
for (const [relative, expected] of Object.entries(baseline.publicFiles)) {
  const input = await fs.readFile(path.join(WEBSITE, 'public/research', relative));
  const output = await fs.readFile(path.join(dist, 'research', relative));
  check(`Frozen public bytes unchanged: ${relative}`, sha256(input) === expected && sha256(output) === expected, expected);
}
for (const relative of researchManifestPaths) {
  check(`Frozen research manifest copy unchanged: ${relative}`, sha256(await fs.readFile(path.join(WEBSITE, 'public/research', relative))) === baseline.manifestSha256 && sha256(await fs.readFile(path.join(dist, 'research', relative))) === baseline.manifestSha256, baseline.manifestSha256);
}
check('No new or missing frozen public research file', publicResearchNames.length === Object.keys(baseline.publicFiles).length + 2 && publicResearchNames.every((file) => file in baseline.publicFiles || researchManifestPaths.includes(file)), publicResearchNames.length);
for (const [phase, historic] of Object.entries(baseline.historicalClosures)) {
  check(`Historical closure unchanged: ${phase}`, sha256(await fs.readFile(path.join(WEBSITE, `reports/${phase}_COMPLETION.json`))) === historic.sha256, historic.sha256);
  for (const row of historic.evidence) check(`Historical evidence unchanged: ${phase}/${row.path}`, sha256(await fs.readFile(path.join(WEBSITE, row.path))) === row.sha256, row.sha256);
}

const imageExceptions = [];
const providers = { htmlPhpJs: 1_000_000, htaccess: 10_000, other: 10_000_000 };
const operational = { javascript: 900_000, json: 500_000, normalImage: 300_000, completePayload: 10_000_000, initialGoal: 1_000_000 };
const forbiddenText = [
  ['absolute Windows local path', /[A-Za-z]:\\(?:Users|Windows|Program Files|Temp|Desktop)\\/i],
  ['absolute POSIX local path', /(?:file:\/\/|\/Users\/[^/\s]+\/|\/home\/[^/\s]+\/|\/mnt\/[a-z]\/)/i],
  ['account file-manager or installer URL', /(?:filemanager\.ai|scriptinstall\.rocks|cpsess\d{6,})/i],
  ['credential token', /(?:ghp_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)/],
];
for (const row of records) {
  const extension = path.extname(row.path).toLowerCase();
  const base = path.basename(row.path);
  const allowed = row.path === 'index.html' || /^assets\/[A-Za-z0-9_-]+\.(js|css)$/.test(row.path) || (row.path.startsWith('research/') && (row.path.slice(9) in baseline.publicFiles || researchManifestPaths.includes(row.path.slice(9)))) || /^ui\/figures\/[A-Za-z0-9_.-]+\.(png|webp|svg)$/.test(row.path) || row.path === packageRecord.manifestPath || row.path === manifest.payloadInventory;
  check(`Static-only allowlisted payload path: ${row.path}`, allowed && !/(?:^|\/)(?:node_modules|\.envs?|\.git|\.aws|\.codex|artifacts|models|scripts)(?:\/|$)/i.test(row.path) && !/\.(?:pt|pth|ckpt|onnx|exe|dll|py|map|zip|tar|gz)$/i.test(row.path), row.bytes);
  const providerLimit = base === '.htaccess' ? providers.htaccess : ['.html', '.php', '.js'].includes(extension) ? providers.htmlPhpJs : providers.other;
  check(`Provider per-file limit: ${row.path}`, row.bytes < providerLimit, { bytes: row.bytes, capExclusive: providerLimit });
  if (extension === '.js') check(`Operational JS chunk limit: ${row.path}`, row.bytes < operational.javascript, row.bytes);
  if (extension === '.json') check(`Operational JSON shard limit: ${row.path}`, row.bytes < operational.json, row.bytes);
  if (['.png', '.webp', '.svg', '.ico'].includes(extension) && row.bytes >= operational.normalImage) {
    const source = research.files.find((file) => `research/${file.path}` === row.path);
    const justified = Boolean(source && ['figures/overview.png', 'figures/uncertainty.png'].includes(source.logicalName) && row.sha256 === baseline.publicFiles[row.path.slice(9)]);
    check(`Documented frozen-image size exception: ${row.path}`, justified, { bytes: row.bytes, reason: 'Frozen scientific PNG retained byte-for-byte; UI derivative is separate and content hashed.' });
    imageExceptions.push({ ...row, logicalName: source?.logicalName, reason: 'Frozen source image integrity; compressed UI derivative does not replace the source.' });
  }
  if (manifestEntries.has(row.path)) {
    const entry = manifestEntries.get(row.path);
    check(`Manifest payload bytes/hash/MIME: ${row.path}`, entry.bytes === row.bytes && entry.sha256 === row.sha256 && entry.mediaType === mimeType(row.path), row.sha256);
  }
  if (['.html', '.js', '.css', '.json', '.csv', '.txt', '.svg'].includes(extension)) {
    const text = await fs.readFile(path.join(dist, row.path), 'utf8');
    for (const [label, pattern] of forbiddenText) check(`No ${label}: ${row.path}`, !pattern.test(text), 'Public text scanned; paths in scientific provenance are relative, never machine URLs.');
    if (extension === '.html') check(`No external runtime script/style CDN: ${row.path}`, !/(?:src|href)=["']https?:\/\//i.test(text), 'Entry assets are relative and same-origin.');
  }
}
const totalBytes = records.reduce((sum, row) => sum + row.bytes, 0);
check('Package count and byte total match complete payload', packageRecord.fileCount === records.length && packageRecord.totalBytes === totalBytes, { files: records.length, bytes: totalBytes });
check('Complete curated payload below 10 MB engineering goal', totalBytes < operational.completePayload, totalBytes);
check('Dependency and attribution notices included', manifest.licenses.length >= 2 && manifest.licenses.every((file) => names.includes(file)), manifest.licenses);
const loader = await fs.readFile(path.join(WEBSITE, 'src/data/loadRelease.ts'), 'utf8');
check('Runtime loader uses compiled immutable manifest and verifies bytes', loader.includes('DATA_RELEASE.manifestPath') && loader.includes('DATA_RELEASE.manifestSha256') && loader.includes('crypto.subtle.digest') && !loader.includes("fetch('research/manifest.json"), immutableManifest);
check('No service worker or runtime CDN implementation introduced', !(await Promise.all((await filesBelow(path.join(WEBSITE, 'src'))).filter((file) => /\.(tsx?|css)$/.test(file)).map((file) => fs.readFile(path.join(WEBSITE, 'src', file), 'utf8')))).some((text) => /navigator\.serviceWorker|importScripts\(|https:\/\/(?:unpkg\.com|cdn\.jsdelivr\.net)/.test(text)), 'No PWA/CDN dependency.');

// Follow the literal emitted HTML/JS/CSS asset paths, including lazy chunk maps.
const referenceChecks = new Set();
for (const row of records.filter((file) => /\.(?:html|js|css)$/.test(file.path))) {
  const text = await fs.readFile(path.join(dist, row.path), 'utf8');
  const matches = [...text.matchAll(/(?:["'(])((?:\.\/?)*(?:assets\/)?[A-Za-z0-9_-]+\.(?:js|css))(?:["')])/g)];
  for (const match of matches) {
    const raw = match[1];
    let target = raw.startsWith('assets/') || raw.startsWith('./assets/') ? raw.replace(/^\.\//, '') : path.posix.normalize(path.posix.join(path.posix.dirname(row.path), raw));
    if (!names.includes(target) && names.includes(`assets/${raw.replace(/^\.\//, '')}`)) target = `assets/${raw.replace(/^\.\//, '')}`;
    const key = `${row.path}->${target}`;
    if (!referenceChecks.has(key)) { referenceChecks.add(key); check(`Emitted chunk/style reference resolves: ${key}`, names.includes(target), raw); }
  }
}
check('Lazy viewer and chart are separate production chunks', names.some((file) => /^assets\/CrystalViewer-.*\.js$/.test(file)) && names.some((file) => /^assets\/ReplayChart-.*\.js$/.test(file)), names.filter((file) => /^assets\//.test(file)));

// A conservative cold-shell envelope includes entry HTML + its direct JS/CSS,
// eight bootstrap datasets + pinned manifest + real compact MgO cell and figure.
const entryText = await fs.readFile(path.join(dist, 'index.html'), 'utf8');
const direct = ['index.html', ...[...entryText.matchAll(/(?:src|href)="\.\/([^"?]+)"/g)].map((match) => match[1])];
const coreLogical = ['summary.json', 'methods.json', 'theme.json', 'claims.json', 'glossary.json', 'provenance.json', 'structures/index.json', 'replay/curves.json'];
const envelope = new Set([...direct, immutableManifest, ...coreLogical.map((name) => `research/${research.files.find((file) => file.logicalName === name).path}`)]);
const structureIndex = await readJson(`public/research/${research.files.find((file) => file.logicalName === 'structures/index.json').path}`);
const knownMgo = structureIndex.coreExamples.find((example) => example.id === 'known-mgo-sequence');
const compactStage = structureIndex.stages.find((stage) => stage.candidateId === knownMgo.candidateId && stage.stage === 'accepted_dft');
for (const logical of [compactStage.logicalFile, compactStage.fallbackFigureLogicalName]) envelope.add(`research/${research.files.find((file) => file.logicalName === logical).path}`);
const displaySource = await fs.readFile(path.join(WEBSITE, 'src/components/CrystalDisplay.tsx'), 'utf8');
check('Compact introduction defers the 3D chunk until interaction', displaySource.includes('useState(compact)') && displaySource.includes('useState(!compact)') && displaySource.includes('Explore interactive 3D'), 'The initial shell displays the genuine stage-specific saved figure. The full Lab retains the interactive viewer.');
const envelopeFiles = await Promise.all([...envelope].sort().map(async (file) => {
  const bytes = await fs.readFile(path.join(dist, file));
  return { path: file, bytes: bytes.length, gzipBytes: gzipSync(bytes).length };
}));
const initialBytes = envelopeFiles.reduce((sum, file) => sum + file.bytes, 0);
const initialGzipBytes = envelopeFiles.reduce((sum, file) => sum + file.gzipBytes, 0);
check('Conservative uncompressed initial shell envelope below 1 MB', initialBytes < operational.initialGoal, { bytes: initialBytes, gzipEstimate: initialGzipBytes, note: 'Measured file envelope, not a claim of provider compression or a browser network trace.' });

// Stage a new entry alongside predecessor immutable files. Do not change dist.
const previous = path.join(WEBSITE, '.cache/w6-previous-dist');
const merged = new Map();
for (const row of records) merged.set(row.path, await fs.readFile(path.join(dist, row.path)));
let previousCount = 0;
for (const row of baseline.previousBuildFiles) {
  const bytes = await fs.readFile(path.join(previous, row.path));
  check(`Saved W5 predecessor bytes: ${row.path}`, bytes.length === row.bytes && sha256(bytes) === row.sha256, row.sha256);
  if (row.path === 'index.html') { merged.set('cached-w5.html', bytes); continue; }
  if (merged.has(row.path)) check(`Immutable predecessor path cannot change bytes: ${row.path}`, sha256(merged.get(row.path)) === row.sha256, row.sha256);
  else { merged.set(row.path, bytes); previousCount++; }
}
const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname).slice(1) || 'index.html';
  if (!merged.has(pathname)) { response.writeHead(404, { 'Content-Type': 'text/plain' }); response.end('Unavailable'); return; }
  const bytes = merged.get(pathname);
  response.writeHead(200, { 'Content-Type': mimeType(pathname), 'Content-Length': bytes.length, 'X-Content-Type-Options': 'nosniff', 'Cache-Control': pathname.endsWith('.html') ? 'no-cache' : 'public, max-age=31536000, immutable' });
  response.end(bytes);
});
let httpChecks = 0;
try {
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  const base = `http://127.0.0.1:${server.address().port}/`;
  for (const [relative, expected] of merged) {
    const response = await fetch(new URL(relative, base));
    const actual = Buffer.from(await response.arrayBuffer());
    check(`HTTP staged payload bytes and MIME: ${relative}`, response.status === 200 && sha256(actual) === sha256(expected) && response.headers.get('content-type') === mimeType(relative), { status: response.status, bytes: actual.length, mediaType: response.headers.get('content-type') });
    httpChecks++;
  }
  const oldHtml = await (await fetch(new URL('cached-w5.html', base))).text();
  const oldAssets = [...oldHtml.matchAll(/(?:src|href)="\.\/([^"?]+)"/g)].map((match) => match[1]);
  check('Cached W5 HTML resolves its original emitted entry assets', oldAssets.length >= 2 && oldAssets.every((file) => merged.has(file)), oldAssets);
  const oldJs = (await Promise.all(oldAssets.filter((file) => file.endsWith('.js')).map((file) => fetch(new URL(file, base)).then((response) => response.text())))).join('\n');
  check('Cached W5 JS still pins original immutable data manifest and hash', oldJs.includes(identity.dataReleaseId) && oldJs.includes(identity.exportManifestSha256), { dataReleaseId: identity.dataReleaseId, manifestSha256: identity.exportManifestSha256 });
  check('New entry does not replace predecessor entry asset names', oldAssets.some((file) => !direct.includes(file)) && merged.has('index.html'), { oldAssets, currentEntryAssets: direct });
  const pinned = await fetch(new URL(immutableManifest, base));
  check('Old and new entries obtain identical pinned research bytes over HTTP', pinned.status === 200 && sha256(Buffer.from(await pinned.arrayBuffer())) === identity.exportManifestSha256, immutableManifest);
} finally { server.closeAllConnections(); await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())); }
check('Ephemeral cache-coherence server stopped', !server.listening, 'Loopback-only fixture closed in finally.');

// Independently enumerate and hash the ZIP through the existing Python runtime.
const python = process.env.FLAMEL_PYTHON || path.resolve(WEBSITE, '../.envs/analysis/Scripts/python.exe');
const zipCode = 'import hashlib,json,sys,zipfile\nwith zipfile.ZipFile(sys.argv[1]) as z:\n print(json.dumps([{"path":n,"bytes":len(z.read(n)),"sha256":hashlib.sha256(z.read(n)).hexdigest()} for n in sorted(z.namelist())]))\n';
const zip = spawnSync(python, ['-c', zipCode, path.join(WEBSITE, packageRecord.archive.path)], { encoding: 'utf8', maxBuffer: 5_000_000 });
check('Archive inspection through existing Python succeeds', zip.status === 0, zip.stderr.trim() || 'zipfile read and SHA-256 enumeration completed.');
if (zip.status === 0) {
  const zipped = JSON.parse(zip.stdout);
  check('Archive has exactly document-root payload entries and bytes', zipped.length === records.length && zipped.every((entry) => records.some((file) => file.path === entry.path && file.bytes === entry.bytes && file.sha256 === entry.sha256)), zipped.length);
}
check('Archive SHA-256 and byte count match local package record', JSON.stringify(await describeFile(WEBSITE, packageRecord.archive.path)) === JSON.stringify(packageRecord.archive), packageRecord.archive);
const failed = checks.filter((row) => !row.passed);
const result = {
  phase: 'W6', status: failed.length ? 'failed' : 'passed', checkedAt: new Date().toISOString(), uiBuildId: identity.uiBuildId,
  dataReleaseId: identity.dataReleaseId, exportManifestSha256: identity.exportManifestSha256,
  checkCount: checks.length, passed: checks.length - failed.length, failed: failed.length, checks,
  limits: { operational, provider: providers, providerReference: 'https://forum.infinityfree.com/t/file-size-and-upload-limits/49308', providerReferenceCheckedOn: '2026-10-22', units: 'Conservative decimal bytes; all comparisons on uncompressed files.' },
  payload: { files: records.length, bytes: totalBytes, largest: [...records].sort((a, b) => b.bytes - a.bytes).slice(0, 10), imageExceptions },
  initialEnvelope: { scope: 'Cold shell plus all eight bootstrap datasets and the actual MgO geometry/saved figure; conservative uncompressed file envelope. Browser ResourceTiming is recorded separately by native-browser QA.', files: envelopeFiles, bytes: initialBytes, gzipEstimateBytes: initialGzipBytes },
  cacheCoherence: { previousUiBuildId: baseline.previousUiBuildId, predecessorFiles: baseline.previousBuildFiles.length, predecessorOnlyRetainedFiles: previousCount, actualLoopbackHttpResponses: httpChecks, ephemeralServerStopped: !server.listening, deployedCacheHeadersTested: false, scope: 'Real HTTP byte/MIME check of locally staged old/new coexistence. Provider cache behavior and upload order require W7.' },
  package: { manifestPath: packageRecord.manifestPath, manifestSha256: packageRecord.manifestSha256, archive: packageRecord.archive },
  deploymentAttempted: false, newScientificExperiments: 0,
};
await writeJson('reports/W6_RELEASE_VALIDATION.json', result);
console.log(`W6 release: ${result.passed}/${result.checkCount} checks passed; ${totalBytes} payload bytes; ${initialBytes} initial-envelope bytes.`);
if (failed.length) { console.error(JSON.stringify(failed, null, 2)); process.exitCode = 1; }
