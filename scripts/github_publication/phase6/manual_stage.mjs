/** Stage through the existing publication guard in a NEW external directory.
 * The source clone can retain a historical incomplete stage without mutation.
 * No upload, hosting access, build, or guard bypass.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const values = new Map();
for (const argument of process.argv.slice(2)) {
  if (argument === '--stage') {
    assert.ok(!values.has('stage'), 'Duplicate --stage');
    values.set('stage', true);
  } else {
    const match = argument.match(/^--(website-root|stage-root|package)=(.+)$/);
    assert.ok(match && !values.has(match[1]), 'Pass each explicit argument exactly once');
    values.set(match[1], match[2]);
  }
}
assert.equal(values.size, 4, 'Usage: --website-root=<source/website> --stage-root=<new external directory> --package=reports/W6_RELEASE_PACKAGE.json --stage');
assert.equal(values.get('stage'), true, 'Explicit staging is required');
const websiteRoot = path.resolve(values.get('website-root'));
const stageRoot = path.resolve(values.get('stage-root'));
assert.ok(stageRoot !== websiteRoot && !stageRoot.startsWith(websiteRoot + path.sep), 'Stage must be outside website source');
for (let parent = stageRoot; ; parent = path.dirname(parent)) {
  try { assert.ok(!(await fs.lstat(parent)).isSymbolicLink(), 'Stage ancestors cannot be symbolic links'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (path.dirname(parent) === parent) break;
}
// mkdir without recursive cannot overwrite/reuse an existing stage root.
await fs.mkdir(stageRoot);
const utils = await import(pathToFileURL(path.join(websiteRoot, 'scripts/release-utils.mjs')).href);
const guard = await import(pathToFileURL(path.join(websiteRoot, 'deployment/latest-link/prepare-publication.mjs')).href);
const { identity } = await utils.assertPrepared();
const verified = await guard.verifyPublication({ websiteRoot, identity, packageRelative: values.get('package') });
const result = await guard.stagePublication(verified, { websiteRoot: stageRoot });
console.log(JSON.stringify({ status: 'passed', mode: 'staged_external', uiBuildId: identity.uiBuildId, stage: result, hostingDeployed: false }, null, 2));
