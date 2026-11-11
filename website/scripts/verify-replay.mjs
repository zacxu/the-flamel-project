/** W3 acceptance: reconstruct the frozen histories independently and exercise the shipped pure model. */
const phase = process.argv.includes('--phase=W6') ? 'W6' : 'W3';

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(website);
const { buildReplaySeries, batchFor, displayQueries, comparisonCsv, queryCsv, csvCell, csvRows } =
  await import(pathToFileURL(path.join(website, 'src/replay/model.ts')));
const { DEFAULT_ROUTE, POLICIES, SEEDS, BUDGETS } =
  await import(pathToFileURL(path.join(website, 'src/state/route.ts')));
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const checks = [];
const equal = (name, actual, expected) => { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); };
const check = (name, condition) => { assert.ok(condition, name); checks.push({ check: name, passed: true }); };
const close = (name, actual, expected) => check(name, typeof actual === 'number' && Math.abs(actual - expected) < 1e-12);
const sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const manifestBytes = await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath));
equal('Pinned manifest matches the source release SHA-256', sha(manifestBytes), DATA_RELEASE.manifestSha256);
const manifest = JSON.parse(manifestBytes);
const read = async (logical) => {
  const item = manifest.files.find((entry) => entry.logicalName === logical);
  assert.ok(item, logical);
  const bytes = await fs.readFile(path.join(website, 'public/research', item.path));
  equal(`Public dataset source hash ${logical}`, sha(bytes), item.sha256);
  return JSON.parse(bytes);
};
const [curves, theme, provenance] = await Promise.all([read('replay/curves.json'), read('theme.json'), read('provenance.json')]);
const histories = await Promise.all(SEEDS.map((seed) => read(`replay/seed-${seed}.json`)));
const inventory = JSON.parse(await fs.readFile(path.join(website, 'research_sources.json')));
const exportReport = JSON.parse(await fs.readFile(path.join(website, 'reports/W1_EXPORT.json')));
const publicSourceIds = new Set(provenance.sources.map((source) => source.sourceId));
const before = {};
for (const [relative, expected] of Object.entries(inventory.baseline_integrity)) {
  before[relative] = sha(await fs.readFile(path.join(root, relative)));
  equal(`Frozen research baseline before replay checks: ${relative}`, before[relative], expected);
}

/** Independent small RFC 4180 parser used on both original CSVs and generated downloads. */
function parseCsv(text) {
  const rows = [];
  let row = [], value = '', quoted = false;
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (quoted) {
      if (char === '"' && text[index + 1] === '"') { value += '"'; index++; }
      else if (char === '"') quoted = false;
      else value += char;
    } else if (char === '"' && value === '') quoted = true;
    else if (char === ',') { row.push(value); value = ''; }
    else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[index + 1] === '\n') index++;
      row.push(value); rows.push(row); row = []; value = '';
    } else value += char;
  }
  assert.equal(quoted, false, 'CSV must terminate quoted values');
  if (value !== '' || row.length) { row.push(value); rows.push(row); }
  return rows;
}
const objects = (csv) => {
  const [header, ...rows] = parseCsv(csv.replace(/^\uFEFF/, ''));
  return rows.map((row) => Object.fromEntries(header.map((key, index) => [key, row[index]])));
};
async function sourceCsv(relative) {
  const bytes = await fs.readFile(path.join(root, relative));
  equal(`Original source remains hash-bound: ${relative}`, sha(bytes), exportReport.inputAllowlist[relative].sha256);
  return objects(bytes.toString('utf8'));
}
const [journal, originalCurves, originalEndpoints, metadata] = await Promise.all([
  sourceCsv('artifacts/phase4/replay/query_journal_all_seeds.csv'),
  sourceCsv('artifacts/phase6/uncertainty/learning_curves.csv'),
  sourceCsv('artifacts/phase6/uncertainty/policy_endpoints.csv'),
  sourceCsv('artifacts/phase2/features/row_metadata.csv'),
]);
equal('Exactly 1,250 frozen historical query events', journal.length, 1250);
equal('Exactly 125 original nonzero saved curve points', originalCurves.length, 125);
equal('Exactly 25 original endpoint rows', originalEndpoints.length, 25);
const metadataById = new Map(metadata.map((row) => [row.material_id, row]));
const distinctSelected = new Set();
let checkedHistories = 0, checkedBatches = 0, checkedEvents = 0;
for (const history of histories) for (const policy of POLICIES) {
  checkedHistories++;
  const records = [];
  const ids = new Set();
  for (let round = 1; round <= 5; round++) {
    checkedBatches++;
    const batch = batchFor(history, policy, round);
    check(`Saved batch exists ${history.seed}/${policy}/${round}`, batch !== null);
    equal(`Ten selected records ${history.seed}/${policy}/${round}`, batch.queries.length, 10);
    const sourceRows = journal.filter((row) => +row.seed === history.seed && row.policy === policy && +row.round === round);
    equal(`Ten original selected records ${history.seed}/${policy}/${round}`, sourceRows.length, 10);
    const hidden = displayQueries(batch, false), revealed = displayQueries(batch, true);
    equal(`Reveal returns the actual saved query projection ${history.seed}/${policy}/${round}`, revealed, batch.queries);
    const changedOutcomes = { ...batch, cumulativeAfterReveal: { impossibleTarget: 1234567.89 },
      queries: batch.queries.map((query) => ({ ...query, revealedLabelEVPerAtom: 1234567.89,
        nearStableHit: !query.nearStableHit, referenceHullHit: !query.referenceHullHit })) };
    equal(`Pre-reveal does not depend on targets, hits or cumulative outcomes ${history.seed}/${policy}/${round}`,
      displayQueries(changedOutcomes, false), hidden);
    check(`No cumulative or reveal identities in projected query data ${history.seed}/${policy}/${round}`,
      !JSON.stringify(hidden).includes('cumulative') && !JSON.stringify(hidden).includes('reveal_utc'));
    for (const [index, query] of batch.queries.entries()) {
      checkedEvents++;
      distinctSelected.add(query.materialId);
      check(`Material never repeats within history ${history.seed}/${policy}/${query.queryNumber}`, !ids.has(query.materialId));
      ids.add(query.materialId);
      const original = sourceRows[index], meta = metadataById.get(query.materialId);
      equal(`Original event identity ${history.seed}/${policy}/${query.queryNumber}`,
        [query.materialId, query.queryNumber, query.role], [original.material_id, +original.query_number, original.role]);
      equal(`Original event full precision ${history.seed}/${policy}/${query.queryNumber}`,
        [query.predictedMeanEVPerAtom, query.calibratedRadiusEVPerAtom, query.diversityAtSelection, query.score,
          query.revealedLabelEVPerAtom],
        [+original.predicted_mean_eV_atom, +original.calibrated_radius_eV_atom, +original.diversity_at_selection,
          original.score === '' ? null : +original.score, +original.label_eV_atom]);
      equal(`Metadata join ${history.seed}/${policy}/${query.queryNumber}`,
        [query.formula, query.reducedFormula, query.chemicalSystem, query.atoms],
        [meta.formula, meta.reduced_formula, meta.chemical_system, +meta.n_sites]);
      equal(`Inclusive historical thresholds ${history.seed}/${policy}/${query.queryNumber}`,
        [query.nearStableHit, query.referenceHullHit], [+original.label_eV_atom <= 0.05, +original.label_eV_atom <= 0]);
      equal(`All outcome fields hidden ${history.seed}/${policy}/${query.queryNumber}`,
        [hidden[index].revealedLabelEVPerAtom, hidden[index].nearStableHit, hidden[index].referenceHullHit], [null, null, null]);
      if (policy === 'random') equal(`Random score remains unavailable ${history.seed}/${query.queryNumber}`, hidden[index].score, null);
    }
    records.push(...batch.queries);
    const original = originalCurves.find((row) => +row.seed === history.seed && row.policy === policy && +row.queries === round * 10);
    const independentlyRebuilt = {
      queries: round * 10,
      nearStableHits: records.filter((query) => query.revealedLabelEVPerAtom <= 0.05).length,
      referenceHullHits: records.filter((query) => query.revealedLabelEVPerAtom <= 0).length,
      chemicalSystemCoverage: new Set(records.map((query) => query.chemicalSystem)).size,
    };
    equal(`Original intermediate cumulative result ${history.seed}/${policy}/${round}`, independentlyRebuilt,
      { queries: +original.queries, nearStableHits: +original.near_stable_hits,
        referenceHullHits: +original.reference_hull_hits, chemicalSystemCoverage: +original.chemical_system_coverage });
    equal(`Public batch cumulative result ${history.seed}/${policy}/${round}`, batch.cumulativeAfterReveal, independentlyRebuilt);
    equal(`Public curve cumulative result ${history.seed}/${policy}/${round}`,
      curves.points.find((point) => point.seed === history.seed && point.policy === policy && point.queries === round * 10),
      { seed: history.seed, policy, ...independentlyRebuilt });
    for (const labelsRevealed of [false, true]) {
      const csv = queryCsv(history, policy, round, labelsRevealed, DATA_RELEASE.dataReleaseId);
      const rows = objects(csv);
      equal(`Query CSV exactly the selected batch ${history.seed}/${policy}/${round}/${labelsRevealed}`, rows.length, 10);
      for (const [index, row] of rows.entries()) {
        const query = batch.queries[index];
        equal(`Query CSV scope ${history.seed}/${policy}/${query.queryNumber}/${labelsRevealed}`,
          [row.seed, row.policy, row.batch, row.query_number, row.material_id],
          [String(history.seed), policy, String(round), String(query.queryNumber), query.materialId]);
        equal(`Query CSV gated outcome ${history.seed}/${policy}/${query.queryNumber}/${labelsRevealed}`,
          [row.historical_target_eV_per_atom, row.historical_near_stable_hit, row.reference_hull_hit],
          labelsRevealed ? [String(query.revealedLabelEVPerAtom), String(query.nearStableHit), String(query.referenceHullHit)] : ['', '', '']);
        equal(`Query CSV exact prediction precision ${history.seed}/${policy}/${query.queryNumber}/${labelsRevealed}`,
          [row.predicted_mean_eV_per_atom, row.calibrated_radius_eV_per_atom, row.recorded_acquisition_score],
          [String(query.predictedMeanEVPerAtom), String(query.calibratedRadiusEVPerAtom), query.score === null ? '' : String(query.score)]);
        equal(`Query CSV label visibility ${history.seed}/${policy}/${query.queryNumber}/${labelsRevealed}`,
          row.label_visibility, labelsRevealed ? 'revealed' : 'hidden');
        equal(`Query CSV study/release/source identity ${history.seed}/${policy}/${query.queryNumber}/${labelsRevealed}`,
          [row.study_id, row.data_release_id, row.source_ids], [history.studyId, DATA_RELEASE.dataReleaseId, history.sourceIds.join(';')]);
      }
      check(`CSV teaches public-data reveal scope ${history.seed}/${policy}/${round}/${labelsRevealed}`,
        rows.every((row) => row.scope.includes('Teaching reveal only; outcomes exist in public static data.')));
    }
  }
  const endpoint = originalEndpoints.find((row) => +row.seed === history.seed && row.policy === policy);
  const final = curves.endpoints.find((row) => row.seed === history.seed && row.policy === policy);
  equal(`Original endpoint is reconstructed ${history.seed}/${policy}`,
    [final.nearStableHits, final.referenceHullHits, final.chemicalSystemCoverage, final.precisionAt50],
    [+endpoint.near_stable_hits, +endpoint.reference_hull_hits, +endpoint.chemical_system_coverage, +endpoint.precision_at_50]);
  check(`Every seed dataset source resolves ${history.seed}/${policy}`, history.sourceIds.every((id) => publicSourceIds.has(id)));
}
equal('All 25 recorded histories were reconstructed', checkedHistories, 25);
equal('All 125 batches were reconstructed', checkedBatches, 125);
equal('All 1,250 selected events were checked', checkedEvents, 1250);
equal('Exactly 720 distinct selected materials', distinctSelected.size, 720);
check('All curve sources resolve publicly', curves.sourceIds.every((id) => publicSourceIds.has(id)));

for (const mode of ['aggregate', 'seed']) for (const seed of SEEDS) for (const metric of ['hits', 'precision', 'systems']) {
  const selection = { mode, seed, policies: POLICIES };
  const series = buildReplaySeries(curves, theme, selection, metric);
  equal(`All five policy series ${mode}/${seed}/${metric}`, series.map((item) => item.policy), POLICIES);
  for (const item of series) {
    equal(`Accessible policy presentation colour and frozen label ${mode}/${seed}/${metric}/${item.policy}`,
      [item.label, item.colour], [theme.policyLabels[item.policy], ({ full: '#9B4275', uncertainty: '#8C6200', quality_diversity: '#007C5B' })[item.policy] ?? theme.policyColours[item.policy]]);
    equal(`Six exact boundaries ${mode}/${seed}/${metric}/${item.policy}`, item.points.map((point) => point.queries), BUDGETS);
    for (const point of item.points) {
      const key = `${mode}/${seed}/${metric}/${item.policy}/${point.queries}`;
      if (point.queries === 0) {
        equal(`Truthful zero origin ${key}`, point,
          { queries: 0, mean: metric === 'precision' ? null : 0,
            sampleStd: mode === 'aggregate' && metric !== 'precision' ? 0 : null,
            low: mode === 'aggregate' && metric !== 'precision' ? 0 : null,
            high: mode === 'aggregate' && metric !== 'precision' ? 0 : null });
        continue;
      }
      const original = originalCurves.filter((row) => row.policy === item.policy && +row.queries === point.queries &&
        (mode === 'aggregate' || +row.seed === seed));
      const values = original.map((row) => metric === 'precision' ? +row.near_stable_hits / +row.queries
        : metric === 'hits' ? +row.near_stable_hits : +row.chemical_system_coverage);
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      close(`Mean from split outcomes ${key}`, point.mean, mean);
      if (mode === 'seed') equal(`Single split has no aggregate band ${key}`,
        [point.sampleStd, point.low, point.high], [null, null, null]);
      else {
        // Independent second-moment formula verifies the n-1 denominator.
        const sampleStd = Math.sqrt(Math.max(0, (values.reduce((sum, value) => sum + value ** 2, 0) - values.length * mean ** 2) / 4));
        close(`Sample SD across five splits ${key}`, point.sampleStd, sampleStd);
        close(`Unclipped descriptive lower bound ${key}`, point.low, mean - sampleStd);
        close(`Unclipped descriptive upper bound ${key}`, point.high, mean + sampleStd);
      }
    }
  }
}

// Every allowed visibility set and completed budget is reflected in the actual download.
for (let mask = 1; mask < 2 ** POLICIES.length; mask++) {
  const policies = POLICIES.filter((_, index) => mask & (1 << index));
  for (const budget of BUDGETS) for (const mode of ['aggregate', 'seed']) {
    const state = { ...DEFAULT_ROUTE, view: 'replay', mode, seed: SEEDS[2], policies, policy: policies[0], budget };
    const rows = objects(comparisonCsv(curves, theme, state, DATA_RELEASE.dataReleaseId));
    const key = `${mask}/${budget}/${mode}`;
    equal(`Comparison CSV has only displayed boundary rows ${key}`, rows.length, policies.length * (budget / 10 + 1));
    check(`Comparison CSV contains only visible policies and completed budgets ${key}`,
      rows.every((row) => policies.includes(row.policy) && +row.completed_queries <= budget));
    equal(`Comparison CSV exact seed scope ${key}`,
      [...new Set(rows.map((row) => row.seed))], [mode === 'seed' ? String(SEEDS[2]) : '']);
    check(`Comparison CSV unit and source/release identity ${key}`,
      rows.every((row) => row.near_stable_threshold_eV_per_atom_inclusive === '0.05' &&
        row.reference_hull_threshold_eV_per_atom_inclusive === '0' && row.data_release_id === DATA_RELEASE.dataReleaseId &&
        row.study_id === curves.studyId && row.source_ids === curves.sourceIds.join(';')));
    for (const row of rows) {
      equal(`Comparison CSV identifies derived versus recorded origin ${key}/${row.policy}/${row.completed_queries}`,
        row.point_origin, +row.completed_queries === 0 ? 'derived_zero_state' : 'recorded_batch_boundary');
      if (+row.completed_queries === 0) equal(`Comparison zero precision unavailable ${key}/${row.policy}`,
        [row.precision_mean_fraction, row.precision_sample_sd_fraction], ['', '']);
      if (mode === 'seed') equal(`Comparison split SD unavailable ${key}/${row.policy}/${row.completed_queries}`,
        [row.historical_near_stable_hits_sample_sd, row.precision_sample_sd_fraction, row.chemical_system_coverage_sample_sd], ['', '', '']);
      const sourceRows = originalCurves.filter((point) => point.policy === row.policy &&
        +point.queries === +row.completed_queries && (mode === 'aggregate' || +point.seed === SEEDS[2]));
      for (const [field, sdField, sourceField, precisionMetric] of [
        ['historical_near_stable_hits_mean', 'historical_near_stable_hits_sample_sd', 'near_stable_hits', false],
        ['precision_mean_fraction', 'precision_sample_sd_fraction', 'near_stable_hits', true],
        ['chemical_system_coverage_mean', 'chemical_system_coverage_sample_sd', 'chemical_system_coverage', false],
      ]) {
        if (+row.completed_queries === 0) {
          equal(`Comparison zero metric ${key}/${row.policy}/${field}`, row[field], precisionMetric ? '' : '0');
          continue;
        }
        const values = sourceRows.map((point) => +point[sourceField] / (precisionMetric ? +point.queries : 1));
        const mean = values.reduce((a, b) => a + b, 0) / values.length;
        close(`Comparison CSV numerical source fidelity ${key}/${row.policy}/${row.completed_queries}/${field}`,
          +row[field], mean);
        if (mode === 'aggregate') {
          const sd = Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1));
          close(`Comparison CSV sample SD source fidelity ${key}/${row.policy}/${row.completed_queries}/${sdField}`,
            +row[sdField], sd);
        }
      }
    }
  }
}
const full = buildReplaySeries(curves, theme, { mode: 'aggregate', seed: SEEDS[0], policies: ['full'] }, 'hits')[0].points.at(-1);
const quality = buildReplaySeries(curves, theme, { mode: 'aggregate', seed: SEEDS[0], policies: ['quality'] }, 'hits')[0].points.at(-1);
close('Frozen negative finding: quality mean is 41.2/50', quality.mean, 41.2);
close('Frozen negative finding: full mean is 29.4/50', full.mean, 29.4);
check('Complete method is not presented as the hit-count winner', full.mean < quality.mean);
const altered = { ...curves, points: curves.points.filter((point) => !(point.seed === SEEDS[0] && point.policy === 'quality' && point.queries === 10)) };
assert.throws(() => buildReplaySeries(altered, theme, { mode: 'aggregate', seed: SEEDS[0], policies: ['quality'] }, 'hits'), /Expected one/);
check('Missing saved curve data fails instead of fabricating a zero', true);
const duplicated = { ...curves, points: [...curves.points, curves.points[0]] };
assert.throws(() => buildReplaySeries(duplicated, theme, { mode: 'aggregate', seed: SEEDS[0], policies: [curves.points[0].policy] }, 'hits'), /Expected one/);
check('Duplicate saved curve data fails instead of picking an arbitrary value', true);
equal('Unavailable policy history has no fabricated batch', batchFor({ ...histories[0], histories: [] }, 'full', 1), null);
assert.throws(() => queryCsv({ ...histories[0], histories: [] }, 'full', 1, false), /unavailable/);
check('Unavailable query export is an explicit error', true);
for (const value of ['=SUM(A1:A2)', '+command', '-formula', '@reference', '  =formula', '\t+command']) {
  check(`Spreadsheet string formula is neutralized: ${JSON.stringify(value)}`, csvCell(value).startsWith("'"));
}
equal('Negative numeric energy retains its exact signed numeric value', csvCell(-0.026843), '-0.026843');
equal('Empty random score stays empty', csvCell(null), '');
equal('False target is a real false value when revealed', csvCell(false), 'false');
for (const value of [NaN, Infinity, -Infinity]) assert.throws(() => csvCell(value), /finite/);
check('CSV refuses non-finite numerical values', true);
const special = ['Mg, O', 'a "quoted" formula', 'multiline\r\nvalue', '\u03b1-TiO2', 'normal', -1.2345678901234567, null];
equal('RFC 4180 unicode/commas/quotes/newline roundtrip', parseCsv(csvRows([special]))[0],
  ['Mg, O', 'a "quoted" formula', 'multiline\r\nvalue', '\u03b1-TiO2', 'normal', '-1.2345678901234567', '']);
check('CSV records use CRLF termination', comparisonCsv(curves, theme, DEFAULT_ROUTE).endsWith('\r\n'));
for (const [relative, expected] of Object.entries(before)) equal(`Frozen research baseline after replay checks: ${relative}`,
  sha(await fs.readFile(path.join(root, relative))), expected);
const report = { phase, scope: 'Pure replay model, original frozen CSV reconstruction, label-gated projection and displayed-data downloads',
  status: 'passed', generatedAt: new Date().toISOString(), checksPassed: checks.length,
  dataReleaseId: DATA_RELEASE.dataReleaseId, histories: checkedHistories, batches: checkedBatches,
  queryEvents: checkedEvents, distinctSelectedMaterials: distinctSelected.size,
  comparisonVisibilitySubsets: 31, comparisonBudgets: BUDGETS.length, preRevealBatches: checkedBatches,
  newResearchExperiments: 0, parentBaselineUnchanged: true, checks };
await fs.mkdir(path.join(website, 'reports'), { recursive: true });
await fs.writeFile(path.join(website, `reports/${phase}_REPLAY_VALIDATION.json`), JSON.stringify(report, null, 2) + '\n');
console.log(`${phase} replay verification passed: ${checks.length} checks; 25 histories, 125 batches, 1,250 original events.`);
