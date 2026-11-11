/** Actual W6 browser files compared with selected shipped projections. Frozen
 * arithmetic is independently checked by the linked W6 science validators. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
const w = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const load = name => import(pathToFileURL(path.join(w, 'src', name)));
const replay = await load('replay/model.ts'), geometry = await load('crystal/geometry.ts');
const evidence = await load('evidence/model.ts'), uncertainty = await load('findings/uncertainty.ts');
const generation = await load('findings/generation.ts'), route = await load('state/route.ts');
const { DATA_RELEASE } = await load('data/release.ts');
const { UI_RELEASE_ID } = await load('generated/uiRelease.ts');
const sha = b => createHash('sha256').update(b).digest('hex');
const read = async name => JSON.parse(await fs.readFile(path.join(w, name), 'utf8'));
const manifest = await read('public/research/manifest.json');
async function dataset(name) {
  const row = manifest.files.find(r => r.logicalName === name); assert.ok(row, name);
  const bytes = await fs.readFile(path.join(w, 'public/research', row.path));
  assert.equal(sha(bytes), row.sha256); return JSON.parse(bytes);
}
const expectations = await read('reports/W6_DOWNLOAD_EXPECTATIONS.json');
const checks = [], downloads = [];
function check(name, passed) { assert.ok(passed, name); checks.push({ name, passed: true }); }
const independentReports = [];
for (const name of ['REPLAY_VALIDATION','GEOMETRY_VALIDATION','GENERATION_VALIDATION','UNCERTAINTY_VALIDATION','EVIDENCE_VALIDATION']) {
  const file = `reports/W6_${name}.json`, bytes = await fs.readFile(path.join(w, file)), report = JSON.parse(bytes);
  check(`${name} current read-only acceptance passed`, report.status === 'passed' && report.dataReleaseId === DATA_RELEASE.dataReleaseId);
  independentReports.push({ path: file, sha256: sha(bytes) });
}
for (const row of expectations) {
  const file = `reports/w6-downloads/${row.filename}`, bytes = await fs.readFile(path.join(w, file));
  const text = bytes.toString('utf8').replace(/^\uFEFF/, ''); let expected;
  const s = row.selection ?? {}, release = DATA_RELEASE.dataReleaseId;
  if (row.kind === 'comparison') {
    const parsed = route.parseRoute(s.hash);
    expected = replay.comparisonCsv(await dataset('replay/curves.json'), await dataset('theme.json'), parsed.state, release);
  } else if (row.kind === 'query') expected = replay.queryCsv(await dataset(`replay/seed-${s.seed}.json`), s.policy, s.batch, s.revealed, release);
  else if (row.kind === 'cif') {
    const index = await dataset('structures/index.json'), stage = index.stages.find(e => e.stageId === s.stageId);
    check('CIF stage exists in frozen registry', !!stage); expected = geometry.structureCif(await dataset(stage.logicalFile), release);
  } else if (row.kind === 'dft') expected = evidence.dftJobsCsv(await dataset('dft.json'), { ...evidence.DEFAULT_DFT_FILTERS, ...s.filters }, release);
  else if (row.kind === 'risk') {
    const data = await dataset('uncertainty.json');
    expected = uncertainty.uncertaintyRiskCsv(data, uncertainty.selectUncertaintyContext(data,s.seed,s.endpoint,s.retainedFraction), release);
  } else if (row.kind === 'cohort') expected = generation.generationCohortCsv(await dataset('generation.json'),s.scope,s.control,release);
  else throw Error('Unexpected download kind');
  check(`Browser bytes match current selected ${row.kind}: ${file}`, text === expected);
  check(`Export identifies pinned data release: ${file}`, text.includes(release));
  check(`Export is nonempty: ${file}`, bytes.length > 100);
  downloads.push({ ...row, path:file, bytes:bytes.length,sha256:sha(bytes),exactProjectionMatch:true });
}
for (const kind of ['comparison','query','cif','dft','risk','cohort']) check(`Actual ${kind} download exercised`,expectations.some(e=>e.kind===kind));
check('Hidden and revealed query files both exercised',expectations.some(e=>e.kind==='query'&&!e.selection.revealed)&&expectations.some(e=>e.kind==='query'&&e.selection.revealed));
const report = { phase:'W6',status:'passed',checkedAt:new Date().toISOString(),uiBuildId:UI_RELEASE_ID,dataReleaseId:DATA_RELEASE.dataReleaseId,
  scope:'Fresh actual browser-file to selected projection verification; independent scientific arithmetic is separately hash-bound.',checksPassed:checks.length,
  expectationsSha256:sha(await fs.readFile(path.join(w,'reports/W6_DOWNLOAD_EXPECTATIONS.json'))),downloads,independentReports,checks };
await fs.writeFile(path.join(w,'reports/W6_DOWNLOAD_VALIDATION.json'),JSON.stringify(report,null,2)+'\n');
console.log(`W6 actual downloads: ${downloads.length} files; ${checks.length} checks passed.`);
