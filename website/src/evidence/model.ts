import type { ClaimMatrixRow, DftDataset, DftEvidenceLevel, DftJob, InventorySystem,
  ReferenceMembership, SourceId } from '../data/contracts.ts';
import { csvRows } from '../replay/model.ts';

export const DFT_ROLES = ['known_MgO_engine_pilot', 'candidate', 'perturbation', 'reference', 'sensitivity'] as const;
export const DFT_PHASES = ['1', '3', '4', '5'] as const;
export const DFT_CALCULATIONS = ['scf', 'vc-relax'] as const;
export const DFT_STATUSES = ['fixed_geometry_engine_readiness_only',
  'accepted_relaxed_geometry_with_finite_sensitivity', 'fixed_geometry_SCF_sensitivity_only',
  'SCF_passed_independent_stationarity_failed', 'preliminary_stationary_setting_only',
  'incomplete_terminal_SCF_no_accepted_final_energy'] as const satisfies readonly DftEvidenceLevel[];

export interface DftFilters {
  readonly role: 'all' | DftJob['role'];
  readonly phase: 'all' | typeof DFT_PHASES[number];
  readonly calculation: 'all' | DftJob['calculation'];
  readonly status: 'all' | DftEvidenceLevel;
}
export const DEFAULT_DFT_FILTERS: DftFilters = { role: 'all', phase: 'all', calculation: 'all', status: 'all' };

/** Filtering preserves original job order, identity and independent acceptance fields. */
export function filteredDftJobs(data: DftDataset, filters: DftFilters): DftJob[] {
  return data.jobs.filter(job => (filters.role === 'all' || job.role === filters.role)
    && (filters.phase === 'all' || String(job.phase) === filters.phase)
    && (filters.calculation === 'all' || job.calculation === filters.calculation)
    && (filters.status === 'all' || job.evidenceLevel === filters.status));
}

/** CSV contains each acceptance layer separately; missing terminal measurements stay empty. */
export function dftJobsCsv(data: DftDataset, filters: DftFilters, dataReleaseId: string): string {
  return csvRows([['data_release_id', 'study_id', 'job_id', 'research_phase', 'role', 'formula',
    'physical_atoms', 'calculation', 'exit_code', 'job_done', 'terminal_scf_accepted',
    'stationary_at_this_setting', 'accepted_with_final_geometry_sensitivity', 'energy_eV_per_atom',
    'max_force_eV_per_angstrom', 'max_full_stress_kbar', 'wavefunction_cutoff_Ry', 'density_cutoff_Ry',
    'k_mesh', 'elapsed_wall_seconds', 'evidence_level', 'source_id', 'result_source_id',
    'filter_role', 'filter_phase', 'filter_calculation', 'filter_evidence_level', 'null_value_meaning', 'scope'],
  ...filteredDftJobs(data, filters).map(job => [dataReleaseId, data.studyId, job.jobId, job.phase,
    job.role, job.formula, job.atoms, job.calculation, job.exitCode, job.jobDone, job.terminalScfAccepted,
    job.stationaryAtThisSetting, job.acceptedWithFinalGeometrySensitivity, job.energyEVPerAtom,
    job.maxForceEVPerAngstrom, job.maxFullStressKbar, job.cutoffRy, job.densityCutoffRy,
    job.kMesh.join('x'), job.elapsedWallSeconds, job.evidenceLevel, job.sourceId, job.resultSourceId,
    filters.role, filters.phase, filters.calculation, filters.status, 'Empty means unavailable, not zero',
    'Recorded QE attempts; process completion, SCF, stationarity and finite checks are separate; no full hull or new stable material'])]);
}

export interface ReferenceFilters {
  readonly system: 'all' | InventorySystem;
  readonly status: 'all' | 'accepted' | 'missing';
  readonly elementalsOnly: boolean;
  readonly spinOnly: boolean;
}
export const DEFAULT_REFERENCE_FILTERS: ReferenceFilters = {
  system: 'all', status: 'all', elementalsOnly: false, spinOnly: false,
};

/** Each row is one system membership. Overlapping material IDs must not be deduplicated. */
export function filteredReferenceMemberships(data: DftDataset, filters: ReferenceFilters): ReferenceMembership[] {
  return data.referenceMemberships.filter(row => (filters.system === 'all' || row.inventorySystem === filters.system)
    && (filters.status === 'all' || row.acceptedFreshCompatibleQe === (filters.status === 'accepted'))
    && (!filters.elementalsOnly || row.elementalEndpointEntry)
    && (!filters.spinOnly || row.spinReviewRequired));
}

export function referenceMembershipsCsv(data: DftDataset, filters: ReferenceFilters, dataReleaseId: string): string {
  return csvRows([['data_release_id', 'study_id', 'inventory_system', 'material_id', 'formula',
    'chemical_system', 'execution_physical_atoms', 'spin_review_required', 'expensive_reference_flag',
    'elemental_endpoint_entry', 'accepted_fresh_compatible_QE', 'accepted_job_id', 'status',
    'blocks_full_inventory_hull', 'source_ids', 'filter_system', 'filter_status', 'filter_elementals_only',
    'filter_spin_only', 'null_value_meaning', 'scope'],
  ...filteredReferenceMemberships(data, filters).map(row => [dataReleaseId, data.studyId, row.inventorySystem,
    row.materialId, row.formula, row.chemicalSystem, row.executionAtoms, row.spinReviewRequired,
    row.expensiveReferenceFlag, row.elementalEndpointEntry, row.acceptedFreshCompatibleQe, row.acceptedJobId,
    row.status, row.blocksFullInventoryHull, row.acceptedFreshCompatibleQe
      ? 'reference_inventory|evidence_summary' : 'reference_inventory|missing_references|evidence_summary',
    filters.system, filters.status, filters.elementalsOnly, filters.spinOnly, 'Empty means unavailable, not zero',
    'One row per inventory-system membership; systems overlap; no complete compatible reference hull'])]);
}

export function claimsCsv(claims: readonly ClaimMatrixRow[], dataReleaseId: string,
  sourceIds: readonly SourceId[] = ['claim_matrix']): string {
  return csvRows([['data_release_id', 'claim', 'status', 'measured_scope', 'limitation', 'source_ids', 'scope'],
    ...claims.map(row => [dataReleaseId, row.claim, row.status, row.scope, row.limitation, sourceIds.join('|'),
      'Frozen study claims with their measured scope and limits; no new website experiments'])]);
}
