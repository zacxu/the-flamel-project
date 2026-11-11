/** W5 uncertainty: compare original frozen CSVs, public data, endpoint projections
 * and every displayed CSV filter. Read-only diagnostics, with no scientific run. */
const phase = process.argv.includes('--phase=W6') ? 'W6' : 'W5';

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(website);
const { selectUncertaintyContext, roleTotals, uncertaintyMetricsCsv, uncertaintyRiskCsv, uncertaintyDecilesCsv, uncertaintyRolesCsv } =
  await import(pathToFileURL(path.join(website, 'src/findings/uncertainty.ts')));
const { SEEDS, POLICIES, RETAINED_FRACTIONS } = await import(pathToFileURL(path.join(website, 'src/state/route.ts')));
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const checks = [];
const equal = (name, actual, expected) => { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); };
const check = (name, value) => { assert.ok(value, name); checks.push({ check: name, passed: true }); };
const close = (name, actual, expected) => check(name, Number.isFinite(actual) && Math.abs(actual - expected) < 1e-12);
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const manifestBytes = await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath));
equal('Release manifest remains pinned', sha(manifestBytes), DATA_RELEASE.manifestSha256);
const manifest = JSON.parse(manifestBytes);
async function readDataset(logicalName) {
  const record = manifest.files.find((item) => item.logicalName === logicalName);
  check(`Manifest contains ${logicalName}`, record);
  const bytes = await fs.readFile(path.join(website, 'public/research', record.path));
  equal(`Immutable public hash ${logicalName}`, sha(bytes), record.sha256);
  return JSON.parse(bytes);
}
const [dataset, provenance] = await Promise.all([readDataset('uncertainty.json'), readDataset('provenance.json')]);
const originalJson = JSON.stringify(dataset);
for (const id of dataset.sourceIds) check(`Public source ID resolves ${id}`, provenance.sources.some((source) => source.sourceId === id));
check('Saved reliability figure logical name resolves', manifest.files.some((item) => item.logicalName === 'figures/uncertainty.png'));
const exportReport = JSON.parse(await fs.readFile(path.join(website, 'reports/W1_EXPORT.json')));
const inventory = JSON.parse(await fs.readFile(path.join(website, 'research_sources.json')));
const before = {};
for (const [relative, expected] of Object.entries(inventory.baseline_integrity)) {
  before[relative] = sha(await fs.readFile(path.join(root, relative)));
  equal(`Frozen baseline before ${relative}`, before[relative], expected);
}

function parseCsv(text) {
  const rows = []; let row = [], value = '', quoted = false;
  text = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { value += '"'; i++; }
      else if (c === '"') quoted = false;
      else value += c;
    } else if (c === '"' && value === '') quoted = true;
    else if (c === ',') { row.push(value); value = ''; }
    else if (c === '\r' || c === '\n') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(value); rows.push(row); row = []; value = '';
    } else value += c;
  }
  assert.equal(quoted, false);
  if (value || row.length) { row.push(value); rows.push(row); }
  const [headers, ...body] = rows;
  return body.map((fields) => Object.fromEntries(headers.map((key, index) => [key, fields[index]])));
}
async function sourceCsv(name) {
  const relative = `artifacts/phase6/uncertainty/${name}.csv`;
  const bytes = await fs.readFile(path.join(root, relative));
  equal(`Frozen original CSV hash ${name}`, sha(bytes), exportReport.inputAllowlist[relative].sha256);
  return parseCsv(bytes.toString('utf8'));
}
const [metrics, risk, deciles, roles] = await Promise.all(['evaluation_metrics', 'risk_coverage', 'uncertainty_deciles', 'full_policy_role_diagnostics'].map(sourceCsv));
equal('All 130 saved evaluation snapshots retained', dataset.evaluationMetrics.length, 130);
equal('All 300 saved retention records retained', dataset.riskCoverage.length, 300);
equal('All 300 saved decile records retained', dataset.deciles.length, 300);
equal('All ten saved role records retained', dataset.roles.length, 10);
const key = (row) => `${row.seed}/${row.policy}/${row.queries}`;
const mappings = {
  metrics: { rows: 'n', maeEVPerAtom: 'MAE_eV_atom', rmseEVPerAtom: 'RMSE_eV_atom', disagreementAbsoluteErrorSpearman: 'Spearman_disagreement_absolute_error', interval90EmpiricalCoverage: 'interval_90_empirical_coverage', meanIntervalWidthEVPerAtom: 'mean_interval_width_eV_atom', calibrationScale: 'calibration_q' },
  risk: { requestedRetainedFraction: 'requested_retained_fraction', retainedRows: 'retained_rows', actualRetainedFraction: 'actual_retained_fraction', maeEVPerAtom: 'MAE_eV_atom', allRowsMaeEVPerAtom: 'all_rows_MAE_eV_atom', maeRelativeToAllRows: 'MAE_relative_to_all_rows', interval90EmpiricalCoverage: 'interval_90_empirical_coverage' },
  deciles: { decile: 'uncertainty_decile', rows: 'n', meanDisagreementEVPerAtom: 'mean_disagreement_eV_atom', minDisagreementEVPerAtom: 'min_disagreement_eV_atom', maxDisagreementEVPerAtom: 'max_disagreement_eV_atom', maeEVPerAtom: 'MAE_eV_atom', interval90EmpiricalCoverage: 'interval_90_empirical_coverage', meanIntervalWidthEVPerAtom: 'mean_interval_width_eV_atom' },
  roles: { queries: 'queries', nearStableHits: 'near_stable_hits', precision: 'precision', referenceHullHits: 'reference_hull_hits', meanPredictedMeanEVPerAtom: 'mean_predicted_mean_eV_atom', meanCalibratedRadiusEVPerAtom: 'mean_calibrated_radius_eV_atom', meanDiversityDistance: 'mean_diversity_distance' },
};
for (const [name, publicRows, originalRows, suffix] of [
  ['metrics', dataset.evaluationMetrics, metrics, () => ''],
  ['risk', dataset.riskCoverage, risk, (r) => `/${Number(r.requestedRetainedFraction ?? r.requested_retained_fraction)}`],
  ['deciles', dataset.deciles, deciles, (r) => `/${Number(r.decile ?? r.uncertainty_decile)}`],
  ['roles', dataset.roles, roles, (r) => `/${r.role}`],
]) {
  const identity = (r) => name === 'roles' ? `${r.seed}/${r.role}` : key(r) + suffix(r);
  const originals = new Map(originalRows.map((row) => [identity(row), row]));
  equal(`Original row count ${name}`, publicRows.length, originalRows.length);
  equal(`Original identities unique ${name}`, originals.size, originalRows.length);
  for (const row of publicRows) {
    const id = identity(row), source = originals.get(id);
    check(`Original record resolves ${name}/${id}`, source);
    for (const [publicName, sourceName] of Object.entries(mappings[name])) equal(`Exact frozen field ${name}/${id}/${publicName}`, row[publicName], Number(source[sourceName]));
  }
}

function csvCommon(label, rows) {
  for (const [i, row] of rows.entries()) {
    equal(`${label}/${i} study`, row.study_id, dataset.studyId);
    equal(`${label}/${i} release`, row.data_release_id, DATA_RELEASE.dataReleaseId);
    equal(`${label}/${i} source IDs`, row.source_ids, dataset.sourceIds.join(';'));
    check(`${label}/${i} scope and null explanation`, row.scope.length > 30 && row.null_meaning.includes('unavailable'));
  }
}
const endpointNames = ['initial_shared', ...POLICIES];
let contexts = 0, retentionSelections = 0, csvDownloads = 0;
for (const seed of SEEDS) for (const endpoint of endpointNames) {
  contexts++;
  const context = selectUncertaintyContext(dataset, seed, endpoint, 1);
  const label = `${seed}/${endpoint}`;
  check(`${label} endpoint exists`, context.metrics);
  equal(`${label} context query endpoint`, context.queries, endpoint === 'initial_shared' ? 0 : 50);
  equal(`${label} one saved endpoint model`, dataset.evaluationMetrics.filter((row) => row.seed === seed && row.policy === endpoint && row.queries === context.queries).length, 1);
  equal(`${label} one split only`, context.metrics.seed, seed);
  equal(`${label} evaluation rows`, context.metrics.rows, 3418);
  equal(`${label} ten recorded retention steps`, context.risk.length, 10);
  equal(`${label} ten recorded deciles`, context.deciles.length, 10);
  equal(`${label} ordered deciles`, context.deciles.map((r) => r.decile), [1,2,3,4,5,6,7,8,9,10]);
  equal(`${label} decile rowcount reconstructed`, context.deciles.reduce((sum, r) => sum + r.rows, 0), context.metrics.rows);
  check(`${label} deciles differ by at most one row`, Math.max(...context.deciles.map((r) => r.rows)) - Math.min(...context.deciles.map((r) => r.rows)) === 1);
  for (const field of ['maeEVPerAtom', 'meanIntervalWidthEVPerAtom', 'interval90EmpiricalCoverage']) close(`${label} deciles reconstruct ${field}`, context.deciles.reduce((sum, r) => sum + r[field] * r.rows, 0) / context.metrics.rows, context.metrics[field]);
  const metricCsv = parseCsv(uncertaintyMetricsCsv(dataset, context, DATA_RELEASE.dataReleaseId)); csvDownloads++;
  equal(`${label} CSV one metrics row`, metricCsv.length, 1); csvCommon(`${label}/metrics`, metricCsv);
  equal(`${label} nominal CSV fraction`, Number(metricCsv[0].nominal_interval_coverage_fraction), .9);
  for (const [column, field] of Object.entries({ empirical_interval_coverage_fraction: 'interval90EmpiricalCoverage', mae_eV_per_atom: 'maeEVPerAtom', rmse_eV_per_atom: 'rmseEVPerAtom', mean_interval_width_eV_per_atom: 'meanIntervalWidthEVPerAtom', disagreement_absolute_error_spearman: 'disagreementAbsoluteErrorSpearman', calibration_scale_q: 'calibrationScale' })) equal(`${label} full precision CSV ${column}`, Number(metricCsv[0][column]), context.metrics[field]);
  for (const fraction of RETAINED_FRACTIONS) {
    retentionSelections++;
    const selected = selectUncertaintyContext(dataset, seed, endpoint, fraction), row = selected.retained;
    check(`${label}/${fraction} retained step resolves`, row);
    equal(`${label}/${fraction} actual rows ceil`, row.retainedRows, Math.ceil(context.metrics.rows * fraction));
    equal(`${label}/${fraction} actual fraction derives rows`, row.actualRetainedFraction, row.retainedRows / context.metrics.rows);
    equal(`${label}/${fraction} all-row MAE matches endpoint`, row.allRowsMaeEVPerAtom, context.metrics.maeEVPerAtom);
    close(`${label}/${fraction} error ratio matches`, row.maeRelativeToAllRows, row.maeEVPerAtom / row.allRowsMaeEVPerAtom);
    const csv = parseCsv(uncertaintyRiskCsv(dataset, selected, DATA_RELEASE.dataReleaseId)); csvDownloads++;
    equal(`${label}/${fraction} retention CSV ten rows`, csv.length, 10); csvCommon(`${label}/${fraction}/risk`, csv);
    equal(`${label}/${fraction} one selected CSV row`, csv.filter((r) => r.selected_retention_step === 'true').length, 1);
    equal(`${label}/${fraction} selected CSV step`, Number(csv.find((r) => r.selected_retention_step === 'true').requested_retained_fraction), fraction);
    for (const [i, record] of csv.entries()) {
      equal(`${label}/${fraction}/${i} CSV seed`, Number(record.seed), seed);
      equal(`${label}/${fraction}/${i} CSV endpoint`, record.endpoint, endpoint);
      equal(`${label}/${fraction}/${i} CSV query endpoint`, Number(record.completed_queries), context.queries);
      for (const [column, field] of Object.entries({ requested_retained_fraction: 'requestedRetainedFraction', retained_rows: 'retainedRows', actual_retained_fraction: 'actualRetainedFraction', mae_eV_per_atom: 'maeEVPerAtom', all_rows_mae_eV_per_atom: 'allRowsMaeEVPerAtom', mae_relative_to_all_rows: 'maeRelativeToAllRows', empirical_interval_coverage_fraction: 'interval90EmpiricalCoverage' })) equal(`${label}/${fraction}/${i} exact CSV ${column}`, Number(record[column]), context.risk[i][field]);
    }
  }
  const csv = parseCsv(uncertaintyDecilesCsv(dataset, context, DATA_RELEASE.dataReleaseId)); csvDownloads++;
  equal(`${label} CSV ten deciles`, csv.length, 10); csvCommon(`${label}/deciles`, csv);
  for (const [i, record] of csv.entries()) {
    equal(`${label}/${i} decile CSV context`, [Number(record.seed), record.endpoint, Number(record.completed_queries)], [seed, endpoint, context.queries]);
    for (const [column, field] of Object.entries({ uncertainty_decile: 'decile', rows: 'rows', mean_disagreement_eV_per_atom: 'meanDisagreementEVPerAtom', min_disagreement_eV_per_atom: 'minDisagreementEVPerAtom', max_disagreement_eV_per_atom: 'maxDisagreementEVPerAtom', mae_eV_per_atom: 'maeEVPerAtom', empirical_interval_coverage_fraction: 'interval90EmpiricalCoverage', mean_interval_width_eV_per_atom: 'meanIntervalWidthEVPerAtom' })) equal(`${label}/${i} exact decile CSV ${column}`, Number(record[column]), context.deciles[i][field]);
  }
}
equal('Exactly 30 saved endpoint contexts exercised', contexts, 30);
equal('All 300 selected retention filters exercised', retentionSelections, 300);
equal('Initial shared model occurs once per seed', dataset.evaluationMetrics.filter((r) => r.policy === 'initial_shared').length, 5);
const rolesCsv = parseCsv(uncertaintyRolesCsv(dataset, DATA_RELEASE.dataReleaseId)); csvDownloads++;
equal('Role CSV all ten rows', rolesCsv.length, 10); csvCommon('roles', rolesCsv);
for (const [i, row] of rolesCsv.entries()) {
  equal(`Role CSV ${i} identity`, [Number(row.seed), row.policy, row.selection_role], [dataset.roles[i].seed, 'full', dataset.roles[i].role]);
  for (const [column, field] of Object.entries({ queries: 'queries', historical_near_stable_hits: 'nearStableHits', precision_fraction: 'precision', reference_hull_hits: 'referenceHullHits', mean_predicted_mean_eV_per_atom: 'meanPredictedMeanEVPerAtom', mean_calibrated_radius_eV_per_atom: 'meanCalibratedRadiusEVPerAtom', mean_diversity_distance: 'meanDiversityDistance' })) equal(`Role CSV ${i} exact ${column}`, Number(row[column]), dataset.roles[i][field]);
}
for (const [role, expected] of [['conservative', [140, 175]], ['optimistic', [7, 75]]]) {
  const totals = roleTotals(dataset.roles, role);
  equal(`Pooled role ${role} event totals`, [totals.hits, totals.queries], expected);
  equal(`Pooled role ${role} event precision`, totals.precision, expected[0] / expected[1]);
  close(`Pooled role ${role} query weighted radius`, totals.meanCalibratedRadiusEVPerAtom,
    roles.filter((r) => r.role === role).reduce((sum, row) => sum + Number(row.mean_calibrated_radius_eV_atom) * Number(row.queries), 0) / expected[1]);
}
equal('Empty role group does not fabricate zero precision', roleTotals([], 'conservative').precision, null);
equal('Unavailable retention selection has null record', selectUncertaintyContext(dataset, SEEDS[0], 'full', .15).retained, null);
equal('Unavailable context does not fabricate endpoint', selectUncertaintyContext(dataset, 0, 'full', 1).metrics, null);
equal('Unavailable context CSV retains headers without fake rows', parseCsv(uncertaintyMetricsCsv(dataset, selectUncertaintyContext(dataset, 0, 'full', 1), DATA_RELEASE.dataReleaseId)).length, 0);
equal('All selection/CSV operations preserve source data', JSON.stringify(dataset), originalJson);
const after = {};
for (const [relative, expected] of Object.entries(before)) {
  after[relative] = sha(await fs.readFile(path.join(root, relative)));
  equal(`Frozen baseline after ${relative}`, after[relative], expected);
}
const report = { phase, feature: 'uncertainty explorer', status: 'passed', generatedAt: new Date().toISOString(),
  checksPassed: checks.length, checksFailed: 0, contexts, retentionSelections, csvDownloads,
  sourceCounts: { evaluationSnapshots: metrics.length, retentionRows: risk.length, decileRows: deciles.length, roleRows: roles.length },
  dataReleaseId: DATA_RELEASE.dataReleaseId, manifestSha256: DATA_RELEASE.manifestSha256,
  scope: 'Frozen-source and pure-display acceptance. Does not claim browser interaction, new model fits, inference or oracle queries.',
  newScientificRuns: 0, before, after, checks };
await fs.writeFile(path.join(website, `reports/${phase}_UNCERTAINTY_VALIDATION.json`), JSON.stringify(report, null, 2) + '\n');
console.log(`${phase} uncertainty: ${checks.length} checks passed; ${contexts} endpoint contexts, ${retentionSelections} retention selections, ${csvDownloads} CSV projections.`);
