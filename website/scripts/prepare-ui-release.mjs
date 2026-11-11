/** Assign a deterministic UI identity without modifying frozen research. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { WEBSITE, expectedIdentity, identityModule, writeJson } from './release-utils.mjs';

if (process.argv.slice(2).some((arg) => arg !== '--check')) throw new Error('Usage: node scripts/prepare-ui-release.mjs [--check]');
const { identity, inputs } = await expectedIdentity();
const target = path.join(WEBSITE, 'src/generated/uiRelease.ts');
if (process.argv.includes('--check')) {
  if (await fs.readFile(target, 'utf8') !== identityModule(identity)) throw new Error('UI identity is stale. Prepare and rebuild.');
  console.log(`UI identity current: ${identity.uiBuildId}`);
} else {
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.writeFile(target, identityModule(identity));
  await writeJson('.cache/W6_UI_RELEASE_INPUTS.json', { ...identity, generatedModule: 'src/generated/uiRelease.ts', fingerprintRule: 'SHA-256 of sorted relative input path, byte count and SHA-256 tuples; generated identity module excluded.', inputs: inputs.files });
  console.log(`Prepared ${identity.uiBuildId}; ${inputs.files.length} local source/configuration inputs. Frozen data: ${identity.dataReleaseId}`);
}
