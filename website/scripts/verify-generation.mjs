/** W5: check shipped generation filters/CSV projections against independent frozen CSVs. */
const phase = process.argv.includes('--phase=W6') ? 'W6' : 'W5';

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(website);
const model = await import(pathToFileURL(path.join(website, 'src/findings/generation.ts')));
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const checks = [];
const equal = (name, actual, expected) => { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); };
const check = (name, condition) => { assert.ok(condition, name); checks.push({ check: name, passed: true }); };
const close = (name, actual, expected) => check(name, Number.isFinite(actual) && Math.abs(actual - expected) < 1e-12);
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function parseCsv(text) {
  const rows = []; let row = [], value = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) { if (c === '"' && text[i + 1] === '"') { value += '"'; i++; } else if (c === '"') quoted = false; else value += c; }
    else if (c === '"' && value === '') quoted = true;
    else if (c === ',') { row.push(value); value = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(value); rows.push(row); row = []; value = ''; }
    else value += c;
  }
  assert.equal(quoted, false, 'CSV quote termination');
  if (value || row.length) { row.push(value); rows.push(row); }
  return rows;
}
function objects(text) { const [header, ...rows] = parseCsv(text.replace(/^\uFEFF/, '')); return rows.map(row => Object.fromEntries(header.map((name, i) => [name, row[i]]))); }
const report = JSON.parse(await fs.readFile(path.join(website, 'reports/W1_EXPORT.json')));
const baseline = JSON.parse(await fs.readFile(path.join(website, 'research_sources.json'))).baseline_integrity;
for (const [name, hash] of Object.entries(baseline)) equal(`Frozen baseline before checks ${name}`, sha(await fs.readFile(path.join(root, name))), hash);
const manifestBytes = await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath));
equal('Pinned manifest unchanged', sha(manifestBytes), DATA_RELEASE.manifestSha256);
const manifest = JSON.parse(manifestBytes);
async function dataset(name) { const entry = manifest.files.find(row => row.logicalName === name); assert.ok(entry); const bytes = await fs.readFile(path.join(website, 'public/research', entry.path)); equal(`Public data hash ${name}`, sha(bytes), entry.sha256); return JSON.parse(bytes); }
async function source(name) { const relative = `artifacts/phase6/structures/${name}.csv`; const bytes = await fs.readFile(path.join(root, relative)); equal(`Original frozen CSV ${name}`, sha(bytes), report.inputAllowlist[relative].sha256); return objects(bytes.toString('utf8')); }
const [data, provenance, registry, cohorts, draws, excluded, prototypes, energies, novelty, pairs] = await Promise.all([
  dataset('generation.json'), dataset('provenance.json'), dataset('structures/index.json'),
  source('generation_cohorts'), source('generation_draws'), source('excluded_larger_cell_diagnostics'),
  source('prototype_baselines'), source('relaxed_structures'), source('composition_novelty'), source('symmetry_energy_pairs'),
]);
const publicSources = new Set(provenance.sources.map(row => row.sourceId));
const boolean = value => value === 'True';
const nullable = value => value === '' ? null : +value;
function verifyProvenance(rows, scopePart) {
  for (const row of rows) {
    equal(`CSV study identity ${scopePart}`, row.study_id, data.studyId);
    equal(`CSV immutable release ${scopePart}`, row.data_release_id, DATA_RELEASE.dataReleaseId);
    check(`CSV null meaning ${scopePart}`, row.null_meaning.includes('unavailable') && row.null_meaning.includes('zero'));
    check(`CSV scope ${scopePart}`, row.scope.length > 20);
    check(`CSV no local paths ${scopePart}`, !/C:\\Users|file:\/\/|artifacts\//i.test(Object.values(row).join(' ')));
    for (const id of row.source_ids.split(';')) check(`CSV public source identity ${scopePart}/${id}`, publicSources.has(id));
  }
}
equal('Twelve independent original cohorts', cohorts.length, 12);
equal('All 88 draw rows retained', draws.length, 88);
equal('All 12 exclusions retained', excluded.length, 12);
equal('All six proposed formulas retained', novelty.length, 6);
equal('Four distinct prototype baselines', prototypes.length, 4);
equal('Eleven selected model records', energies.length, 11);
equal('Two selected model pairs', pairs.length, 2);
for (const row of data.cohorts) {
  const old = cohorts.find(item => item.scope === row.scope && item.formula === row.formula && (item.arm || null) === row.arm);
  check(`Cohort original identity ${row.scope}/${row.formula}/${row.arm}`, !!old);
  for (const [key, column] of Object.entries({ draws: 'draws', exactValid: 'exact_valid', exactValidUnique: 'exact_valid_unique', validRequestedSpacegroup: 'valid_requested_spacegroup', excludedLargerCellDiagnostics: 'excluded_larger_cell_diagnostics' })) equal(`Cohort source ${row.scope}/${row.formula}/${row.arm}/${key}`, row[key], +old[column]);
}
for (const scope of ['primary', 'supplementary']) for (const control of ['mgo_rocksalt', 'tio2_rutile']) {
  const selected = model.controlCohorts(data, scope, control);
  const expected = cohorts.filter(row => row.kind === 'control' && row.scope === (scope === 'primary' ? 'primary_first8' : 'supplementary_topup_only') && row.control === (scope === 'supplementary' ? 'mgo_rocksalt' : control));
  equal(`Two distinct arms ${scope}/${control}`, selected.length, 2);
  const rows = objects(model.generationCohortCsv(data, scope, control, DATA_RELEASE.dataReleaseId));
  equal(`Filtered CSV has only two current cohorts ${scope}/${control}`, rows.length, expected.length);
  rows.forEach((row, i) => {
    for (const key of ['control', 'arm', 'draws', 'exact_valid', 'exact_valid_unique', 'valid_requested_spacegroup', 'excluded_larger_cell_diagnostics']) equal(`Filtered cohort ${scope}/${control}/${i}/${key}`, row[key], expected[i][key]);
    equal(`Requested formula ${scope}/${control}/${i}`, row.requested_formula, expected[i].formula);
    equal(`Scope not pooled ${scope}/${control}/${i}`, row.cohort_scope, expected[i].scope);
    close(`Valid fraction ${scope}/${control}/${i}`, +row.valid_fraction, +expected[i].exact_valid / +expected[i].draws);
    close(`Unique yield ${scope}/${control}/${i}`, +row.unique_yield_fraction, +expected[i].exact_valid_unique / +expected[i].draws);
    equal(`Denominator remains eight or four ${scope}/${control}/${i}`, +row.draws, scope === 'primary' ? 8 : 4);
  });
  verifyProvenance(rows, `${scope}/${control}`);
}
equal('Zero denominator is null', model.fraction(0, 0), null);
const originalDraws = new Map(draws.map(row => [row.candidate_id, row]));
const drawMappings = {
  requestedAtoms: 'requested_n_atoms', atoms: 'n_atoms', requestedSpacegroup: 'requested_spacegroup', measuredSpacegroup: 'measured_spacegroup', minimumPeriodicDistanceAngstrom: 'minimum_periodic_distance_angstrom',
};
for (const row of data.draws) {
  const old = originalDraws.get(row.candidateId); check(`Draw original identity ${row.candidateId}`, !!old);
  for (const [key, column] of Object.entries(drawMappings)) equal(`Draw source number ${row.candidateId}/${key}`, row[key], nullable(old[column]));
  for (const [key, column] of Object.entries({ exactCountsMatch: 'exact_counts_match', geometryValid: 'geometry_valid', valid: 'valid', correctRatioGeometryWithinCapDiagnosticOnly: 'correct_ratio_geometry_within_cap_diagnostic_only', differentCellCountDiagnosticExcluded: 'different_cell_count_diagnostic_excluded', largerCellDiagnosticExcluded: 'larger_cell_diagnostic_excluded' })) equal(`Draw source flag ${row.candidateId}/${key}`, row[key], boolean(old[column]));
  equal(`Actual element counts ${row.candidateId}`, row.actualCounts, JSON.parse(old.actual_counts));
  equal(`Duplicate identity ${row.candidateId}`, row.duplicateOf, old.duplicate_of || null);
  equal(`Geometry source hash ${row.candidateId}`, row.geometrySourceSha256, old.source_sha256);
  const reasons = model.eligibilityReasons(row);
  equal(`Count mismatch explanation ${row.candidateId}`, reasons.includes('Requested element counts not reproduced'), !boolean(old.exact_counts_match));
  equal(`Geometry failure explanation ${row.candidateId}`, reasons.includes('Recorded geometry validity failed'), !boolean(old.geometry_valid));
  equal(`Exact eligibility explanation ${row.candidateId}`, reasons.includes('Exact-cell eligible'), boolean(old.valid));
}
let newAttempts = 0;
for (const proposal of novelty) {
  const selected = model.compositionDraws(data, proposal.formula), original = draws.filter(row => row.kind === 'new_composition' && row.formula === proposal.formula);
  equal(`Eight attempts ${proposal.formula}`, selected.length, 8); newAttempts += selected.length;
  equal(`Zero exact-cell eligible ${proposal.formula}`, selected.filter(row => row.valid).length, 0);
  equal(`All source attempt identities ${proposal.formula}`, selected.map(row => row.candidateId), original.map(row => row.candidate_id));
  const rows = objects(model.generationDrawCsv(data, selected, DATA_RELEASE.dataReleaseId, `${proposal.formula}; eight new-formula attempts`));
  equal(`Displayed CSV eight rows ${proposal.formula}`, rows.length, 8);
  rows.forEach((row, i) => {
    const old = original[i];
    for (const [key, column] of Object.entries({ candidate_id: 'candidate_id', requested_formula: 'formula', cohort_scope: 'scope', kind: 'kind', requested_atoms: 'requested_n_atoms', actual_atoms: 'n_atoms', requested_spacegroup: 'requested_spacegroup', measured_spacegroup: 'measured_spacegroup', minimum_periodic_distance_angstrom: 'minimum_periodic_distance_angstrom', geometry_source_sha256: 'source_sha256' })) equal(`Filtered draw CSV ${proposal.formula}/${i}/${key}`, row[key], old[column]);
    for (const [key, column] of Object.entries({ exact_counts_match: 'exact_counts_match', geometry_valid: 'geometry_valid', exact_cell_eligible: 'valid', larger_cell_diagnostic_excluded: 'larger_cell_diagnostic_excluded', different_cell_count_diagnostic_excluded: 'different_cell_count_diagnostic_excluded', correct_ratio_geometry_within_cap_diagnostic_only: 'correct_ratio_geometry_within_cap_diagnostic_only' })) equal(`Filtered draw flag ${proposal.formula}/${i}/${key}`, row[key], String(boolean(old[column])));
    equal(`No invented control ${proposal.formula}/${i}`, row.control, ''); equal(`No invented arm ${proposal.formula}/${i}`, row.arm, '');
    check(`No stability inference in eligibility ${proposal.formula}/${i}`, !/unstable|DFT|novel/.test(row.eligibility_reasons));
  });
  verifyProvenance(rows, proposal.formula);
}
equal('Global new-formula denominator stays 48', newAttempts, 48);
equal('Global exact-cell success remains zero', data.summary.newFormulaExactValid, 0);
const excludedRows = objects(model.generationDrawCsv(data, data.excluded, DATA_RELEASE.dataReleaseId, 'All twelve new-formula larger-cell diagnostics'));
equal('All twelve exclusions exported', excludedRows.length, 12);
equal('Exclusions preserve original identities', excludedRows.map(row => row.candidate_id), excluded.map(row => row.candidate_id));
for (const row of excludedRows) {
  equal(`Exclusion remains ineligible ${row.candidate_id}`, row.exact_cell_eligible, 'false');
  equal(`Exclusion remains diagnostic ${row.candidate_id}`, row.larger_cell_diagnostic_excluded, 'true');
  equal(`Exclusion correct-ratio diagnostic ${row.candidate_id}`, row.correct_ratio_geometry_within_cap_diagnostic_only, 'true');
  equal(`Exclusion count mismatch ${row.candidate_id}`, row.exact_counts_match, 'false');
  check(`Exclusion belongs to actual draw ${row.candidate_id}`, originalDraws.has(row.candidate_id));
}
verifyProvenance(excludedRows, 'all 12 exclusions');
equal('Unknown composition produces no invented rows', model.compositionDraws(data, 'NotAFormula'), []);
const originalEnergies = new Map(energies.map(row => [row.candidate_id, row]));
function verifyEnergyCsv(records, scope) {
  const rows = objects(model.modelEnergyCsv(data, records, DATA_RELEASE.dataReleaseId, scope));
  equal(`Energy CSV current row count ${scope}`, rows.length, records.length);
  rows.forEach((row, i) => {
    const old = originalEnergies.get(records[i].candidateId);
    for (const [key, column] of Object.entries({ candidate_id: 'candidate_id', role: 'role', control: 'control', arm: 'arm', final_formula: 'final_formula', physical_atoms: 'actual_atoms', CHGNet_energy_eV_per_atom: 'CHGNet_energy_eV_per_atom', optimizer_steps: 'optimizer_steps', filter_fmax_eV_per_angstrom: 'filter_fmax_eV_per_angstrom', final_spacegroup: 'final_spacegroup_symprec_0p01', same_composition_MP_geometries_tested: 'same_composition_MP_geometries_tested', geometry_source_sha256: 'source_sha256' })) equal(`Model source precision ${scope}/${i}/${key}`, row[key], old[column]);
    equal(`Model convergence ${scope}/${i}`, row.converged, String(boolean(old.converged)));
    equal(`Pinned geometry matches ${scope}/${i}`, row.matched_pinned_MP_geometry_ids, JSON.parse(old.matches_pinned_MP_same_composition_geometry_ids).join(';'));
    equal(`Model global novelty false ${scope}/${i}`, row.global_structure_novelty_established, 'false');
    equal(`Model stable-material result false ${scope}/${i}`, row.new_stable_material_established, 'false');
    equal(`Stage SG tolerance ${scope}/${i}`, row.spacegroup_symprec_angstrom, '0.01');
    check(`Saved model crystal link exists ${scope}/${i}`, registry.candidates.some(item => item.candidateId === row.candidate_id));
  });
  verifyProvenance(rows, scope); return rows;
}
const allModel = verifyEnergyCsv(data.relaxedStructures, 'All eleven selected model records; compare only within composition');
equal('Two recorded zero-step optimizer outcomes preserved', allModel.filter(row => row.optimizer_steps === '0').length, 2);
for (const pair of data.symmetryPairs) {
  const selected = model.selectedEnergyRows(data, pair.control), old = pairs.find(row => row.control === pair.control);
  equal(`Selected energy-pair identities ${pair.control}`, selected.map(row => row.candidateId), [old.nontrivial_candidate_id, old.p1_candidate_id]);
  equal(`One per arm ${pair.control}`, pair.quotaPerArm, 1);
  equal(`Pair pool source ${pair.control}`, pair.scope, old.scope);
  equal(`Pair no energy distribution ${pair.control}`, pair.energyDistributionEstablished, false);
  equal(`Pair no DFT stability ${pair.control}`, pair.dftStabilityComparison, false);
  close(`Pair saved full precision ${pair.control}`, pair.p1MinusNontrivialChgnetEVPerAtom, +old.P1_minus_nontrivial_CHGNet_eV_per_atom);
  close(`Pair recomputed within composition ${pair.control}`, pair.p1MinusNontrivialChgnetEVPerAtom, selected[1].chgnetEnergyEVPerAtom - selected[0].chgnetEnergyEVPerAtom);
  equal(`Pair same composition ${pair.control}`, selected[0].finalFormula, selected[1].finalFormula);
  verifyEnergyCsv(selected, `${pair.control}; ${pair.scope}; one selected structure per arm`);
}
const references = data.relaxedStructures.filter(row => ['reference_anatase', 'reference_rutile'].includes(row.candidateId));
verifyEnergyCsv(references, 'Anatase and rutile; within-TiO2 model comparison');
close('Anatase-minus-rutile source model ranking', data.summary.anataseMinusRutileChgnetEVPerAtom, references.find(row => row.candidateId === 'reference_anatase').chgnetEnergyEVPerAtom - references.find(row => row.candidateId === 'reference_rutile').chgnetEnergyEVPerAtom);
const protoRows = objects(model.prototypeCsv(data, DATA_RELEASE.dataReleaseId)); equal('All four prototype CSV rows', protoRows.length, 4);
protoRows.forEach((row, i) => {
  const old = prototypes[i];
  for (const key of ['candidate_id', 'parent_material_id', 'target_formula', 'CHGNet_energy_eV_per_atom']) equal(`Prototype source ${i}/${key}`, row[key], old[key]);
  equal(`Prototype actual atoms ${i}`, row.physical_atoms, old.atoms);
  equal(`Prototype remains separate ${i}`, originalDraws.has(row.candidate_id), false);
  equal(`Prototype no fresh DFT ${i}`, row.fresh_DFT_submitted, 'false');
  equal(`Prototype no stable material ${i}`, row.stable_material_established, 'false');
}); verifyProvenance(protoRows, 'four separate prototypes');
const noveltyRows = objects(model.compositionNoveltyCsv(data, DATA_RELEASE.dataReleaseId)); equal('All six novelty CSV rows', noveltyRows.length, 6);
noveltyRows.forEach((row, i) => {
  const old = novelty[i]; equal(`Novelty formula identity ${i}`, row.formula, old.formula);
  equal(`MP historical match count ${i}`, row.MP_matching_composition_records, old.mp_matching_composition_records);
  equal(`WBM historical match count ${i}`, row.WBM_matching_composition_records, old.wbm_matching_composition_records);
  equal(`Historical absence ${i}`, row.absent_from_both_pinned_snapshots, 'true');
  for (const key of ['global_composition_novelty_established', 'generator_pretraining_OOD_established', 'DFT_confirmed_stability']) equal(`No unsupported claim ${i}/${key}`, row[key], 'false');
  check(`MP pinned historical date ${i}`, row.MP_snapshot.includes('2022.10.28'));
  equal(`MP catalog count ${i}`, row.MP_catalog_records, '154718'); equal(`WBM catalog count ${i}`, row.WBM_catalog_records, '256963');
}); verifyProvenance(noveltyRows, 'six historical composition absences');
const sourceComponent = await fs.readFile(path.join(website, 'src/findings/GenerationFindings.tsx'), 'utf8');
for (const text of ['15/23 MgO', '34/44 TiO', '0/48', 'same fixed CrystalFormer architecture', 'No TiO', 'physically']) {
  // The physical-instability caveat is stated as "physical instability".
  check(`Visible scientific scope copy ${text}`, sourceComponent.includes(text === 'physically' ? 'physical instability' : text));
}
for (const logical of ['figures/generation.png', 'figures/model-energies.png']) check(`Saved figure is manifest bound ${logical}`, manifest.files.some(row => row.logicalName === logical));
for (const [name, hash] of Object.entries(baseline)) equal(`Frozen baseline after checks ${name}`, sha(await fs.readFile(path.join(root, name))), hash);
const output = { phase, component: 'generation', status: 'passed', checksPassed: checks.length, dataReleaseId: DATA_RELEASE.dataReleaseId, manifestSha256: DATA_RELEASE.manifestSha256, populations: { cohorts: 12, draws: 88, newFormulaAttempts: 48, exactCellValidNewFormulaAttempts: 0, excludedNewFormulaDiagnostics: 12, prototypes: 4, selectedModelRecords: 11, selectedEnergyPairs: 2, proposedCompositions: 6 }, checks, scope: 'Pure shipped filters/CSV projections checked independently against hash-verified original frozen CSVs. No generation, inference, relaxation, DFT, installation or public-data mutation. Browser interaction is separately recorded.' };
await fs.writeFile(path.join(website, `reports/${phase}_GENERATION_VALIDATION.json`), JSON.stringify(output, null, 2) + '\n');
console.log(`${phase} generation validation passed: ${checks.length} checks; 88 draws, 48 proposal attempts, 12 exclusions, 4 prototypes and 11 model records.`);
