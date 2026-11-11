/** Pure saved-geometry operations. Lattice vectors are ROWS; no inference or relaxation. */
import type { Bool3, Matrix3, SavedGeometry, SavedStage, Vec3 } from '../data/contracts';

export const fractionalToCartesian = (f: Vec3, lattice: Matrix3): Vec3 => [
  f[0] * lattice[0][0] + f[1] * lattice[1][0] + f[2] * lattice[2][0],
  f[0] * lattice[0][1] + f[1] * lattice[1][1] + f[2] * lattice[2][1],
  f[0] * lattice[0][2] + f[1] * lattice[1][2] + f[2] * lattice[2][2],
];
export const determinant = (m: Matrix3): number => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
  - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
  + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
export const cellVolume = (m: Matrix3): number => Math.abs(determinant(m));

export function inverseLattice(m: Matrix3): Matrix3 {
  const d = determinant(m);
  if (!Number.isFinite(d) || d === 0 || !m.flat().every(Number.isFinite)) throw new Error('A finite nonsingular saved lattice is required.');
  return [
    [(m[1][1] * m[2][2] - m[1][2] * m[2][1]) / d, (m[0][2] * m[2][1] - m[0][1] * m[2][2]) / d, (m[0][1] * m[1][2] - m[0][2] * m[1][1]) / d],
    [(m[1][2] * m[2][0] - m[1][0] * m[2][2]) / d, (m[0][0] * m[2][2] - m[0][2] * m[2][0]) / d, (m[0][2] * m[1][0] - m[0][0] * m[1][2]) / d],
    [(m[1][0] * m[2][1] - m[1][1] * m[2][0]) / d, (m[0][1] * m[2][0] - m[0][0] * m[2][1]) / d, (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / d],
  ];
}
export const cartesianToFractional = (cartesian: Vec3, lattice: Matrix3): Vec3 => fractionalToCartesian(cartesian, inverseLattice(lattice));
/** Display wrapping only: nonperiodic axes and original records remain untouched. */
export const wrapFractional = (fractional: Vec3, pbc: Bool3): Vec3 => fractional.map((n, axis) => pbc[axis] ? n - Math.floor(n) : n) as unknown as Vec3;
export const cellCorners = (lattice: Matrix3): readonly Vec3[] => Array.from({ length: 8 }, (_, i) => fractionalToCartesian([i & 1, (i >> 1) & 1, (i >> 2) & 1], lattice));
export function cellEdges(lattice: Matrix3): readonly (readonly [Vec3, Vec3])[] {
  const corners = cellCorners(lattice);
  return corners.flatMap((point, i) => [1, 2, 4].filter((bit) => !(i & bit)).map((bit) => [point, corners[i | bit]] as const));
}
export interface GeometryBounds { readonly min: Vec3; readonly max: Vec3; readonly center: Vec3; readonly radius: number }
export function geometryBounds(lattice: Matrix3, additionalPoints: readonly Vec3[] = []): GeometryBounds {
  const points = [...cellCorners(lattice), ...additionalPoints];
  const min = [0, 1, 2].map((axis) => Math.min(...points.map((p) => p[axis]))) as unknown as Vec3;
  const max = [0, 1, 2].map((axis) => Math.max(...points.map((p) => p[axis]))) as unknown as Vec3;
  const center = min.map((n, axis) => (n + max[axis]) / 2) as unknown as Vec3;
  return { min, max, center, radius: Math.max(...points.map((p) => Math.hypot(p[0] - center[0], p[1] - center[1], p[2] - center[2]))) };
}

/** Exact finite closest-image search, including skew lattices where component rounding fails.
 * A trial image gives R. For every improving image x, |(x L^-1)_i| <= R ||column_i(L^-1)||.
 * Those reciprocal bounds cover every possible improving integer translation. */
export function distancePeriodic(a: Vec3, b: Vec3, lattice: Matrix3, pbc: Bool3): number {
  const delta = a.map((n, axis) => n - b[axis]) as unknown as Vec3;
  const inverse = inverseLattice(lattice);
  const trial = delta.map((n, axis) => pbc[axis] ? n - Math.round(n) : n) as unknown as Vec3;
  let best = Math.hypot(...fractionalToCartesian(trial, lattice));
  const limits = [0, 1, 2].map((axis) => {
    if (!pbc[axis]) return [0, 0] as const;
    const bound = best * Math.hypot(inverse[0][axis], inverse[1][axis], inverse[2][axis]) + 1e-12;
    return [Math.ceil(-delta[axis] - bound), Math.floor(-delta[axis] + bound)] as const;
  });
  for (let i = limits[0][0]; i <= limits[0][1]; i++) for (let j = limits[1][0]; j <= limits[1][1]; j++) for (let k = limits[2][0]; k <= limits[2][1]; k++) {
    best = Math.min(best, Math.hypot(...fractionalToCartesian([delta[0] + i, delta[1] + j, delta[2] + k], lattice)));
  }
  return best;
}
export function minimumPeriodicDistance(geometry: SavedGeometry): number | null {
  let distance = Infinity;
  for (let i = 0; i < geometry.fractionalCoordinates.length; i++) for (let j = i + 1; j < geometry.fractionalCoordinates.length; j++) {
    distance = Math.min(distance, distancePeriodic(geometry.fractionalCoordinates[i], geometry.fractionalCoordinates[j], geometry.latticeRowsAngstrom, geometry.pbc));
  }
  return Number.isFinite(distance) ? distance : null;
}

const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export function latticeParameters(lattice: Matrix3): { a: number; b: number; c: number; alpha: number; beta: number; gamma: number } {
  const [a, b, c] = lattice.map((v) => Math.hypot(...v));
  if (Math.min(a, b, c) <= 0) throw new Error('A finite nonsingular saved lattice is required.');
  const angle = (u: Vec3, v: Vec3, lengths: number) => Math.acos(Math.max(-1, Math.min(1, dot(u, v) / lengths))) * 180 / Math.PI;
  return { a, b, c, alpha: angle(lattice[1], lattice[2], b * c), beta: angle(lattice[0], lattice[2], a * c), gamma: angle(lattice[0], lattice[1], a * b) };
}
const cifValue = (text: string): string => {
  if (/[\r\n'"\\]/.test(text)) throw new Error('Unexpected character in saved CIF identity.');
  return `'${text}'`;
};
/** Explicit-site CIF, P1 encoding only. Recorded symmetry is metadata, never expanded/inferred.
 * Standard CIF preserves the lattice metric, not arbitrary Cartesian orientation. Raw source
 * lattice rows are additionally preserved as custom metadata. Coordinates are NOT wrapped. */
export function structureCif(stage: SavedStage, dataReleaseId = 'data-v1-2a138b7808f0d12c5151'): string {
  const g = stage.geometry, parameters = latticeParameters(g.latticeRowsAngstrom);
  if (!g.pbc.every(Boolean)) throw new Error('Standard crystal CIF export requires three periodic axes; this saved geometry is not fully periodic.');
  const lines = ['# Flamel saved structure; no new optimization or symmetry inference.',
    '# Explicit physical sites in P1; source symmetry remains separate recorded metadata.',
    `data_${stage.stageId.replace(/[^a-zA-Z0-9_]/g, '_')}`,
    `_flamel_study_id ${cifValue(stage.studyId)}`, `_flamel_data_release_id ${cifValue(dataReleaseId)}`,
    `_flamel_candidate_id ${cifValue(stage.candidateId)}`, `_flamel_stage_id ${cifValue(stage.stageId)}`,
    `_flamel_stage_kind ${cifValue(stage.stage)}`, `_flamel_method ${cifValue(stage.method)}`,
    `_flamel_excluded ${stage.eligibility.excluded ? 'yes' : 'no'}`,
    `_flamel_exact_cell_eligible ${stage.eligibility.exactCellEligible === null ? '?' : stage.eligibility.exactCellEligible ? 'yes' : 'no'}`,
    `_flamel_queue_selected ${stage.eligibility.queueSelected ? 'yes' : 'no'}`,
    `_flamel_source_id ${cifValue(stage.sourceId)}`, `_flamel_source_sha256 ${cifValue(stage.sourceSha256)}`,
    `_flamel_physical_sites ${g.actualAtoms}`, `_flamel_pbc_a ${g.pbc[0] ? 'yes' : 'no'}`, `_flamel_pbc_b ${g.pbc[1] ? 'yes' : 'no'}`, `_flamel_pbc_c ${g.pbc[2] ? 'yes' : 'no'}`,
    `_flamel_recorded_spacegroup_number ${stage.symmetry.spacegroupNumber ?? '?'}`,
    `_flamel_recorded_symprec_angstrom ${stage.symmetry.symprecAngstrom ?? '?'}`,
    `_flamel_recorded_angle_tolerance_degrees ${stage.symmetry.angleToleranceDegrees ?? '?'}`,
    `_flamel_global_novelty_established no`, `_flamel_new_stable_material_established no`,
    `_chemical_formula_sum ${cifValue(g.formula)}`,
    ...Object.entries(parameters).map(([key, value]) => `_cell_${key.length === 1 ? 'length' : 'angle'}_${key} ${value}`),
    `_cell_volume ${cellVolume(g.latticeRowsAngstrom)}`, `_space_group_name_H-M_alt 'P 1'`, `_space_group_IT_number 1`,
    'loop_', '_space_group_symop_operation_xyz', "'x,y,z'",
    'loop_', '_flamel_lattice_row', '_flamel_lattice_x_angstrom', '_flamel_lattice_y_angstrom', '_flamel_lattice_z_angstrom',
    ...g.latticeRowsAngstrom.map((row, i) => `${i} ${row.join(' ')}`),
    'loop_', '_atom_site_label', '_atom_site_type_symbol', '_atom_site_fract_x', '_atom_site_fract_y', '_atom_site_fract_z', '_atom_site_occupancy'];
  for (const site of g.sites) for (const species of site.species) {
    const fractional = g.fractionalCoordinates[site.siteIndex];
    lines.push(`${species.element}_${site.siteIndex} ${species.element} ${fractional.join(' ')} ${species.occupancy}`);
  }
  return `${lines.join('\n')}\n`;
}

const stable = (value: unknown): string => {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${stable(item)}`).join(',')}}`;
  return JSON.stringify(value);
};
const complete = (value: unknown): boolean => value !== null && value !== undefined &&
  (typeof value === 'number' ? Number.isFinite(value) : typeof value === 'string' ? value.trim().length > 0 && !/^(unknown|unavailable|not[ _-]?recorded|n\/a|\?)$/i.test(value.trim()) :
    Array.isArray(value) ? value.length > 0 && value.every(complete) : typeof value === 'object' ? Object.keys(value).length > 0 && Object.values(value).every(complete) : typeof value === 'boolean');
const composition = (g: SavedGeometry): string => {
  const counts: Record<string, number> = {};
  for (const site of g.sites) for (const specie of site.species) counts[specie.element] = (counts[specie.element] ?? 0) + specie.occupancy;
  const entries = Object.entries(counts).sort(([a], [b]) => a.localeCompare(b));
  return entries.map(([element, count]) => `${element}:${(count / entries[0][1]).toPrecision(14)}`).join('|');
};
export interface EnergyComparison { readonly compatible: boolean; readonly reason: string; readonly deltaEVPerAtom: number | null }
/** Strict gate. Delta is RIGHT minus LEFT, with no formation/hull interpretation. */
export function comparableEnergy(left: SavedStage, right: SavedStage): EnergyComparison {
  const unavailable = (reason: string): EnergyComparison => ({ compatible: false, reason, deltaEVPerAtom: null });
  if (!left.energy || !right.energy) return unavailable('A saved energy is unavailable for one or both stages.');
  if (composition(left.geometry) !== composition(right.geometry)) return unavailable('Reduced compositions differ.');
  const a = left.energy, b = right.energy;
  if (a.engine !== b.engine || a.unit !== b.unit) return unavailable('Energy engines or units differ.');
  if (!Number.isFinite(a.value) || !Number.isFinite(b.value)) return unavailable('A saved energy is nonfinite.');
  const required = a.engine === 'CHGNet'
    ? ['modelVersion', 'checkpointSha256', 'packageVersion', 'optimizer', 'maxSteps', 'forceThresholdEVPerAngstrom', 'cellRelaxed', 'filter', 'imposedSymmetry']
    : ['functional', 'wavefunctionCutoffRy', 'densityCutoffRy', 'kMesh', 'kSpacingTargetInverseAngstrom', 'nspin', 'occupations', 'pseudoSha256ByElement', 'executableSha256'];
  for (const energy of [a, b]) {
    if (!complete(energy.settingsScope) || !required.every((key) => complete((energy.settings as unknown as Record<string, unknown>)[key]))) return unavailable('Actual saved calculation settings are incomplete.');
    const settings = energy.settings;
    const validHash = (hash: string) => /^[a-f0-9]{64}$/i.test(hash);
    if (energy.engine === 'CHGNet') {
      const s = settings as import('../data/contracts').ChgnetSettings;
      if (!validHash(s.checkpointSha256) || !Number.isInteger(s.maxSteps) || s.maxSteps < 1 || s.forceThresholdEVPerAngstrom <= 0 || typeof s.cellRelaxed !== 'boolean' || typeof s.imposedSymmetry !== 'boolean') return unavailable('Actual saved calculation settings are invalid or unknown.');
    } else {
      const s = settings as import('../data/contracts').QeSettings;
      if (!validHash(s.executableSha256) || !Object.values(s.pseudoSha256ByElement).every(validHash) || s.kMesh.length !== 3 || !s.kMesh.every((n) => Number.isInteger(n) && n > 0) || s.wavefunctionCutoffRy <= 0 || s.densityCutoffRy <= 0 || s.kSpacingTargetInverseAngstrom <= 0 || !Number.isInteger(s.nspin) || s.nspin < 1) return unavailable('Actual saved calculation settings are invalid or unknown.');
    }
  }
  if (a.settingsScope !== b.settingsScope || stable(a.settings) !== stable(b.settings)) return unavailable('Actual calculation settings or their recorded scope differ.');
  return { compatible: true, reason: 'Same reduced composition, engine, units and complete actual saved settings. Delta is right minus left; it is not a hull or formation energy.', deltaEVPerAtom: b.value - a.value };
}
