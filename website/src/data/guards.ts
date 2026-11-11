import type { DatasetFor, JsonLogicalName } from './contracts.ts';
import { DATA_RELEASE } from './release.ts';

/** Validate unknown bytes at the UI boundary, including nested values used by
 * views. Hash verification binds the release; these guards keep a malformed
 * record from becoming an uncaught render error or an invented zero. */
export class ResearchShapeError extends Error {
  constructor(path: string, expected: string) {
    super(`Research data has an unsupported value at ${path}; expected ${expected}.`);
    this.name = 'ResearchShapeError';
  }
}
type Spec = (value: unknown, path: string) => void;
function fail(path: string, expected: string): never { throw new ResearchShapeError(path, expected); }
function record(value: unknown, path: string): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) fail(path, 'an object');
  return value as Record<string, unknown>;
}
const text: Spec = (v, p) => { if (typeof v !== 'string' || !v.trim()) fail(p, 'a non-empty string'); };
const finite: Spec = (v, p) => { if (typeof v !== 'number' || !Number.isFinite(v)) fail(p, 'a finite number'); };
const count: Spec = (v, p) => { finite(v, p); if (!Number.isSafeInteger(v) || (v as number) < 0) fail(p, 'a non-negative integer'); };
const positiveCount: Spec = (v, p) => { count(v, p); if ((v as number) < 1) fail(p, 'a positive integer'); };
const positive: Spec = (v, p) => { finite(v, p); if ((v as number) <= 0) fail(p, 'a positive number'); };
const spacegroup: Spec = (v, p) => { positiveCount(v, p); if ((v as number) > 230) fail(p, 'a space group from 1 to 230'); };
const nonnegative: Spec = (v, p) => { finite(v, p); if ((v as number) < 0) fail(p, 'a non-negative number'); };
const fraction: Spec = (v, p) => { finite(v, p); if ((v as number) < 0 || (v as number) > 1) fail(p, 'a fraction from 0 to 1'); };
const bool: Spec = (v, p) => { if (typeof v !== 'boolean') fail(p, 'a boolean'); };
function literal(...allowed: readonly (string | number | boolean | null)[]): Spec {
  return (v, p) => { if (!allowed.some((entry) => entry === v)) fail(p, allowed.map(String).join(' or ')); };
}
function nullable(spec: Spec): Spec { return (v, p) => { if (v !== null) spec(v, p); }; }
function optional(spec: Spec): Spec { return (v, p) => { if (v !== undefined) spec(v, p); }; }
function array(spec: Spec, exactLength?: number): Spec {
  return (v, p) => {
    if (!Array.isArray(v) || (exactLength !== undefined && v.length !== exactLength)) {
      fail(p, exactLength === undefined ? 'an array' : `an array with ${exactLength} entries`);
    }
    v.forEach((entry, i) => spec(entry, `${p}[${i}]`));
  };
}
function object(shape: Readonly<Record<string, Spec>>): Spec {
  return (v, p) => {
    const row = record(v, p);
    for (const [key, spec] of Object.entries(shape)) spec(row[key], `${p}.${key}`);
  };
}
function dictionary(spec: Spec): Spec {
  return (v, p) => { for (const [key, entry] of Object.entries(record(v, p))) spec(entry, `${p}.${key}`); };
}
function fields(names: string, spec: Spec): Record<string, Spec> {
  return Object.fromEntries(names.split(' ').map((name) => [name, spec]));
}
const sha: Spec = (v, p) => { if (typeof v !== 'string' || !/^[a-f0-9]{64}$/.test(v)) fail(p, 'a SHA-256 identity'); };
const utc: Spec = (v, p) => { text(v, p); if (!Number.isFinite(Date.parse(v as string))) fail(p, 'an ISO timestamp'); };
const url: Spec = (v, p) => {
  text(v, p);
  try { if (!['https:', 'http:'].includes(new URL(v as string).protocol)) fail(p, 'an HTTP(S) URL'); }
  catch { fail(p, 'an HTTP(S) URL'); }
};
const policies = ['full', 'quality', 'quality_diversity', 'random', 'uncertainty'] as const;
const policy = literal(...policies);
const evaluationPolicy = literal(...policies, 'initial_shared');
const seed = literal(20261022, 20261023, 20261024, 20261025, 20261026);
const budget = literal(0, 10, 20, 30, 40, 50);
const control = literal('mgo_rocksalt', 'tio2_rutile');
const arm = literal('nontrivial', 'p1');
const cohortScope = literal('primary_first8', 'supplementary_topup_only');
const pairScope = literal('primary_first8_per_arm', 'supplementary_primary_plus_topup_pool');
const stageKind = literal('generated', 'prototype_initial', 'catalog_initial', 'generated_excluded', 'model_relaxed', 'accepted_dft');
const stageMethod = literal('crystalformer', 'prototype_substitution', 'catalog_reference', 'chgnet', 'quantum_espresso');
const sourceIds = array(text);
const evidence = array(object({ sourceId: text, field: nullable(text) }));
const vec3 = array(finite, 3);
const stat = object({ ...fields('mean sampleStd min max', finite), values: array(finite) });
const policyStat = object({ ...fields('nearStableHits referenceHullHits chemicalSystemCoverage precisionAt50', stat) });
const policyStatistics = object(Object.fromEntries(policies.map((name) => [name, policyStat])));
const cumulative = { queries: budget, ...fields('nearStableHits referenceHullHits chemicalSystemCoverage', count) };
const point = { ...cumulative, seed, policy };
const claimRow = object(fields('claim status scope limitation', text));
const counts = object(fields('replaySeeds policies historicalQueryEvents distinctSelectedHistoricalMaterials evaluationSnapshots actualCrystalFormerDraws newFormulaDraws newFormulaExactValid excludedNewFormulaLargerCellDiagnostics modelSelectedStructures prototypeBaselines sameCompositionModelReferences qeAttempts acceptedRelaxedQeGeometries acceptedOriginalSourceReferenceIds consolidatedResearchChecksPassed', count));
const summary = object({
  ...fields('projectName researchTitle hypothesis', text), studyStatus: literal('frozen_prototype'),
  demoMode: literal('recorded_evidence_replay'), newStableMaterialEstablished: literal(false), pipeline: array(text),
  counts, policyStatistics, fullMinusQualityHits: stat, findings: array(text), scientificLimits: array(text),
  claims: array(claimRow), budgets: array(object({ lane: literal('generation', 'chgnet_attempts', 'chgnet_wall', 'QE_wall'),
    ...fields('cap charged remaining', nonnegative), unit: literal('conservative_structure_slots', 'conservative_launch_slots', 'seconds'), interpretation: text })),
  numericalStudyFrozen: literal(true), newExperimentsInWebsiteExport: literal(0), sourceIds,
});
const curves = object({ seeds: array(seed, 5), policies: array(policy, 5), thresholds: object({
  nearStableEVPerAtom: literal(0.05), referenceHullEVPerAtom: literal(0), comparison: literal('less_than_or_equal'), label: literal('historical signed hull distance'),
}), points: array(object(point), 125), endpoints: array(object({ ...point, precisionAt50: fraction }), 25),
  zeroQueryOrigin: object({ ...fields('queries nearStableHits referenceHullHits chemicalSystemCoverage', literal(0)),
    precision: literal(null), origin: literal('derived_zero_state'), label: text }),
  policyStatistics, fullMinusQualityHits: stat, sourceIds });
const replay = object({ seed, scope: text, sourceIds, histories: array(object({ policy,
  batches: array(object({ round: literal(1, 2, 3, 4, 5), decision: object({ utc, sha256: sha }), reveal: object({ utc, sha256: sha }),
    queries: array(object({ queryNumber: positiveCount, ...fields('materialId formula reducedFormula chemicalSystem', text), atoms: positiveCount,
      role: literal('random', 'quality', 'quality_diversity', 'uncertainty', 'conservative', 'optimistic'), score: nullable(finite),
      ...fields('predictedMeanEVPerAtom revealedLabelEVPerAtom', finite), ...fields('calibratedRadiusEVPerAtom diversityAtSelection', nonnegative),
      nearStableHit: bool, referenceHullHit: bool }), 10), cumulativeAfterReveal: object(cumulative) }), 5) }), 5) });
const claims = object({ claims: array(object({ ...fields('id title text', text), sourceIds, claimStatus: literal('supported_with_stated_scope') })),
  newStableMaterialEstablished: literal(false), notes: array(text) });
const glossary = object({ terms: array(object({ ...fields('id label definition', text), unit: nullable(text) })) });
const theme = object({ palette: object(fields('paper graphite copper selection', text)),
  policyColours: object(Object.fromEntries([...policies, 'initial_shared'].map((p) => [p, text]))),
  policyLabels: object(Object.fromEntries([...policies, 'initial_shared'].map((p) => [p, text]))),
  elementColours: dictionary(text), statusLabels: object(fields('generated prototype_initial catalog_initial generated_excluded model_relaxed accepted_dft excluded incomplete not_evaluated', text)),
  typography: object(fields('heading body numeric', text)), motion: object({ autoRotationDefault: literal(false), respectReducedMotion: literal(true) }) });
const methods = object({ ...fields('title headline description', text), executionMode: literal('recorded_research_only'), liveScientificCompute: literal(false),
  target: object({ name: text, unit: literal('eV/atom'), nearStableInclusive: literal(0.05), referenceHullInclusive: literal(0), freshQETargetCompatible: literal(false) }),
  workflow: array(object({ id: literal('propose', 'generate', 'screen', 'select', 'relax', 'validate', 'compare'), label: text, description: text }), 7),
  sourceIds, attributions: array(object({ ...fields('name role licence credit modifications', text), url, licenceUrl: nullable(url) })),
  externalPublicationLinks: array(object({ kind: literal('repository', 'writeup', 'video'), label: text, url: literal(null), status: literal('not_published') })),
  sourceRegistryReference: text, scope: array(text) });
const provenance = object({ sources: array(object({ ...fields('sourceId label description', text), sha256: sha, bytes: positiveCount })),
  studyFrozenAt: utc, sourceInventorySha256: sha, sourceIdentityMeaning: text,
  units: object({ energy: literal('eV/atom'), lattice: literal('angstrom'), force: literal('eV/angstrom'), stress: literal('kbar'),
    cutoff: literal('Ry'), time: literal('seconds'), fraction: literal('0 to 1') }), newExperiments: literal(0), scope: text,
  attributionDataset: literal('methods.json'), claimDataset: literal('claims.json') });
const stageIndex = object({ ...fields('candidateId stageId sourceId fallbackFigureLogicalName', text), stage: stageKind, parentStageId: nullable(text),
  logicalFile: text, sourceSha256: sha, actualAtoms: positiveCount });
const structures = object({ candidates: array(object({ ...fields('candidateId formula defaultStageId', text),
  role: literal('symmetry', 'prototype', 'same_composition_reference', 'excluded_diagnostic', 'source_reference'),
  method: literal('crystalformer', 'prototype_substitution', 'catalog_reference'), actualAtoms: positiveCount, stageIds: array(text), eligible: bool,
  newStableMaterialEstablished: literal(false), evidence, control: optional(nullable(control)), arm: optional(nullable(arm)),
  comparisonScope: optional(nullable(pairScope)), ...fields('parentMaterialId referenceMaterialId referencePhase', optional(nullable(text))), cachedModelReuse: optional(bool) })),
  stages: array(stageIndex), coreExamples: array(object({ id: text, candidateId: text, stageIds: optional(array(text)) })),
  evidenceOnly: array(object({ ...fields('evidenceId candidateId sourceId explanation', text), kind: literal('incomplete_dft_perturbation'), jobIds: array(text),
    acceptedTerminalStageId: literal(null), energy: literal(null), status: literal('time_limit_before_terminal_convergence'), newStableMaterialEstablished: literal(false) })),
  counts: object(fields('entities stages modelFinals acceptedQERelaxedGeometries excludedExamples', count)),
  geometryConvention: object({ latticeVectors: literal('rows'), latticeUnit: literal('angstrom'), coordinates: literal('fractional'),
    cartesianFormula: literal('fractional @ lattice'), siteIndices: text, displayWrappingApplied: literal(false), periodicImagesAdded: literal(false), physicalAtomsExcludeDisplayImages: literal(true) }),
  validation: object({ nonOrthogonalStageIds: array(text), ...fields('newSymmetryInference newMatching newModelInference newRelaxations', literal(false)) }), scope: text });
const generationDraw = object({ ...fields('candidateId formula sourceId', text), scope: cohortScope, kind: literal('control', 'new_composition'), control: nullable(control), arm: nullable(arm),
  ...fields('requestedSpacegroup measuredSpacegroup', nullable(spacegroup)), ...fields('atoms requestedAtoms', positiveCount), actualCounts: dictionary(positive),
  ...fields('exactCountsMatch geometryValid valid correctRatioGeometryWithinCapDiagnosticOnly differentCellCountDiagnosticExcluded largerCellDiagnosticExcluded', bool),
  minimumPeriodicDistanceAngstrom: nullable(positive), duplicateOf: nullable(text), geometrySourceSha256: sha });
const generation = object({ cohorts: array(object({ scope: cohortScope, kind: literal('control', 'new_composition'), control: nullable(control), arm: nullable(arm), formula: text,
  ...fields('draws exactValid exactValidUnique validRequestedSpacegroup excludedLargerCellDiagnostics', count) }), 12), draws: array(generationDraw, 88), excluded: array(generationDraw, 12), excludedScope: text,
  prototypes: array(object({ ...fields('candidateId parentMaterialId targetFormula', text), atoms: positiveCount,
    ...fields('initialGeometryValid chgnetConverged freshDftSubmitted stableMaterialEstablished', bool), finalSpacegroup: spacegroup, chgnetEnergyEVPerAtom: finite }), 4),
  relaxedStructures: array(object({ ...fields('candidateId finalFormula sourceId', text), role: literal('symmetry', 'prototype', 'same_composition_reference'), control: nullable(control), arm: nullable(arm),
    atoms: positiveCount, chgnetEnergyEVPerAtom: nullable(finite), optimizerSteps: nullable(count), converged: bool, filterFmaxEVPerAngstrom: nullable(nonnegative), finalSpacegroup: nullable(spacegroup),
    spacegroupSymprecAngstrom: literal(0.01), matchesPinnedMpSameCompositionGeometryIds: array(text), sameCompositionMpGeometriesTested: count,
    ...fields('globalStructureNoveltyEstablished newStableMaterialEstablished', bool), geometrySourceId: nullable(text), geometrySourceSha256: sha }), 11),
  ...fields('modelEnergyScope modelNoveltyScope', text), symmetryPairs: array(object({ control, scope: pairScope, quotaPerArm: positiveCount,
    ...fields('nontrivialCandidateId p1CandidateId', text), p1MinusNontrivialChgnetEVPerAtom: finite,
    ...fields('relaxedPairStructureMatch energyDistributionEstablished dftStabilityComparison', bool) }), 2),
  compositionNovelty: array(object({ formula: text, counts: dictionary(positiveCount), ...fields('mpMatchingCompositionRecords wbmMatchingCompositionRecords', count),
    ...fields('absentFromBothPinnedSnapshots globalCompositionNoveltyEstablished generatorPretrainingOodEstablished dftConfirmedStability', bool) }), 6),
  catalogScope: object({ ...fields('mpSnapshot wbmSnapshot scope', text), populations: object({ mp: object(fields('records uniqueCompositions', positiveCount)), wbm: object(fields('records uniqueCompositions', positiveCount)) }) }),
  summary: object({ ...fields('actualCrystalFormerDraws newFormulaDraws newFormulaExactValid modelSelectedStructures prototypeBaselines', count), anataseMinusRutileChgnetEVPerAtom: finite,
    primaryYieldDenominatorsUnchanged: literal(true), scope: text, limits: array(text) }), sourceIds });
const evaluationSnapshot = { seed, policy: evaluationPolicy, queries: budget };
const evaluationAggregate = object(fields('maeEVPerAtom rmseEVPerAtom disagreementAbsoluteErrorSpearman interval90EmpiricalCoverage meanIntervalWidthEVPerAtom calibrationScale', stat));
const uncertainty = object({ evaluationMetrics: array(object({ ...evaluationSnapshot, rows: positiveCount,
  ...fields('maeEVPerAtom rmseEVPerAtom meanIntervalWidthEVPerAtom calibrationScale', nonnegative), disagreementAbsoluteErrorSpearman: finite, interval90EmpiricalCoverage: fraction }), 130),
  riskCoverage: array(object({ ...evaluationSnapshot, ...fields('requestedRetainedFraction actualRetainedFraction interval90EmpiricalCoverage', fraction), retainedRows: positiveCount,
    ...fields('maeEVPerAtom allRowsMaeEVPerAtom maeRelativeToAllRows', nonnegative) }), 300),
  deciles: array(object({ ...evaluationSnapshot, decile: positiveCount, rows: positiveCount,
    ...fields('meanDisagreementEVPerAtom minDisagreementEVPerAtom maxDisagreementEVPerAtom maeEVPerAtom meanIntervalWidthEVPerAtom', nonnegative), interval90EmpiricalCoverage: fraction }), 300),
  roles: array(object({ seed, role: literal('conservative', 'optimistic'), ...fields('queries nearStableHits referenceHullHits', count), precision: fraction,
    meanPredictedMeanEVPerAtom: finite, ...fields('meanCalibratedRadiusEVPerAtom meanDiversityDistance', nonnegative) }), 10),
  summary: object({ endpointAggregates: object(Object.fromEntries([...policies, 'initial_shared'].map((p) => [p, evaluationAggregate]))), evaluationRowsPerSeed: positiveCount,
    ...fields('featureScope riskCoverageMethod decileMethod roleScope', text), wholeChemicalSystemSeparationWithinSeed: bool, crossSeedPopulationsOverlap: literal(true), nominalIntervalCoverage: literal(0.9),
    ...fields('newModelFits newOracleQueries', literal(0)), limits: array(text) }), sourceIds });
const referenceMembership = object({ inventorySystem: literal('Ca-Mg-O', 'Mg-O'), ...fields('materialId formula chemicalSystem', text), executionAtoms: positiveCount,
  ...fields('spinReviewRequired expensiveReferenceFlag elementalEndpointEntry acceptedFreshCompatibleQe blocksFullInventoryHull', bool), acceptedJobId: nullable(text),
  status: literal('accepted_relaxed_and_finite_checked', 'uncomputed_fresh_compatible_QE') });
const referenceCoverage = object({ ...fields('frozenEntries acceptedFreshCompatibleQe missing missingSpinReviewEntries missingElementalEntries', count), fullInventoryComplete: literal(false) });
const dft = object({ jobs: array(object({ jobId: text, phase: positiveCount,
  role: literal('known_MgO_engine_pilot', 'candidate', 'perturbation', 'reference', 'sensitivity'), formula: text, atoms: positiveCount, calculation: literal('scf', 'vc-relax'),
  exitCode: nullable(count), ...fields('jobDone terminalScfAccepted stationaryAtThisSetting acceptedWithFinalGeometrySensitivity', bool),
  energyEVPerAtom: nullable(finite), ...fields('maxForceEVPerAngstrom maxFullStressKbar', nullable(nonnegative)), ...fields('cutoffRy densityCutoffRy', positive), kMesh: vec3, elapsedWallSeconds: nonnegative,
  evidenceLevel: literal('fixed_geometry_engine_readiness_only', 'accepted_relaxed_geometry_with_finite_sensitivity', 'fixed_geometry_SCF_sensitivity_only',
    'SCF_passed_independent_stationarity_failed', 'preliminary_stationary_setting_only', 'incomplete_terminal_SCF_no_accepted_final_energy'), sourceId: text, resultSourceId: nullable(text) }), 19),
  referenceMemberships: array(referenceMembership, 218), missingMemberships: array(referenceMembership, 215),
  acceptedGeometries: array(object({ acceptedJobId: text, energyEVPerAtom: finite,
    ...fields('maxForceEVPerAngstrom maxFullStressKbar cutoffShiftEVPerAtom kpointShiftEVPerAtom', nonnegative) }), 3),
  coverage: object({ 'Ca-Mg-O': referenceCoverage, 'Mg-O': referenceCoverage }), ...fields('membershipScope finiteCheckScope', text),
  knownMgoControl: object({ candidateMinusReferenceEVPerAtom: finite, energyOrderingResolved: bool, matchesReferenceStructure: bool }),
  reaction: object({ equation: text, anchorWeightedEnergyEVPerAtom: finite, candidateEnergyAvailable: literal(false), reactionEnergyAvailable: literal(false) }),
  ...fields('perturbationValidationComplete phononCalculationPerformed fullHullEstablished newStableMaterialEstablished', bool),
  decision: object({ ...fields('decision reason', text), ...fields('requiredAllowedUnfinishedJobs newNumericalJobsPhase6', count), stopUtc: utc, earlyClosureDoesNotRelaxFailedChecks: bool }), sourceIds });
const geometry = object({ actualAtoms: positiveCount, ...fields('formula reducedFormula', text), latticeRowsAngstrom: array(vec3, 3), fractionalCoordinates: array(vec3),
  sites: array(object({ siteIndex: count, species: array(object({ element: text, occupancy: fraction })) })), pbc: array(bool, 3), volumeAngstrom3: positive,
  minimumPeriodicDistanceAngstrom: nullable(positive), displayWrappingApplied: literal(false), periodicImagesAdded: literal(false) });
const chgnetSettings = object({ ...fields('modelVersion packageVersion optimizer filter', text), checkpointSha256: sha, maxSteps: positiveCount,
  forceThresholdEVPerAngstrom: positive, cellRelaxed: bool, imposedSymmetry: bool });
const qeSettings = object({ functional: text, ...fields('wavefunctionCutoffRy densityCutoffRy kSpacingTargetInverseAngstrom', positive), kMesh: vec3,
  nspin: positiveCount, occupations: text, pseudoSha256ByElement: dictionary(sha), executableSha256: sha });
const energy: Spec = (v, p) => {
  if (v === null) return;
  const row = record(v, p);
  object({ value: finite, unit: literal('eV/atom'), engine: literal('CHGNet', 'Quantum ESPRESSO PBE'), settingsScope: text,
    settings: row.engine === 'CHGNet' ? chgnetSettings : qeSettings, interpretation: text })(v, p);
};
const savedStage = object({ ...fields('candidateId stageId sourceId fallbackFigureLogicalName', text), parentStageId: nullable(text), recordedParentSourceId: nullable(text), sourceSha256: sha,
  evidence, method: stageMethod, stage: stageKind,
  eligibility: object({ ...fields('exactCellEligible workloadEligible', nullable(bool)), queueSelected: bool, newPhase5DFTDispatchAuthorized: literal(false), excluded: bool, reasons: array(text), interpretation: text }),
  dftValidation: object({ status: literal('not_performed_at_this_stage', 'accepted_numerical_control', 'accepted_numerical_reference'), jobId: nullable(text),
    ...fields('terminalSCFAccepted stationarityAccepted finiteSensitivityAccepted', nullable(bool)), ...fields('newStableMaterialEstablished fullHullEstablished', literal(false)) }),
  novelty: object({ ...fields('globalStructureNoveltyEstablished globalCompositionNoveltyEstablished generatorPretrainingOODEstablished', literal(false)), matchesPinnedGeometryIds: array(text),
    sameCompositionGeometriesTested: nullable(count), scope: text }), geometry,
  symmetry: object({ ...fields('spacegroupNumber requestedSpacegroupNumber', nullable(spacegroup)), ...fields('symprecAngstrom angleToleranceDegrees', nullable(positive)),
    evidenceSourceId: nullable(text), newSymmetryInferencePerformed: literal(false) }), energy,
  fallbackFigureDisplay: object({ coordinatesWrappedIntoUnitCell: literal(true), periodicImagesAdded: literal(false), physicalAtoms: positiveCount }) });

const staticSpecs: Record<string, Spec> = { 'summary.json': summary, 'replay/curves.json': curves, 'uncertainty.json': uncertainty,
  'generation.json': generation, 'dft.json': dft, 'structures/index.json': structures, 'claims.json': claims,
  'glossary.json': glossary, 'theme.json': theme, 'methods.json': methods, 'provenance.json': provenance };

/** A typed result is produced only after complete field validation. No coercion,
 * rounding, default-filling, inferred symmetry, or scientific computation occurs. */
export function guardDataset<Name extends JsonLogicalName>(name: Name, value: unknown): DatasetFor<Name> {
  object({ schemaVersion: literal(1), dataset: literal(name.replace(/\.json$/, '')), studyId: literal(DATA_RELEASE.studyId) })(value, name);
  const spec = staticSpecs[name] ?? (/^replay\/seed-2026102[2-6]\.json$/.test(name) ? replay :
    /^structures\/[^/]+\.json$/.test(name) ? savedStage : undefined);
  if (!spec) fail(name, 'a supported research dataset');
  spec(value, name);
  const logicalName: string = name;
  if (logicalName.startsWith('structures/') && logicalName !== 'structures/index.json') {
    const row = value as Record<string, unknown>;
    const g = row.geometry as Record<string, unknown>;
    if ((g.fractionalCoordinates as unknown[]).length !== g.actualAtoms || (g.sites as unknown[]).length !== g.actualAtoms) {
      fail(`${name}.geometry`, 'one coordinate and site per physical atom');
    }
    const display = row.fallbackFigureDisplay as Record<string, unknown>;
    if (display.physicalAtoms !== g.actualAtoms) fail(`${name}.fallbackFigureDisplay.physicalAtoms`, 'the saved physical atom count');
  }
  const data = value as Record<string, unknown>;
  const unique = (values: readonly unknown[], path: string) => {
    if (new Set(values).size !== values.length) fail(path, 'unique identities');
  };
  if (logicalName === 'structures/index.json') {
    const candidates = data.candidates as { candidateId: string; stageIds: string[]; defaultStageId: string }[];
    const stages = data.stages as { stageId: string; candidateId: string; parentStageId: string | null }[];
    const registeredCounts = data.counts as { entities: number; stages: number };
    unique(candidates.map((candidate) => candidate.candidateId), `${name}.candidates`);
    unique(stages.map((stage) => stage.stageId), `${name}.stages`);
    if (registeredCounts.entities !== candidates.length || registeredCounts.stages !== stages.length) fail(`${name}.counts`, 'the registered entity and stage counts');
    const byId = new Map(stages.map((stage) => [stage.stageId, stage]));
    for (const candidate of candidates) {
      if (!candidate.stageIds.includes(candidate.defaultStageId)) fail(`${name}.candidates.defaultStageId`, 'one of the candidate stages');
      for (const id of candidate.stageIds) {
        if (byId.get(id)?.candidateId !== candidate.candidateId) fail(`${name}.candidates.stageIds`, 'stages owned by the candidate');
      }
    }
  }
  if (logicalName === 'replay/curves.json') {
    unique(data.seeds as unknown[], `${name}.seeds`);
    unique(data.policies as unknown[], `${name}.policies`);
    const points = data.points as { seed: number; policy: string; queries: number }[];
    unique(points.map((p) => `${p.seed}/${p.policy}/${p.queries}`), `${name}.points`);
  }
  if (/^replay\/seed-/.test(logicalName)) {
    if (`replay/seed-${data.seed}.json` !== name) fail(`${name}.seed`, 'the seed in the logical filename');
    const histories = data.histories as { policy: string; batches: { round: number; queries: { queryNumber: number }[] }[] }[];
    unique(histories.map((history) => history.policy), `${name}.histories`);
    for (const history of histories) {
      history.batches.forEach((batch, index) => {
        if (batch.round !== index + 1) fail(`${name}.histories.batches.round`, 'the recorded round order');
        batch.queries.forEach((query, queryIndex) => {
          if (query.queryNumber !== index * 10 + queryIndex + 1) fail(`${name}.histories.batches.queries.queryNumber`, 'the recorded query order');
        });
      });
    }
  }
  if (logicalName === 'provenance.json') unique((data.sources as { sourceId: string }[]).map((source) => source.sourceId), `${name}.sources`);
  if (logicalName === 'claims.json') unique((data.claims as { id: string }[]).map((claim) => claim.id), `${name}.claims`);
  if (logicalName === 'glossary.json') unique((data.terms as { id: string }[]).map((term) => term.id), `${name}.terms`);
  return value as DatasetFor<Name>;
}
