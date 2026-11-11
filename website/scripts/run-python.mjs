import { existsSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const websiteRoot = fileURLToPath(new URL('../', import.meta.url));
const defaultPython = path.resolve(websiteRoot, '..', '.envs', 'analysis', 'Scripts', 'python.exe');
const python = process.env.FLAMEL_PYTHON || defaultPython;
if (!existsSync(python)) {
  throw new Error('Existing analysis Python is unavailable. Set FLAMEL_PYTHON to the research export interpreter.');
}
const script = path.resolve(websiteRoot, process.argv[2] || '');
const relative = path.relative(path.join(websiteRoot, 'scripts'), script);
if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
  throw new Error('Only scripts inside website/scripts may run through this wrapper.');
}
const result = spawnSync(python, [script, ...process.argv.slice(3)], {
  cwd: websiteRoot, stdio: 'inherit', env: { ...process.env, PYTHONUTF8: '1' },
});
if (result.error) throw result.error;
process.exit(result.status ?? 1);
