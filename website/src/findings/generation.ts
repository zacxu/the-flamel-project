import type { Control, GenerationCohort, GenerationDataset, GenerationDraw, RelaxedStructureRecord } from '../data/contracts.ts';
import { csvRows, type CsvValue } from '../replay/model.ts';

export type GenerationScope = 'primary' | 'supplementary';
export const controlLabel = (control: Control) => control === 'mgo_rocksalt' ? 'MgO' : 'TiO₂';
export const armLabel = (arm: string | null) => arm === 'nontrivial' ? 'Nontrivial SG conditioned' : arm === 'p1' ? 'P1 conditioned' : 'Composition proposal';
export const scopeLabel = (scope: GenerationScope) => scope === 'primary' ? 'Primary · first eight per arm' : 'Supplementary · four additional MgO draws per arm';
export const fraction = (count: number, denominator: number): number | null => denominator > 0 ? count / denominator : null;
export const countsText = (counts: Readonly<Record<string, number>>) => Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)).map(([element, count]) => `${element}:${count}`).join('; ');
export function controlCohorts(data: GenerationDataset, scope: GenerationScope, control: Control): readonly GenerationCohort[] {
  return data.cohorts.filter(row => row.kind === 'control' && row.scope === (scope === 'primary' ? 'primary_first8' : 'supplementary_topup_only') && row.control === (scope === 'supplementary' ? 'mgo_rocksalt' : control));
}
export function compositionDraws(data: GenerationDataset, formula: string): readonly GenerationDraw[] {
  return data.draws.filter(row => row.kind === 'new_composition' && row.formula === formula);
}
/** These explanations report the two saved eligibility flags, without inferring physical stability. */
export function eligibilityReasons(row: GenerationDraw): readonly string[] {
  const reasons: string[] = [];
  if (!row.exactCountsMatch) reasons.push('Requested element counts not reproduced');
  if (!row.geometryValid) reasons.push('Recorded geometry validity failed');
  if (!row.valid && reasons.length === 0) reasons.push('Recorded exact-cell eligibility failed');
  if (row.valid) reasons.push('Exact-cell eligible');
  return reasons;
}
export function selectedEnergyRows(data: GenerationDataset, control: Control): readonly RelaxedStructureRecord[] {
  const pair = data.symmetryPairs.find(row => row.control === control);
  return pair ? [pair.nontrivialCandidateId, pair.p1CandidateId].map(id => data.relaxedStructures.find(row => row.candidateId === id)).filter((row): row is RelaxedStructureRecord => !!row) : [];
}
const nullMeaning = 'Empty numeric or identifier fields mean unavailable or not applicable; zero is a recorded zero. Fractions use 0 to 1.';
const provenanceColumns = ['study_id', 'data_release_id', 'source_ids', 'null_meaning', 'scope'];
const provenance = (data: GenerationDataset, release: string, sources: readonly string[], scope: string): CsvValue[] => [data.studyId, release, sources.join(';'), nullMeaning, scope];
export function generationCohortCsv(data: GenerationDataset, scope: GenerationScope, control: Control, release: string): string {
  const rows: CsvValue[][] = [['cohort_scope', 'control', 'arm', 'requested_formula', 'draws', 'exact_valid', 'valid_fraction', 'exact_valid_unique', 'unique_yield_fraction', 'valid_requested_spacegroup', 'excluded_larger_cell_diagnostics', ...provenanceColumns]];
  for (const row of controlCohorts(data, scope, control)) rows.push([row.scope, row.control, row.arm, row.formula, row.draws, row.exactValid, fraction(row.exactValid, row.draws), row.exactValidUnique, fraction(row.exactValidUnique, row.draws), row.validRequestedSpacegroup, row.excludedLargerCellDiagnostics, ...provenance(data, release, ['generation_cohorts', 'generation_draws'], scopeLabel(scope) + '; same trained architecture, different sampling conditioning. Primary and supplementary denominators are separate.')]);
  return csvRows(rows);
}
export function generationDrawCsv(data: GenerationDataset, draws: readonly GenerationDraw[], release: string, scope: string): string {
  const rows: CsvValue[][] = [['candidate_id', 'requested_formula', 'cohort_scope', 'kind', 'control', 'arm', 'requested_atoms', 'actual_atoms', 'actual_element_counts', 'requested_spacegroup', 'measured_spacegroup', 'minimum_periodic_distance_angstrom', 'exact_counts_match', 'geometry_valid', 'exact_cell_eligible', 'eligibility_reasons', 'duplicate_of', 'correct_ratio_geometry_within_cap_diagnostic_only', 'different_cell_count_diagnostic_excluded', 'larger_cell_diagnostic_excluded', 'geometry_source_sha256', ...provenanceColumns]];
  for (const row of draws) rows.push([row.candidateId, row.formula, row.scope, row.kind, row.control, row.arm, row.requestedAtoms, row.atoms, countsText(row.actualCounts), row.requestedSpacegroup, row.measuredSpacegroup, row.minimumPeriodicDistanceAngstrom, row.exactCountsMatch, row.geometryValid, row.valid, eligibilityReasons(row).join('; '), row.duplicateOf, row.correctRatioGeometryWithinCapDiagnosticOnly, row.differentCellCountDiagnosticExcluded, row.largerCellDiagnosticExcluded, row.geometrySourceSha256, ...provenance(data, release, [row.sourceId, ...(scope === 'All twelve new-formula larger-cell diagnostics' ? ['excluded_diagnostics'] : [])], scope + '; representation/workload gate, not physical stability.')]);
  return csvRows(rows);
}
export function modelEnergyCsv(data: GenerationDataset, records: readonly RelaxedStructureRecord[], release: string, scope: string): string {
  const rows: CsvValue[][] = [['candidate_id', 'role', 'control', 'arm', 'final_formula', 'physical_atoms', 'CHGNet_energy_eV_per_atom', 'optimizer_steps', 'converged', 'filter_fmax_eV_per_angstrom', 'final_spacegroup', 'spacegroup_symprec_angstrom', 'matched_pinned_MP_geometry_ids', 'same_composition_MP_geometries_tested', 'global_structure_novelty_established', 'new_stable_material_established', 'geometry_source_id', 'geometry_source_sha256', ...provenanceColumns]];
  for (const row of records) rows.push([row.candidateId, row.role, row.control, row.arm, row.finalFormula, row.atoms, row.chgnetEnergyEVPerAtom, row.optimizerSteps, row.converged, row.filterFmaxEVPerAngstrom, row.finalSpacegroup, row.spacegroupSymprecAngstrom, row.matchesPinnedMpSameCompositionGeometryIds.join(';'), row.sameCompositionMpGeometriesTested, row.globalStructureNoveltyEstablished, row.newStableMaterialEstablished, row.geometrySourceId, row.geometrySourceSha256, ...provenance(data, release, [row.sourceId, ...(row.geometrySourceId ? [row.geometrySourceId] : [])], scope + '; CHGNet model predictions, not formation energies, DFT stability or a cross-composition ranking.')]);
  return csvRows(rows);
}
export function prototypeCsv(data: GenerationDataset, release: string): string {
  const rows: CsvValue[][] = [['candidate_id', 'parent_material_id', 'target_formula', 'physical_atoms', 'initial_geometry_valid', 'CHGNet_converged', 'final_spacegroup_symprec_0p01_angstrom', 'CHGNet_energy_eV_per_atom', 'fresh_DFT_submitted', 'stable_material_established', ...provenanceColumns]];
  for (const row of data.prototypes) rows.push([row.candidateId, row.parentMaterialId, row.targetFormula, row.atoms, row.initialGeometryValid, row.chgnetConverged, row.finalSpacegroup, row.chgnetEnergyEVPerAtom, row.freshDftSubmitted, row.stableMaterialEstablished, ...provenance(data, release, ['prototype_baselines', 'relaxed_structures'], 'Four prepared prototype substitutions, separate from CrystalFormer draws; no newly established stable material.')]);
  return csvRows(rows);
}
export function compositionNoveltyCsv(data: GenerationDataset, release: string): string {
  const rows: CsvValue[][] = [['formula', 'element_counts', 'MP_matching_composition_records', 'WBM_matching_composition_records', 'absent_from_both_pinned_snapshots', 'global_composition_novelty_established', 'generator_pretraining_OOD_established', 'DFT_confirmed_stability', 'MP_snapshot', 'WBM_snapshot', 'MP_catalog_records', 'MP_unique_compositions', 'WBM_catalog_records', 'WBM_unique_compositions', ...provenanceColumns]];
  for (const row of data.compositionNovelty) rows.push([row.formula, countsText(row.counts), row.mpMatchingCompositionRecords, row.wbmMatchingCompositionRecords, row.absentFromBothPinnedSnapshots, row.globalCompositionNoveltyEstablished, row.generatorPretrainingOodEstablished, row.dftConfirmedStability, data.catalogScope.mpSnapshot, data.catalogScope.wbmSnapshot, data.catalogScope.populations.mp.records, data.catalogScope.populations.mp.uniqueCompositions, data.catalogScope.populations.wbm.records, data.catalogScope.populations.wbm.uniqueCompositions, ...provenance(data, release, ['composition_novelty', 'structures_summary'], data.catalogScope.scope)]);
  return csvRows(rows);
}
