/** Exercise the shipped runtime guards against the immutable real release and
 * deliberately malformed records. This performs no scientific computation. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { guardDataset, ResearchShapeError } = await import(pathToFileURL(path.join(website, 'src/data/guards.ts')));
const manifest = JSON.parse(await fs.readFile(path.join(website, 'public/research/manifest.json'), 'utf8'));
const datasets = new Map();
const checks = [];
const passed = (name) => checks.push({ check: name, passed: true });
for (const entry of manifest.files.filter((file) => file.mediaType === 'application/json')) {
  const raw = await fs.readFile(path.join(website, 'public/research', entry.path), 'utf8');
  const data = JSON.parse(raw);
  datasets.set(entry.logicalName, data);
  assert.strictEqual(guardDataset(entry.logicalName, data), data, 'The guard returns the unmodified saved object');
  assert.equal(JSON.stringify(data), JSON.stringify(JSON.parse(raw)), 'The guard does not mutate the recorded values');
  passed(`Actual ${entry.logicalName} validates without coercion or mutation`);
  for (const [field, value] of [['schemaVersion', 99], ['studyId', 'other-study'], ['dataset', 'other-dataset']]) {
    assert.throws(() => guardDataset(entry.logicalName, { ...data, [field]: value }), ResearchShapeError);
    passed(`${entry.logicalName} rejects an invalid ${field}`);
  }
}
function rejects(name, description, mutate) {
  const fixture = structuredClone(datasets.get(name));
  mutate(fixture);
  assert.throws(() => guardDataset(name, fixture), ResearchShapeError, description);
  passed(description);
}
rejects('summary.json', 'A missing policy statistic fails before rendering', (v) => { delete v.policyStatistics.full; });
rejects('summary.json', 'A numeric string is rejected rather than coerced', (v) => { v.policyStatistics.full.nearStableHits.mean = '29.4'; });
rejects('summary.json', 'Non-finite nested statistics are rejected', (v) => { v.policyStatistics.full.nearStableHits.values[0] = Infinity; });
rejects('summary.json', 'A null count is rejected rather than shown as zero', (v) => { v.counts.historicalQueryEvents = null; });
rejects('summary.json', 'A discovery flag inconsistent with the closed prototype is rejected', (v) => { v.newStableMaterialEstablished = true; });
rejects('methods.json', 'Unsupported live computation metadata is rejected', (v) => { v.liveScientificCompute = true; });
rejects('methods.json', 'A JavaScript attribution URL is rejected', (v) => { v.attributions[0].url = 'javascript:alert(1)'; });
rejects('methods.json', 'A missing workflow label is rejected', (v) => { delete v.workflow[0].label; });
rejects('theme.json', 'A missing frozen policy colour is rejected', (v) => { delete v.policyColours.full; });
rejects('claims.json', 'A claim without its evidence identities is rejected', (v) => { delete v.claims[0].sourceIds; });
rejects('claims.json', 'Duplicate claim identities are rejected', (v) => { v.claims[1].id = v.claims[0].id; });
rejects('glossary.json', 'A missing glossary definition is rejected', (v) => { delete v.terms[0].definition; });
rejects('provenance.json', 'Malformed source checksums are rejected', (v) => { v.sources[0].sha256 = 'unknown'; });
rejects('provenance.json', 'Duplicate source identities are rejected', (v) => { v.sources[1].sourceId = v.sources[0].sourceId; });
rejects('replay/curves.json', 'Curve array truncation is rejected', (v) => { v.points.pop(); });
rejects('replay/curves.json', 'Duplicate curve observations are rejected', (v) => { v.points[1] = v.points[0]; });
rejects('replay/curves.json', 'A made-up zero-query precision is rejected', (v) => { v.zeroQueryOrigin.precision = 0; });
rejects('replay/seed-20261022.json', 'A history with a different filename seed is rejected', (v) => { v.seed = 20261023; });
rejects('replay/seed-20261022.json', 'A history query without formula metadata is rejected', (v) => { delete v.histories[0].batches[0].queries[0].formula; });
rejects('replay/seed-20261022.json', 'A string-valued hit flag is rejected', (v) => { v.histories[0].batches[0].queries[0].nearStableHit = 'false'; });
rejects('replay/seed-20261022.json', 'A malformed chronological query order is rejected', (v) => { v.histories[0].batches[0].queries[0].queryNumber = 50; });
rejects('structures/index.json', 'A fabricated registered stage count is rejected', (v) => { v.counts.stages = 27; });
rejects('structures/index.json', 'A default stage outside its saved candidate is rejected', (v) => { v.candidates[0].defaultStageId = 'no-such-stage'; });
rejects('structures/index.json', 'A stage assigned to another candidate is rejected', (v) => { v.stages[0].candidateId = 'no-such-candidate'; });
const stageName = [...datasets.keys()].find((name) => name.startsWith('structures/') && name !== 'structures/index.json');
assert.ok(stageName);
rejects(stageName, 'A non-finite atomic coordinate is rejected', (v) => { v.geometry.fractionalCoordinates[0][0] = NaN; });
rejects(stageName, 'A missing physical site is rejected', (v) => { v.geometry.sites.pop(); });
rejects(stageName, 'A mismatched fallback physical atom count is rejected', (v) => { v.fallbackFigureDisplay.physicalAtoms += 1; });
rejects(stageName, 'An invalid saved space group is rejected', (v) => { v.symmetry.spacegroupNumber = 231; });
rejects('generation.json', 'A model energy string is rejected', (v) => { v.relaxedStructures[0].chgnetEnergyEVPerAtom = '-2.0'; });
rejects('generation.json', 'An unknown generator arm is rejected', (v) => { v.cohorts[0].arm = 'invented'; });
rejects('dft.json', 'A missing terminal SCF acceptance flag is rejected', (v) => { delete v.jobs[0].terminalScfAccepted; });
rejects('dft.json', 'An unknown DFT evidence level is rejected', (v) => { v.jobs[0].evidenceLevel = 'stable'; });
rejects('uncertainty.json', 'An empirical coverage over one is rejected', (v) => { v.evaluationMetrics[0].interval90EmpiricalCoverage = 90; });
rejects('uncertainty.json', 'A malformed risk coverage row is rejected', (v) => { v.riskCoverage[0].retainedRows = null; });
const phase = process.argv.includes('--phase=W6') ? 'W6' : process.argv.includes('--phase=W5') ? 'W5' : process.argv.includes('--phase=W4') ? 'W4' : process.argv.includes('--phase=W3') ? 'W3' : 'W2';
const report = { phase, status: 'passed', generatedAt: new Date().toISOString(),
  dataReleaseId: manifest.dataReleaseId, actualDatasets: datasets.size, checksPassed: checks.length, checks,
  scope: 'Shipped runtime guards against all recorded public datasets and malformed boundary fixtures; no data export or scientific computation.' };
await fs.writeFile(path.join(website, `reports/${phase}_DATA_GUARDS.json`), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ status: report.status, actualDatasets: datasets.size, checksPassed: checks.length }));
