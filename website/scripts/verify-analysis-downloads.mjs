/** Validate actual browser-saved CSV bytes against their recorded UI selections.
 * Numerical independence is supplied by the three separately executed W5 source
 * verifiers; this script verifies the browser-to-projection chain, not new math. */
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(website);
const generation = await import(pathToFileURL(path.join(website, 'src/findings/generation.ts')));
const uncertainty = await import(pathToFileURL(path.join(website, 'src/findings/uncertainty.ts')));
const evidence = await import(pathToFileURL(path.join(website, 'src/evidence/model.ts')));
const { csvRows } = await import(pathToFileURL(path.join(website, 'src/replay/model.ts')));
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const checks = [];
const equal = (name, actual, expected) => { assert.deepEqual(actual, expected, name); checks.push({ name, passed: true }); };
const check = (name, value) => { assert.ok(value, name); checks.push({ name, passed: true }); };
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const readJson = async (relative) => JSON.parse(await fs.readFile(path.join(website, relative), 'utf8'));
const baselineBytes = await fs.readFile(path.join(website, 'reports/W5_BASELINE.json'));
const baseline = JSON.parse(baselineBytes);
equal('W5 baseline release matches pinned release', baseline.dataReleaseId, DATA_RELEASE.dataReleaseId);
equal('W5 baseline manifest matches pinned hash', baseline.manifestSha256, DATA_RELEASE.manifestSha256);
equal('W5 baseline names all 103 original inputs', Object.keys(baseline.sourceHashes).length, 103);
const before = {};
for (const [relative, expected] of Object.entries({ ...baseline.sourceHashes, ...baseline.baseline })) {
  before[relative] = sha(await fs.readFile(path.join(root, relative)));
  equal(`Frozen source before actual download verification ${relative}`, before[relative], expected);
}

const manifestBytes = await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath));
equal('Pinned public manifest SHA-256', sha(manifestBytes), DATA_RELEASE.manifestSha256);
const manifest = JSON.parse(manifestBytes);
const publicDatasetHashes = {};
async function dataset(logicalName) {
  const record = manifest.files.find((item) => item.logicalName === logicalName);
  check(`Manifest contains ${logicalName}`, record);
  const bytes = await fs.readFile(path.join(website, 'public/research', record.path));
  equal(`Public source hash ${logicalName}`, sha(bytes), record.sha256);
  publicDatasetHashes[logicalName] = record.sha256;
  return JSON.parse(bytes);
}
const [generated, uncertain, dft, summary] = await Promise.all([
  dataset('generation.json'), dataset('uncertainty.json'), dataset('dft.json'), dataset('summary.json'),
]);
const independentReports = [];
for (const reportName of ['W5_GENERATION_VALIDATION.json', 'W5_UNCERTAINTY_VALIDATION.json', 'W5_EVIDENCE_VALIDATION.json']) {
  const relative = `reports/${reportName}`, bytes = await fs.readFile(path.join(website, relative)), report = JSON.parse(bytes);
  equal(`${reportName} completed`, report.status, 'passed');
  equal(`${reportName} phase`, report.phase, 'W5');
  equal(`${reportName} release`, report.dataReleaseId, DATA_RELEASE.dataReleaseId);
  equal(`${reportName} pinned manifest`, report.manifestSha256, DATA_RELEASE.manifestSha256);
  check(`${reportName} has positive independent verification count`, report.checksPassed > 0);
  check(`${reportName} has no failed checks`, (report.checksFailed ?? 0) === 0 && (report.failedChecks ?? []).length === 0);
  independentReports.push({ path: relative, sha256: sha(bytes), checksPassed: report.checksPassed });
}

function projectedCsv(kind, selection = {}) {
  const release = DATA_RELEASE.dataReleaseId;
  if (kind === 'generationCohortCsv') return generation.generationCohortCsv(generated, selection.scope, selection.control, release);
  if (kind === 'generationDrawCsv') {
    const rows = selection.excluded ? generated.excluded : generation.compositionDraws(generated, selection.formula);
    const scope = selection.scope ?? (selection.excluded ? 'All twelve new-formula larger-cell diagnostics' : `${selection.formula}; eight new-formula attempts`);
    return generation.generationDrawCsv(generated, rows, release, scope);
  }
  if (kind === 'modelEnergyCsv') {
    const pair = generated.symmetryPairs.find((row) => row.control === selection.control);
    const rows = selection.all ? generated.relaxedStructures : selection.references
      ? generated.relaxedStructures.filter((row) => ['reference_anatase', 'reference_rutile'].includes(row.candidateId))
      : generation.selectedEnergyRows(generated, selection.control);
    const scope = selection.scope ?? (selection.all ? 'All eleven selected model records in source method order; compare energies only within composition'
      : selection.references ? 'Saved anatase and rutile references; within-TiO2 CHGNet comparison only'
      : `${selection.control}; ${pair?.scope ?? 'Unavailable'}; selected one structure per arm`);
    return generation.modelEnergyCsv(generated, rows, release, scope);
  }
  if (kind === 'prototypeCsv') return generation.prototypeCsv(generated, release);
  if (kind === 'compositionNoveltyCsv') return generation.compositionNoveltyCsv(generated, release);
  if (['uncertaintyMetricsCsv', 'uncertaintyRiskCsv', 'uncertaintyDecilesCsv'].includes(kind)) {
    const context = uncertainty.selectUncertaintyContext(uncertain, selection.seed, selection.endpoint, selection.retainedFraction ?? 1);
    check(`Recorded uncertainty selection exists: ${kind}/${selection.seed}/${selection.endpoint}`, context.metrics);
    return uncertainty[kind](uncertain, context, release);
  }
  if (kind === 'uncertaintyRolesCsv') return uncertainty.uncertaintyRolesCsv(uncertain, release);
  if (kind === 'dftJobsCsv') return evidence.dftJobsCsv(dft, { ...evidence.DEFAULT_DFT_FILTERS, ...(selection.filters ?? selection) }, release);
  if (kind === 'referenceMembershipsCsv') return evidence.referenceMembershipsCsv(dft, { ...evidence.DEFAULT_REFERENCE_FILTERS, ...(selection.filters ?? selection) }, release);
  if (kind === 'claimsCsv') return evidence.claimsCsv(summary.claims, release, summary.sourceIds);
  if (kind === 'budget') return csvRows([['lane', 'cap', 'charged', 'remaining', 'unit', 'interpretation', 'data_release_id', 'source_ids'],
    ...summary.budgets.map((row) => [row.lane, row.cap, row.charged, row.remaining, row.unit, row.interpretation, release, summary.sourceIds.join(';')])]);
  throw new Error(`Unknown browser CSV projection kind: ${kind}`);
}

/** Count logical records while respecting quoted line breaks. Byte comparison
 * already verifies field escaping, ordering, precision, units and null strings. */
function csvRecordCount(csv) {
  let quoted = false, rows = 0;
  for (let i = 0; i < csv.length; i++) {
    if (csv[i] === '"') {
      if (quoted && csv[i + 1] === '"') i++;
      else quoted = !quoted;
    } else if (!quoted && csv[i] === '\n') rows++;
  }
  equal('CSV quoted fields terminate', quoted, false);
  return Math.max(0, rows - 1);
}
const expectationsBytes = await fs.readFile(path.join(website, 'reports/W5_DOWNLOAD_EXPECTATIONS.json'));
const expectations = JSON.parse(expectationsBytes);
check('Browser download selection manifest is a nonempty array', Array.isArray(expectations) && expectations.length > 0);
equal('Actual download filenames are unique', new Set(expectations.map((item) => item.filename)).size, expectations.length);
const supported = ['generationCohortCsv', 'generationDrawCsv', 'prototypeCsv', 'modelEnergyCsv', 'compositionNoveltyCsv',
  'uncertaintyMetricsCsv', 'uncertaintyRiskCsv', 'uncertaintyDecilesCsv', 'uncertaintyRolesCsv', 'dftJobsCsv', 'referenceMembershipsCsv', 'claimsCsv', 'budget'];
const downloads = [];
for (const entry of expectations) {
  check(`Known CSV kind ${entry.kind}`, supported.includes(entry.kind));
  check(`Safe retained CSV basename ${entry.filename}`, typeof entry.filename === 'string' && entry.filename === path.basename(entry.filename)
    && !entry.filename.includes('..') && entry.filename.toLowerCase().endsWith('.csv'));
  const relative = `reports/analysis-downloads/${entry.filename}`;
  const bytes = await fs.readFile(path.join(website, relative));
  const hasUtf8Bom = bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf;
  equal(`Actual browser CSV has UTF-8 BOM ${entry.filename}`, hasUtf8Bom, true);
  const payload = hasUtf8Bom ? bytes.subarray(3) : bytes;
  const actual = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(payload);
  const expected = projectedCsv(entry.kind, entry.selection ?? {});
  check(`Actual browser bytes equal selected projection ${entry.filename}`, payload.equals(Buffer.from(expected, 'utf8')));
  check(`Actual browser CSV uses CRLF records ${entry.filename}`, actual.endsWith('\r\n'));
  check(`Actual browser CSV identifies the pinned release ${entry.filename}`, actual.includes(DATA_RELEASE.dataReleaseId));
  const rowCount = csvRecordCount(actual);
  equal(`Actual browser CSV logical row count ${entry.filename}`, rowCount, csvRecordCount(expected));
  downloads.push({ path: relative, kind: entry.kind, selection: entry.selection ?? {}, bytes: bytes.length,
    sha256: sha(bytes), utf8Bom: hasUtf8Bom, dataRows: rowCount, projectionSha256: sha(Buffer.from(expected, 'utf8')), exactProjectionMatch: true });
}
for (const kind of supported) check(`At least one real browser CSV covers ${kind}`, downloads.some((item) => item.kind === kind));
const after = {};
for (const [relative, expected] of Object.entries(before)) {
  after[relative] = sha(await fs.readFile(path.join(root, relative)));
  equal(`Frozen source after actual download verification ${relative}`, after[relative], expected);
}
const helperHashes = {};
for (const relative of ['src/findings/generation.ts', 'src/findings/uncertainty.ts', 'src/evidence/model.ts', 'src/replay/model.ts'])
  helperHashes[relative] = sha(await fs.readFile(path.join(website, relative)));
const report = { phase: 'W5', status: 'passed', createdUtc: new Date().toISOString(),
  scope: 'Actual browser-saved UTF-8 CSV byte comparison against current selected UI projections, chained to three independent frozen-source validators. This is not an additional independent numerical reconstruction.',
  checksPassed: checks.length, failedChecks: [], dataReleaseId: DATA_RELEASE.dataReleaseId, manifestSha256: DATA_RELEASE.manifestSha256,
  baselineSha256: sha(baselineBytes), selectionManifestSha256: sha(expectationsBytes), independentReports, publicDatasetHashes, helperHashes,
  originalSourceCount: Object.keys(baseline.sourceHashes).length, originalSourcesUnchanged: true, newScientificRuns: 0,
  downloadedFiles: downloads.length, downloadedDataRows: downloads.reduce((sum, item) => sum + item.dataRows, 0), downloads,
  before, after, checks };
await fs.writeFile(path.join(website, 'reports/W5_DOWNLOAD_VALIDATION.json'), JSON.stringify(report, null, 2) + '\n');
console.log(`W5 browser CSV validation: ${checks.length} checks passed, ${downloads.length} files, ${report.downloadedDataRows} rows; all 103 original inputs unchanged.`);
