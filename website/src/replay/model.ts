import { policyColour } from '../presentation/policyColours.ts';
import type { BatchBudget, Policy, ReplayBatch, ReplayCurves, ReplayDataset, ReplayQuery, ReplaySeed,
  Round, ThemeDataset } from '../data/contracts.ts';
import type { RouteState } from '../state/route.ts';

/** These are recorded acquisition outcomes, not predictor uncertainty intervals. */
export type ReplayMetric = 'hits' | 'precision' | 'systems';
export interface ReplayChartPoint {
  readonly queries: BatchBudget;
  readonly mean: number | null;
  readonly sampleStd: number | null;
  readonly low: number | null;
  readonly high: number | null;
}
export interface ReplaySeries {
  readonly policy: Policy;
  readonly label: string;
  readonly colour: string;
  readonly points: readonly ReplayChartPoint[];
}
export interface ReplaySelection {
  readonly mode: 'aggregate' | 'seed';
  readonly seed: ReplaySeed;
  readonly policies: readonly Policy[];
}
export const REPLAY_BUDGETS: readonly BatchBudget[] = [0, 10, 20, 30, 40, 50];
export const METRIC_LABELS: Readonly<Record<ReplayMetric, string>> = {
  hits: 'Historical near-stable hits', precision: 'Historical near-stable precision',
  systems: 'Chemical-system coverage',
};
export const METRIC_UNITS: Readonly<Record<ReplayMetric, string>> = {
  hits: 'selected materials', precision: 'fraction', systems: 'distinct chemical systems',
};

function summarize(values: readonly number[]): { mean: number; sampleStd: number } {
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const sampleStd = Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1));
  return { mean, sampleStd };
}

/** One point per saved batch boundary. Missing or duplicate records are errors, never zero-filled. */
export function buildReplaySeries(curves: ReplayCurves, theme: ThemeDataset,
  selection: ReplaySelection, metric: ReplayMetric): ReplaySeries[] {
  if (selection.mode === 'aggregate' && curves.seeds.length !== 5) {
    throw new Error('Aggregate replay requires the five recorded splits.');
  }
  const seeds = selection.mode === 'aggregate' ? curves.seeds : [selection.seed];
  return selection.policies.map((policy) => ({
    policy, label: theme.policyLabels[policy], colour: policyColour(theme, policy),
    points: REPLAY_BUDGETS.map((queries): ReplayChartPoint => {
      if (queries === 0) {
        const mean = metric === 'precision' ? null : 0;
        const sampleStd = selection.mode === 'aggregate' && mean !== null ? 0 : null;
        return { queries, mean, sampleStd, low: sampleStd === null ? null : 0, high: sampleStd === null ? null : 0 };
      }
      const values = seeds.map((seed) => {
        const matches = curves.points.filter((point) => point.seed === seed && point.policy === policy && point.queries === queries);
        if (matches.length !== 1) throw new Error(`Expected one saved curve point for ${seed}/${policy}/${queries}.`);
        const point = matches[0];
        return metric === 'precision' ? point.nearStableHits / queries : metric === 'hits'
          ? point.nearStableHits : point.chemicalSystemCoverage;
      });
      if (selection.mode === 'seed') return { queries, mean: values[0], sampleStd: null, low: null, high: null };
      const { mean, sampleStd } = summarize(values);
      // Preserve raw descriptive mean +/- sample SD, even beyond the metric's physical range.
      return { queries, mean, sampleStd, low: mean - sampleStd, high: mean + sampleStd };
    }),
  }));
}

export function batchFor(history: ReplayDataset, policy: Policy, batch: Round): ReplayBatch | null {
  const matching = history.histories.filter((item) => item.policy === policy);
  if (matching.length !== 1) return null;
  const batches = matching[0].batches.filter((item) => item.round === batch);
  return batches.length === 1 ? batches[0] : null;
}

/** Nulls are deliberate label hiding; absent random acquisition scores remain null independently. */
export type DisplayReplayQuery = Omit<ReplayQuery, 'revealedLabelEVPerAtom' | 'nearStableHit' | 'referenceHullHit'> & {
  readonly revealedLabelEVPerAtom: number | null;
  readonly nearStableHit: boolean | null;
  readonly referenceHullHit: boolean | null;
};

/** Explicit projection prevents raw outcomes or cumulative counts leaking into pre-reveal rendering. */
export function displayQueries(batch: ReplayBatch, revealed: boolean): DisplayReplayQuery[] {
  return batch.queries.map((query) => ({
    queryNumber: query.queryNumber, materialId: query.materialId, formula: query.formula,
    reducedFormula: query.reducedFormula, chemicalSystem: query.chemicalSystem, atoms: query.atoms,
    role: query.role, score: query.score, predictedMeanEVPerAtom: query.predictedMeanEVPerAtom,
    calibratedRadiusEVPerAtom: query.calibratedRadiusEVPerAtom, diversityAtSelection: query.diversityAtSelection,
    revealedLabelEVPerAtom: revealed ? query.revealedLabelEVPerAtom : null,
    nearStableHit: revealed ? query.nearStableHit : null,
    referenceHullHit: revealed ? query.referenceHullHit : null,
  }));
}

export type CsvValue = string | number | boolean | null | undefined;
/** RFC 4180 escaping plus spreadsheet formula protection for string values only. */
export function csvCell(value: CsvValue): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('CSV values must be finite.');
  let text = String(value);
  // Leading whitespace/control characters can be ignored by spreadsheet formula parsers.
  if (typeof value === 'string' && /^[\s\u0000-\u001f]*[=+@-]/.test(value)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
export function csvRows(rows: readonly (readonly CsvValue[])[]): string {
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n') + '\r\n';
}

/** CSV mirrors the comparison table: visible policies, six recorded boundaries up to completed budget. */
export function comparisonCsv(curves: ReplayCurves, theme: ThemeDataset, state: RouteState,
  dataReleaseId = ''): string {
  const selection: ReplaySelection = state;
  const hits = buildReplaySeries(curves, theme, selection, 'hits');
  const precision = buildReplaySeries(curves, theme, selection, 'precision');
  const systems = buildReplaySeries(curves, theme, selection, 'systems');
  const rows: CsvValue[][] = [[
    'mode', 'seed', 'policy', 'policy_label', 'completed_queries', 'point_origin', 'historical_near_stable_hits_mean',
    'historical_near_stable_hits_sample_sd', 'precision_mean_fraction', 'precision_sample_sd_fraction',
    'chemical_system_coverage_mean', 'chemical_system_coverage_sample_sd', 'aggregate_split_count',
    'near_stable_threshold_eV_per_atom_inclusive', 'reference_hull_threshold_eV_per_atom_inclusive',
    'study_id', 'data_release_id', 'source_ids', 'scope', 'null_meaning',
  ]];
  for (const [index, series] of hits.entries()) for (const [pointIndex, point] of series.points.entries()) {
    if (point.queries > state.budget) continue;
    const pr = precision[index].points[pointIndex], sy = systems[index].points[pointIndex];
    rows.push([state.mode, state.mode === 'seed' ? state.seed : null, series.policy, series.label,
      point.queries, point.queries === 0 ? 'derived_zero_state' : 'recorded_batch_boundary',
      point.mean, point.sampleStd, pr.mean, pr.sampleStd, sy.mean, sy.sampleStd,
      state.mode === 'aggregate' ? curves.seeds.length : null,
      curves.thresholds.nearStableEVPerAtom, curves.thresholds.referenceHullEVPerAtom,
      curves.studyId, dataReleaseId, curves.sourceIds.join(';'),
      state.mode === 'aggregate' ? 'Five split outcomes; descriptive sample SD (n-1), not a confidence interval.'
        : 'One recorded split; no split-variability band.',
      'Precision is unavailable at zero queries; split sample SD is unavailable in single-split mode.',
    ]);
  }
  return csvRows(rows);
}

/** Only the inspected ten-row batch is exported. Label hiding is pedagogical, not access control. */
export function queryCsv(history: ReplayDataset, policy: Policy, round: Round, revealed: boolean,
  dataReleaseId = ''): string {
  const batch = batchFor(history, policy, round);
  if (!batch) throw new Error('The selected recorded batch is unavailable.');
  const rows: CsvValue[][] = [[
    'seed', 'policy', 'batch', 'query_number', 'material_id', 'formula', 'reduced_formula', 'chemical_system',
    'physical_atoms', 'selection_role', 'recorded_acquisition_score', 'predicted_mean_eV_per_atom',
    'calibrated_radius_eV_per_atom', 'diversity_at_selection', 'historical_target_eV_per_atom',
    'historical_near_stable_hit', 'reference_hull_hit', 'label_visibility', 'study_id', 'data_release_id',
    'source_ids', 'null_meaning', 'scope',
  ]];
  for (const query of displayQueries(batch, revealed)) rows.push([
    history.seed, policy, round, query.queryNumber, query.materialId, query.formula, query.reducedFormula,
    query.chemicalSystem, query.atoms, query.role, query.score, query.predictedMeanEVPerAtom,
    query.calibratedRadiusEVPerAtom, query.diversityAtSelection, query.revealedLabelEVPerAtom,
    query.nearStableHit, query.referenceHullHit, revealed ? 'revealed' : 'hidden', history.studyId,
    dataReleaseId, history.sourceIds.join(';'),
    'Empty acquisition score means unavailable (including random); empty targets/hits mean labels hidden.',
    'Selected records only; not the candidate pool. Teaching reveal only; outcomes exist in public static data.',
  ]);
  return csvRows(rows);
}
