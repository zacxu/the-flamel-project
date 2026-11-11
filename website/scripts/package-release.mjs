/** Package only the production static payload, with an immutable inventory. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { WEBSITE, assertPrepared, describeFile, filesBelow, mimeType, readJson, sha256, writeJson } from './release-utils.mjs';

if (process.argv.length > 2) throw new Error('Usage: node scripts/package-release.mjs');
const { identity } = await assertPrepared();
const dist = path.join(WEBSITE, 'dist');
const runtimeNames = (await filesBelow(dist)).filter((file) => !file.startsWith('release-manifests/'));
const runtime = await Promise.all(runtimeNames.map(async (file) => ({ ...await describeFile(dist, file), mediaType: mimeType(file) })));
const js = runtime.filter((file) => file.path.endsWith('.js'));
const sourceTexts = await Promise.all(js.map((file) => fs.readFile(path.join(dist, file.path), 'utf8')));
if (!sourceTexts.some((text) => text.includes(identity.uiBuildId))) throw new Error('Production JavaScript does not contain the prepared UI identity. Rebuild first.');
const releaseDirectory = `release-manifests/${identity.uiBuildId}`;
const inventoryPath = `${releaseDirectory}.files.csv`;
const csv = `path,bytes,sha256,media_type\n${runtime.map((file) => [file.path, file.bytes, file.sha256, file.mediaType].map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n')}\n`;
await fs.mkdir(path.join(dist, 'release-manifests'), { recursive: true });
await fs.writeFile(path.join(dist, inventoryPath), csv);
const inventory = { ...await describeFile(dist, inventoryPath), mediaType: mimeType(inventoryPath) };
const manifestPath = `${releaseDirectory}.json`;
const oldMetadata = (await filesBelow(dist)).filter((file) => file.startsWith('release-manifests/') && file !== inventoryPath && file !== manifestPath);
if (oldMetadata.length) throw new Error('A stale release manifest remains in dist. Rebuild from source before packaging.');
const baseline = await readJson('reports/W6_BASELINE.json');
const manifest = {
  ...identity, releaseManifestVersion: 1,
  scope: 'Local static website release; recorded frozen study only; no live inference or deployment.',
  payloadInventory: inventoryPath,
  selfExclusion: 'This manifest excludes its own hash. Its SHA-256 is recorded by the local package record outside the public payload. The CSV inventories runtime files; this manifest inventories those files plus the CSV.',
  predecessorUiBuildId: baseline.previousUiBuildId,
  cachePolicy: 'Upload immutable files before index.html; retain prior immutable assets/data for cached entries. Never replace a versioned path with different bytes. No service worker.',
  licenses: runtime.filter((file) => /\/notices\//.test(file.path)).map((file) => file.path),
  files: [...runtime, inventory].sort((a, b) => a.path.localeCompare(b.path)),
};
await fs.writeFile(path.join(dist, manifestPath), `${JSON.stringify(manifest, null, 2)}\n`);
const packaged = await Promise.all((await filesBelow(dist)).map((file) => describeFile(dist, file)));
// ZIP entries are document-root relative. No local source paths or README enter it.
const releaseRelative = `releases/${identity.uiBuildId}`;
const release = path.join(WEBSITE, releaseRelative);
await fs.mkdir(release, { recursive: true });
const zipPath = path.join(release, `${identity.uiBuildId}.zip`);
const python = process.env.FLAMEL_PYTHON || path.resolve(WEBSITE, '../.envs/analysis/Scripts/python.exe');
const code = 'from pathlib import Path\nimport sys, zipfile\nroot=Path(sys.argv[1]); target=Path(sys.argv[2])\nwith zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:\n for p in sorted(root.rglob("*")):\n  if p.is_file():\n   info=zipfile.ZipInfo(p.relative_to(root).as_posix(),date_time=(2026,10,22,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16\n   z.writestr(info,p.read_bytes(),compresslevel=9)\n';
const zipped = spawnSync(python, ['-c', code, dist, zipPath], { encoding: 'utf8' });
if (zipped.status !== 0) throw new Error(`Local ZIP creation failed: ${zipped.stderr}`);
const archive = await describeFile(release, path.basename(zipPath));
const packageRecord = {
  phase: 'W6', status: 'packaged_locally', ...identity,
  payload: 'dist/', manifestPath, manifestSha256: sha256(await fs.readFile(path.join(dist, manifestPath))),
  fileCount: packaged.length, totalBytes: packaged.reduce((sum, file) => sum + file.bytes, 0), files: packaged,
  archive: { ...archive, path: `${releaseRelative}/${archive.path}` },
  deployed: false, uploadInstructions: 'Upload ZIP contents, not the ZIP itself or a nested dist folder. W7 must verify the assigned document root, backup, immutable-first upload and fresh HTTPS browser operation.',
};
await writeJson('reports/W6_RELEASE_PACKAGE.json', packageRecord);
await writeJson(`${releaseRelative}/package-record.json`, packageRecord);
await fs.writeFile(path.join(release, 'README.md'), `# Local release ${identity.uiBuildId}\n\nThis archive contains the exact production document-root files, including the versioned release manifest. It does not contain source, dependencies, scientific environments, credentials or a study archive. It has not been deployed.\n\nFor a local HTTP preview, run the pinned Node executable with \`scripts/qa-server.mjs --port 4175\` from \`website/\`, then open \`http://127.0.0.1:4175/\`. Alternatively run \`scripts/npm.ps1 run preview -- --port 4175\`. Do not open index.html with file://.\n\nW7 must inspect the authenticated account, confirm document root and HTTPS, back up current files, upload immutable files and manifest first, preserve predecessor immutable assets, replace index.html last, then verify in a fresh normal browser. The local ZIP is a handoff artifact, not a substitute for those checks.\n`);
console.log(`Packaged ${identity.uiBuildId}: ${packaged.length} files, ${packageRecord.totalBytes} bytes; ZIP ${archive.bytes} bytes. Not deployed.`);
