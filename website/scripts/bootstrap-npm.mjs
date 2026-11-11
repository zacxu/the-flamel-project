import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const tooling = path.join(root, '.tooling');
const version = '12.2.1';
const url = `https://registry.npmjs.org/npm/-/npm-${version}.tgz`;
const expected = 'sha512-bKCmFRVT/BB+YPEYbZwQ1XUI3N5t4xKSpU1MxOjo7z3iWzKBJ0ZXRC1xFdEN+TC7N5TdywaBzf2dMXGJq/e2PQ==';
const target = path.join(tooling, 'npm');
try {
  const pkg = JSON.parse(await readFile(path.join(target, 'package.json'), 'utf8'));
  if (pkg.version === version) process.exit(0);
  throw new Error(`Unexpected local npm ${pkg.version}; expected ${version}.`);
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
await mkdir(tooling, { recursive: true });
const response = await fetch(url);
if (!response.ok) throw new Error(`npm bootstrap download failed: HTTP ${response.status}.`);
const buffer = Buffer.from(await response.arrayBuffer());
const integrity = `sha512-${createHash('sha512').update(buffer).digest('base64')}`;
if (integrity !== expected) throw new Error('npm archive integrity mismatch.');
const archive = path.join(tooling, `npm-${version}.tgz`);
await writeFile(archive, buffer);
await mkdir(target, { recursive: true });
const extraction = spawnSync('tar', ['-xzf', archive, '--strip-components=1', '-C', target], { stdio: 'inherit' });
if (extraction.status !== 0) throw new Error('npm archive extraction failed.');
console.log(`Prepared workspace-only npm ${version}; registry archive integrity verified.`);
