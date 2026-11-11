import type { EvaluationPolicy, ReplaySeed, RoleDiagnostic, UncertaintyDataset } from '../data/contracts.ts';
import { csvRows, type CsvValue } from '../replay/model.ts';

export const ENDPOINT_LABELS: Readonly<Record<EvaluationPolicy, string>> = {
  initial_shared: 'Initial', quality: 'Quality', full: 'Full',
  quality_diversity: 'Quality + diversity', random: 'Random', uncertainty: 'Uncertainty only',
};
export const CORE_ENDPOINTS = ['initial_shared', 'quality', 'full'] as const;
export const ADVANCED_ENDPOINTS = ['quality_diversity', 'random', 'uncertainty'] as const;

/** Risk and deciles exist only at the shared initial model or final 50-query model.
 * Do not substitute intermediate evaluation metrics or average overlapping splits. */
export function selectUncertaintyContext(dataset: UncertaintyDataset, seed: ReplaySeed,
  endpoint: EvaluationPolicy, retainedFraction: number) {
  const queries = endpoint === 'initial_shared' ? 0 : 50;
  const matches = (row: { seed: ReplaySeed; policy: EvaluationPolicy; queries: number }) =>
    row.seed === seed && row.policy === endpoint && row.queries === queries;
  const metrics = dataset.evaluationMetrics.find(matches) ?? null;
  const risk = dataset.riskCoverage.filter(matches).sort((a, b) => a.requestedRetainedFraction - b.requestedRetainedFraction);
  const deciles = dataset.deciles.filter(matches).sort((a, b) => a.decile - b.decile);
  const retained = risk.find((row) => row.requestedRetainedFraction === retainedFraction) ?? null;
  return { seed, endpoint, queries, metrics, risk, deciles, retained };
}
export type UncertaintyContext = ReturnType<typeof selectUncertaintyContext>;

export function roleTotals(roles: readonly RoleDiagnostic[], role: RoleDiagnostic['role']) {
  const rows = roles.filter((row) => row.role === role);
  const queries = rows.reduce((sum, row) => sum + row.queries, 0);
  const hits = rows.reduce((sum, row) => sum + row.nearStableHits, 0);
  return { role, queries, hits, precision: queries === 0 ? null : hits / queries,
    meanCalibratedRadiusEVPerAtom: queries === 0 ? null : rows.reduce((sum, row) =>
      sum + row.meanCalibratedRadiusEVPerAtom * row.queries, 0) / queries };
}

const commonHeaders = ['study_id', 'data_release_id', 'source_ids', 'scope', 'null_meaning'];
function common(dataset: UncertaintyDataset, releaseId: string, scope: string): CsvValue[] {
  return [dataset.studyId, releaseId, dataset.sourceIds.join(';'), scope, 'Empty means unavailable; zero is a measured value.'];
}
export function uncertaintyMetricsCsv(dataset: UncertaintyDataset, context: UncertaintyContext, releaseId: string): string {
  const headers = ['seed', 'endpoint', 'completed_queries', 'evaluation_rows', 'nominal_interval_coverage_fraction',
    'empirical_interval_coverage_fraction', 'mae_eV_per_atom', 'rmse_eV_per_atom', 'mean_interval_width_eV_per_atom',
    'disagreement_absolute_error_spearman', 'calibration_scale_q', ...commonHeaders];
  const row = context.metrics;
  return csvRows([headers, ...row ? [[row.seed, row.policy, row.queries, row.rows,
    dataset.summary.nominalIntervalCoverage, row.interval90EmpiricalCoverage, row.maeEVPerAtom, row.rmseEVPerAtom,
    row.meanIntervalWidthEVPerAtom, row.disagreementAbsoluteErrorSpearman, row.calibrationScale,
    ...common(dataset, releaseId, 'One saved split/model endpoint; initial_shared is one model per seed. No per-query refit or arbitrary-OOD coverage guarantee.')]] : []]);
}
export function uncertaintyRiskCsv(dataset: UncertaintyDataset, context: UncertaintyContext, releaseId: string): string {
  return csvRows([['seed', 'endpoint', 'completed_queries', 'requested_retained_fraction', 'retained_rows',
    'actual_retained_fraction', 'mae_eV_per_atom', 'all_rows_mae_eV_per_atom', 'mae_relative_to_all_rows',
    'empirical_interval_coverage_fraction', 'selected_retention_step', ...commonHeaders], ...context.risk.map((row) => [
    row.seed, row.policy, row.queries, row.requestedRetainedFraction, row.retainedRows, row.actualRetainedFraction,
    row.maeEVPerAtom, row.allRowsMaeEVPerAtom, row.maeRelativeToAllRows, row.interval90EmpiricalCoverage,
    row === context.retained, ...common(dataset, releaseId, dataset.summary.riskCoverageMethod),
  ])]);
}
export function uncertaintyDecilesCsv(dataset: UncertaintyDataset, context: UncertaintyContext, releaseId: string): string {
  return csvRows([['seed', 'endpoint', 'completed_queries', 'uncertainty_decile', 'rows',
    'mean_disagreement_eV_per_atom', 'min_disagreement_eV_per_atom', 'max_disagreement_eV_per_atom',
    'mae_eV_per_atom', 'empirical_interval_coverage_fraction', 'mean_interval_width_eV_per_atom', ...commonHeaders],
  ...context.deciles.map((row) => [row.seed, row.policy, row.queries, row.decile, row.rows,
    row.meanDisagreementEVPerAtom, row.minDisagreementEVPerAtom, row.maxDisagreementEVPerAtom,
    row.maeEVPerAtom, row.interval90EmpiricalCoverage, row.meanIntervalWidthEVPerAtom,
    ...common(dataset, releaseId, dataset.summary.decileMethod),
  ])]);
}
export function uncertaintyRolesCsv(dataset: UncertaintyDataset, releaseId: string): string {
  return csvRows([['seed', 'policy', 'selection_role', 'queries', 'historical_near_stable_hits', 'precision_fraction',
    'reference_hull_hits', 'mean_predicted_mean_eV_per_atom', 'mean_calibrated_radius_eV_per_atom',
    'mean_diversity_distance', ...commonHeaders], ...dataset.roles.map((row) => [row.seed, 'full', row.role,
    row.queries, row.nearStableHits, row.precision, row.referenceHullHits, row.meanPredictedMeanEVPerAtom,
    row.meanCalibratedRadiusEVPerAtom, row.meanDiversityDistance,
    ...common(dataset, releaseId, dataset.summary.roleScope),
  ])]);
}
