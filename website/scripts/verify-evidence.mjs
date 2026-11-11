/** W5 acceptance: compare the shipped evidence model and downloads with frozen original records. */
const phase = process.argv.includes('--phase=W6') ? 'W6' : 'W5';

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
const website = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(website);
const { DEFAULT_DFT_FILTERS, DFT_ROLES, DFT_PHASES, DFT_CALCULATIONS, DFT_STATUSES, filteredDftJobs,
  dftJobsCsv, DEFAULT_REFERENCE_FILTERS, filteredReferenceMemberships, referenceMembershipsCsv, claimsCsv } =
  await import(pathToFileURL(path.join(website, 'src/evidence/model.ts')));
const { DATA_RELEASE } = await import(pathToFileURL(path.join(website, 'src/data/release.ts')));
const checks = [];
const equal = (name, actual, expected) => { assert.deepEqual(actual, expected, name); checks.push({ check: name, passed: true }); };
const check = (name, condition) => { assert.ok(condition, name); checks.push({ check: name, passed: true }); };
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const manifestBytes = await fs.readFile(path.join(website, 'public', DATA_RELEASE.manifestPath));
equal('Pinned immutable release manifest hash', sha(manifestBytes), DATA_RELEASE.manifestSha256);
const manifest = JSON.parse(manifestBytes);
async function readDataset(logical) {
  const entry = manifest.files.find(item => item.logicalName === logical);
  check(`Dataset manifest entry ${logical}`, !!entry);
  const bytes = await fs.readFile(path.join(website, 'public/research', entry.path));
  equal(`Dataset hash ${logical}`, sha(bytes), entry.sha256);
  return JSON.parse(bytes);
}
const [dft, summary, provenance] = await Promise.all(['dft.json', 'summary.json', 'provenance.json'].map(readDataset));
const releaseId = DATA_RELEASE.dataReleaseId;
const sourceIds = new Set(provenance.sources.map(source => source.sourceId));
const inventory = JSON.parse(await fs.readFile(path.join(website, 'research_sources.json')));
const exportReport = JSON.parse(await fs.readFile(path.join(website, 'reports/W1_EXPORT.json')));
const originalHashes = {};
for (const [relative, expected] of Object.entries(inventory.baseline_integrity)) {
  originalHashes[relative] = sha(await fs.readFile(path.join(root, relative)));
  equal(`Frozen baseline before evidence checks ${relative}`, originalHashes[relative], expected);
}

// Independent RFC 4180 parser, including escaped quotes/newlines and optional UTF-8 BOM.
function parseCsv(text) {
  const rows = []; let row = [], value = '', quoted = false;
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
  assert.equal(quoted, false, 'CSV quote termination');
  if (value !== '' || row.length) { row.push(value); rows.push(row); }
  return rows;
}
function objects(csv) {
  const [header, ...rows] = parseCsv(csv.replace(/^\uFEFF/, ''));
  for (const row of rows) assert.equal(row.length, header.length, 'Every exported row has the complete header width');
  return { header, rows: rows.map(row => Object.fromEntries(header.map((key, index) => [key, row[index]]))) };
}
async function source(relative, json = false) {
  const bytes = await fs.readFile(path.join(root, relative));
  const entry = exportReport.inputAllowlist[relative];
  check(`Original source allowlist ${relative}`, !!entry);
  equal(`Original source hash ${relative}`, sha(bytes), entry.sha256);
  originalHashes[relative] = sha(bytes);
  return json ? JSON.parse(bytes) : objects(bytes.toString('utf8')).rows;
}
const [jobs, references, missing, originalClaims, evidence] = await Promise.all([
  source('artifacts/phase6/evidence/fresh_DFT_evidence_table.csv'),
  source('artifacts/phase6/evidence/reference_inventory_completeness.csv'),
  source('artifacts/phase6/evidence/missing_reference_inventory.csv'),
  source('artifacts/phase6/evidence/claim_matrix.csv'),
  source('artifacts/phase6/evidence/summary.json', true),
]);
const numberOrNull = value => value === '' ? null : +value;
const truth = value => value === 'True';
const expectedJob = row => {
  const sourceResult = exportReport.inputAllowlist[row.source_result];
  return { jobId: row.job_id, phase: +row.phase, role: row.role, formula: row.formula, atoms: +row.n_atoms,
    calculation: row.calculation, exitCode: numberOrNull(row.exit_code), jobDone: truth(row.JOB_DONE),
    terminalScfAccepted: truth(row.terminal_SCF_accepted), stationaryAtThisSetting: truth(row.stationary_at_this_setting),
    acceptedWithFinalGeometrySensitivity: truth(row.accepted_with_final_geometry_sensitivity),
    energyEVPerAtom: numberOrNull(row.energy_eV_per_atom), maxForceEVPerAngstrom: numberOrNull(row.max_force_eV_A),
    maxFullStressKbar: numberOrNull(row.max_full_stress_kbar), cutoffRy: +row.cutoff_Ry,
    densityCutoffRy: +row.density_cutoff_Ry, kMesh: row.k_mesh.split('x').map(Number),
    elapsedWallSeconds: +row.elapsed_wall_seconds, evidenceLevel: row.evidence_level,
    sourceId: 'dft_jobs', resultSourceId: sourceResult?.sourceId ?? null };
};
const expectedReference = row => ({ inventorySystem: row.inventory_system, materialId: row.material_id,
  formula: row.formula, chemicalSystem: row.chemical_system, executionAtoms: +row.execution_n_sites,
  spinReviewRequired: truth(row.spin_review_required), expensiveReferenceFlag: truth(row.expensive_reference_flag),
  elementalEndpointEntry: truth(row.elemental_endpoint_entry), acceptedFreshCompatibleQe: truth(row.accepted_fresh_compatible_QE),
  acceptedJobId: row.accepted_job_id || null, status: row.status, blocksFullInventoryHull: truth(row.blocks_full_inventory_hull) });
equal('All nineteen jobs retain all original fields and provenance', dft.jobs, jobs.map(expectedJob));
equal('All 218 original inventory memberships retain overlapping identities', dft.referenceMemberships, references.map(expectedReference));
equal('All 215 missing memberships remain missing', dft.missingMemberships, missing.map(expectedReference));
equal('Ten claim matrix rows retain their original status, scope and limits', summary.claims,
  originalClaims.map(row => ({ claim: row.claim, status: row.status, scope: row.scope, limitation: row.limitation })));
equal('All original jobs are visible by default', filteredDftJobs(dft, DEFAULT_DFT_FILTERS), dft.jobs);
equal('All original memberships are visible by default', filteredReferenceMemberships(dft, DEFAULT_REFERENCE_FILTERS), dft.referenceMemberships);

equal('Role selector exposes exactly the frozen roles', [...DFT_ROLES].sort(), [...new Set(jobs.map(row => row.role))].sort());
equal('Phase selector exposes exactly phases 1, 3, 4 and 5', [...DFT_PHASES], [...new Set(jobs.map(row => row.phase))].sort());
equal('Calculation selector exposes exactly the frozen calculation types', [...DFT_CALCULATIONS].sort(), [...new Set(jobs.map(row => row.calculation))].sort());
equal('Status selector exposes every original evidence status', [...DFT_STATUSES].sort(), [...new Set(jobs.map(row => row.evidence_level))].sort());
const expectedJobCsv = (job, filters) => ({ data_release_id: releaseId, study_id: dft.studyId, job_id: job.jobId,
  research_phase: String(job.phase), role: job.role, formula: job.formula, physical_atoms: String(job.atoms),
  calculation: job.calculation, exit_code: job.exitCode === null ? '' : String(job.exitCode), job_done: String(job.jobDone),
  terminal_scf_accepted: String(job.terminalScfAccepted), stationary_at_this_setting: String(job.stationaryAtThisSetting),
  accepted_with_final_geometry_sensitivity: String(job.acceptedWithFinalGeometrySensitivity),
  energy_eV_per_atom: job.energyEVPerAtom === null ? '' : String(job.energyEVPerAtom),
  max_force_eV_per_angstrom: job.maxForceEVPerAngstrom === null ? '' : String(job.maxForceEVPerAngstrom),
  max_full_stress_kbar: job.maxFullStressKbar === null ? '' : String(job.maxFullStressKbar),
  wavefunction_cutoff_Ry: String(job.cutoffRy), density_cutoff_Ry: String(job.densityCutoffRy),
  k_mesh: job.kMesh.join('x'), elapsed_wall_seconds: String(job.elapsedWallSeconds), evidence_level: job.evidenceLevel,
  source_id: job.sourceId, result_source_id: job.resultSourceId ?? '', filter_role: filters.role,
  filter_phase: filters.phase, filter_calculation: filters.calculation, filter_evidence_level: filters.status,
  null_value_meaning: 'Empty means unavailable, not zero',
  scope: 'Recorded QE attempts; process completion, SCF, stationarity and finite checks are separate; no full hull or new stable material' });
let jobFilterCombinations = 0, exportedJobRows = 0;
for (const role of ['all', ...DFT_ROLES]) for (const phase of ['all', ...DFT_PHASES])
  for (const calculation of ['all', ...DFT_CALCULATIONS]) for (const status of ['all', ...DFT_STATUSES]) {
    const filters = { role, phase, calculation, status }; const key = `${role}/${phase}/${calculation}/${status}`;
    const expected = jobs.filter(row => (role === 'all' || row.role === role) && (phase === 'all' || row.phase === phase)
      && (calculation === 'all' || row.calculation === calculation) && (status === 'all' || row.evidence_level === status)).map(expectedJob);
    const actual = filteredDftJobs(dft, filters); jobFilterCombinations++;
    equal(`Exact identities and all fields for job filter ${key}`, actual, expected);
    const csv = objects(dftJobsCsv(dft, filters, releaseId)); exportedJobRows += csv.rows.length;
    equal(`Complete precision/null/unit/provenance CSV for job filter ${key}`, csv.rows, expected.map(row => expectedJobCsv(row, filters)));
    equal(`CSV retains all 29 headers including zero-result filter ${key}`, csv.header.length, 29);
  }

const expectedReferenceCsv = (row, filters) => ({ data_release_id: releaseId, study_id: dft.studyId,
  inventory_system: row.inventorySystem, material_id: row.materialId, formula: row.formula,
  chemical_system: row.chemicalSystem, execution_physical_atoms: String(row.executionAtoms),
  spin_review_required: String(row.spinReviewRequired), expensive_reference_flag: String(row.expensiveReferenceFlag),
  elemental_endpoint_entry: String(row.elementalEndpointEntry), accepted_fresh_compatible_QE: String(row.acceptedFreshCompatibleQe),
  accepted_job_id: row.acceptedJobId ?? '', status: row.status, blocks_full_inventory_hull: String(row.blocksFullInventoryHull),
  source_ids: row.acceptedFreshCompatibleQe ? 'reference_inventory|evidence_summary' : 'reference_inventory|missing_references|evidence_summary',
  filter_system: filters.system, filter_status: filters.status, filter_elementals_only: String(filters.elementalsOnly),
  filter_spin_only: String(filters.spinOnly), null_value_meaning: 'Empty means unavailable, not zero',
  scope: 'One row per inventory-system membership; systems overlap; no complete compatible reference hull' });
let referenceFilterCombinations = 0, exportedReferenceRows = 0;
for (const system of ['all', 'Ca-Mg-O', 'Mg-O']) for (const status of ['all', 'accepted', 'missing'])
  for (const elementalsOnly of [false, true]) for (const spinOnly of [false, true]) {
    const filters = { system, status, elementalsOnly, spinOnly };
    const key = `${system}/${status}/${elementalsOnly}/${spinOnly}`;
    const expected = references.filter(row => (system === 'all' || row.inventory_system === system)
      && (status === 'all' || truth(row.accepted_fresh_compatible_QE) === (status === 'accepted'))
      && (!elementalsOnly || truth(row.elemental_endpoint_entry)) && (!spinOnly || truth(row.spin_review_required))).map(expectedReference);
    referenceFilterCombinations++;
    equal(`Exact memberships and independent elemental/spin filters ${key}`, filteredReferenceMemberships(dft, filters), expected);
    const csv = objects(referenceMembershipsCsv(dft, filters, releaseId)); exportedReferenceRows += csv.rows.length;
    equal(`Reference CSV retains overlapping memberships and every field ${key}`, csv.rows, expected.map(row => expectedReferenceCsv(row, filters)));
    equal(`Reference CSV has all 21 headers even if empty ${key}`, csv.header.length, 21);
  }

equal('Three accepted relaxed geometries remain distinct', dft.acceptedGeometries.length, 3);
equal('The accepted geometry job IDs are exactly the three finite-checked vc-relax jobs',
  dft.acceptedGeometries.map(row => row.acceptedJobId).sort(), dft.jobs.filter(job => job.acceptedWithFinalGeometrySensitivity).map(job => job.jobId).sort());
for (const geometry of dft.acceptedGeometries) {
  const row = evidence.fresh_QE_relaxed_geometries_with_final_finite_checks.find(item => item.accepted_job_id === geometry.acceptedJobId);
  equal(`All accepted geometry finite checks match the frozen summary ${geometry.acceptedJobId}`, geometry,
    { acceptedJobId: row.accepted_job_id, energyEVPerAtom: row.energy_eV_atom, maxForceEVPerAngstrom: row.force_eV_A,
      maxFullStressKbar: row.full_stress_kbar, cutoffShiftEVPerAtom: row.cutoff_shift_eV_atom, kpointShiftEVPerAtom: row.kpoint_shift_eV_atom });
}
const acceptedMemberships = dft.referenceMemberships.filter(row => row.acceptedFreshCompatibleQe);
equal('Three accepted memberships represent exactly two source-reference material IDs',
  [acceptedMemberships.length, new Set(acceptedMemberships.map(row => row.materialId)).size], [3, 2]);
equal('Generated MgO never counts as an extra reference inventory membership',
  acceptedMemberships.some(row => row.acceptedJobId === 'p3_candidate_mgo_fallback_90'), false);
for (const system of ['Ca-Mg-O', 'Mg-O']) {
  const rows = dft.referenceMemberships.filter(row => row.inventorySystem === system);
  const absent = rows.filter(row => !row.acceptedFreshCompatibleQe);
  const coverage = dft.coverage[system];
  equal(`All coverage values independently reconstructed from memberships ${system}`, coverage,
    { frozenEntries: rows.length, acceptedFreshCompatibleQe: rows.length - absent.length, missing: absent.length,
      fullInventoryComplete: false, missingSpinReviewEntries: absent.filter(row => row.spinReviewRequired).length,
      missingElementalEntries: absent.filter(row => row.elementalEndpointEntry).length });
}
equal('Membership totals are 218 entries and 215 missing, with system overlap retained',
  [dft.referenceMemberships.length, dft.missingMemberships.length], [218, 215]);
check('Memberships include overlapping material IDs across systems', new Set(dft.referenceMemberships.map(row => row.materialId)).size < 218);
const incomplete = dft.jobs.find(row => row.role === 'perturbation');
equal('900-second perturbation is process-complete but has no accepted terminal energy/force/stress',
  [incomplete.elapsedWallSeconds >= 900, incomplete.jobDone, incomplete.terminalScfAccepted,
    incomplete.stationaryAtThisSetting, incomplete.acceptedWithFinalGeometrySensitivity,
    incomplete.energyEVPerAtom, incomplete.maxForceEVPerAngstrom, incomplete.maxFullStressKbar],
  [true, true, false, false, false, null, null, null]);
equal('Readiness pilot force/stress are unavailable, not zero',
  [dft.jobs[0].maxForceEVPerAngstrom, dft.jobs[0].maxFullStressKbar, dft.jobs[0].acceptedWithFinalGeometrySensitivity], [null, null, false]);
check('SCF accepted is insufficient for independent stationarity', dft.jobs.some(job => job.terminalScfAccepted && !job.stationaryAtThisSetting));
check('Stationary setting is insufficient for final geometry finite sensitivity acceptance',
  dft.jobs.some(job => job.stationaryAtThisSetting && !job.acceptedWithFinalGeometrySensitivity));
equal('Known-control candidate/reference difference retains source full precision',
  dft.knownMgoControl.candidateMinusReferenceEVPerAtom, evidence.known_MgO_candidate_minus_reference_eV_atom);
equal('Known-control ordering remains unresolved', dft.knownMgoControl.energyOrderingResolved, false);
check('Raw MgO difference is below each accepted MgO cutoff sensitivity shift',
  dft.acceptedGeometries.filter(row => row.acceptedJobId.includes('mgo')).every(row =>
    Math.abs(dft.knownMgoControl.candidateMinusReferenceEVPerAtom) < row.cutoffShiftEVPerAtom));
equal('Finite check interpretation remains a measured setting sensitivity, not a rigorous DFT error bound',
  dft.finiteCheckScope, evidence.finite_check_scope);
equal('No perturbation, phonon, complete hull, or new-stable-material claim',
  [dft.perturbationValidationComplete, dft.phononCalculationPerformed, dft.fullHullEstablished, dft.newStableMaterialEstablished],
  [false, false, false, false]);
equal('Reaction is an available reference anchor, with no candidate or reaction energy',
  [dft.reaction.candidateEnergyAvailable, dft.reaction.reactionEnergyAvailable], [false, false]);
for (const job of dft.jobs) {
  check(`Public source ID resolves for job ${job.jobId}`, sourceIds.has(job.sourceId));
  check(`Result source ID is public or explicitly unavailable ${job.jobId}`, job.resultSourceId === null || sourceIds.has(job.resultSourceId));
  const original = jobs.find(row => row.job_id === job.jobId);
  if (job.resultSourceId !== null) {
    const bytes = await fs.readFile(path.join(root, original.source_result));
    equal(`Job result original hash ${job.jobId}`, sha(bytes), exportReport.inputAllowlist[original.source_result].sha256);
    originalHashes[original.source_result] = sha(bytes);
  }
}
const matrixCsv = objects(claimsCsv(summary.claims, releaseId, ['claim_matrix']));
equal('Claim CSV preserves every row with exact claim/status/scope/limitation and source ID', matrixCsv.rows,
  originalClaims.map(row => ({ data_release_id: releaseId, claim: row.claim, status: row.status,
    measured_scope: row.scope, limitation: row.limitation, source_ids: 'claim_matrix',
    scope: 'Frozen study claims with their measured scope and limits; no new website experiments' })));
const adversarial = objects(claimsCsv([{ claim: '=SUM(A1:A2)', status: 'has,comma', scope: 'line\nbreak', limitation: 'a "quote"' }], releaseId));
equal('Shared RFC 4180 writer protects spreadsheet strings without corrupting scientific number signs',
  adversarial.rows[0].claim, "'=SUM(A1:A2)");
equal('Claim CSV quotes comma/newline/quote fields losslessly',
  [adversarial.rows[0].status, adversarial.rows[0].measured_scope, adversarial.rows[0].limitation], ['has,comma', 'line\nbreak', 'a "quote"']);
for (const [relative, expected] of Object.entries(originalHashes))
  equal(`Frozen original remains unchanged after all checks ${relative}`, sha(await fs.readFile(path.join(root, relative))), expected);

const report = { phase, status: 'passed', scope: 'Read-only verification of evidence filters/CSV against original frozen records; no scientific compute',
  createdUtc: new Date().toISOString(), dataReleaseId: releaseId, manifestSha256: DATA_RELEASE.manifestSha256,
  totals: { jobs: jobs.length, memberships: references.length, missingMemberships: missing.length, acceptedGeometries: 3,
    acceptedSourceReferenceIds: 2, claimRows: originalClaims.length, jobFilterCombinations, referenceFilterCombinations,
    checkedCsvJobRows: exportedJobRows, checkedCsvMembershipRows: exportedReferenceRows },
  checksPassed: checks.length, checksTotal: checks.length, failedChecks: [], originalSourcesUnchanged: true,
  newExperiments: 0, checks };
await fs.writeFile(path.join(website, `reports/${phase}_EVIDENCE_VALIDATION.json`), JSON.stringify(report, null, 2) + '\n');
console.log(`${phase} evidence validation passed: ${checks.length} checks; ${jobFilterCombinations} job filters; ${referenceFilterCombinations} membership filters.`);
