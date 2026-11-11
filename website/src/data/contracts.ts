/** Frozen public research contracts. Runtime validation remains mandatory. */
export type SourceId = string;
export type CandidateId = string;
export type StageId = string;
export type Sha256 = string;
export type IsoUtc = string;
export type ReplaySeed = 20261022 | 20261023 | 20261024 | 20261025 | 20261026;
export type Policy = "full" | "quality" | "quality_diversity" | "random" | "uncertainty";
export type EvaluationPolicy = Policy | "initial_shared";
export type Round = 1 | 2 | 3 | 4 | 5;
export type BatchBudget = 0 | 10 | 20 | 30 | 40 | 50;
export type Control = "mgo_rocksalt" | "tio2_rutile";
export type Arm = "nontrivial" | "p1";
export type CohortScope = "primary_first8" | "supplementary_topup_only";
export type PairScope = "primary_first8_per_arm" | "supplementary_primary_plus_topup_pool";
export type InventorySystem = "Ca-Mg-O" | "Mg-O";
export type Vec3 = readonly [number, number, number];
export type Matrix3 = readonly [Vec3, Vec3, Vec3];
export type Bool3 = readonly [boolean, boolean, boolean];
export type ElementCounts = Readonly<Record<string, number>>;

export interface DataEnvelope<Name extends string = string> {
  readonly schemaVersion: 1;
  readonly dataset: Name;
  readonly studyId: string;
}
export interface DescriptiveStatistics {
  readonly mean: number;
  readonly sampleStd: number;
  readonly min: number;
  readonly max: number;
  readonly values: readonly number[];
}
export interface PolicyEndpointStatistics {
  readonly nearStableHits: DescriptiveStatistics;
  readonly referenceHullHits: DescriptiveStatistics;
  readonly chemicalSystemCoverage: DescriptiveStatistics;
  readonly precisionAt50: DescriptiveStatistics;
}
export type PolicyStatistics = Readonly<Record<Policy, PolicyEndpointStatistics>>;
export interface ClaimMatrixRow {
  readonly claim: string;
  readonly status: string;
  readonly scope: string;
  readonly limitation: string;
}
export interface BudgetRow {
  readonly lane: "generation" | "chgnet_attempts" | "chgnet_wall" | "QE_wall";
  readonly cap: number;
  readonly charged: number;
  readonly remaining: number;
  readonly unit: "conservative_structure_slots" | "conservative_launch_slots" | "seconds";
  readonly interpretation: string;
}
export interface StudySummary extends DataEnvelope<"summary"> {
  readonly projectName: string;
  readonly researchTitle: string;
  readonly hypothesis: string;
  readonly studyStatus: "frozen_prototype";
  readonly demoMode: "recorded_evidence_replay";
  readonly newStableMaterialEstablished: false;
  readonly pipeline: readonly string[];
  readonly counts: {
    readonly replaySeeds: number; readonly policies: number;
    readonly historicalQueryEvents: number; readonly distinctSelectedHistoricalMaterials: number;
    readonly evaluationSnapshots: number; readonly actualCrystalFormerDraws: number;
    readonly newFormulaDraws: number; readonly newFormulaExactValid: number;
    readonly excludedNewFormulaLargerCellDiagnostics: number; readonly modelSelectedStructures: number;
    readonly prototypeBaselines: number; readonly sameCompositionModelReferences: number;
    readonly qeAttempts: number; readonly acceptedRelaxedQeGeometries: number;
    readonly acceptedOriginalSourceReferenceIds: number; readonly consolidatedResearchChecksPassed: number;
  };
  readonly policyStatistics: PolicyStatistics;
  readonly fullMinusQualityHits: DescriptiveStatistics;
  readonly findings: readonly string[];
  readonly scientificLimits: readonly string[];
  readonly claims: readonly ClaimMatrixRow[];
  readonly budgets: readonly BudgetRow[];
  readonly numericalStudyFrozen: true;
  readonly newExperimentsInWebsiteExport: 0;
  readonly sourceIds: readonly SourceId[];
}

export interface ReplayCumulative {
  readonly queries: BatchBudget;
  readonly nearStableHits: number;
  readonly referenceHullHits: number;
  readonly chemicalSystemCoverage: number;
}
export interface ReplayPoint extends ReplayCumulative {
  readonly seed: ReplaySeed;
  readonly policy: Policy;
}
export interface ReplayEndpoint extends ReplayPoint { readonly precisionAt50: number }
export interface ReplayQuery {
  readonly queryNumber: number;
  readonly materialId: string;
  readonly formula: string;
  readonly reducedFormula: string;
  readonly chemicalSystem: string;
  readonly atoms: number;
  readonly role: "random" | "quality" | "quality_diversity" | "uncertainty" | "conservative" | "optimistic";
  readonly score: number | null;
  readonly predictedMeanEVPerAtom: number;
  readonly calibratedRadiusEVPerAtom: number;
  readonly diversityAtSelection: number;
  readonly revealedLabelEVPerAtom: number;
  readonly nearStableHit: boolean;
  readonly referenceHullHit: boolean;
}
export interface RecordedIdentity { readonly utc: IsoUtc; readonly sha256: Sha256 }
export interface ReplayBatch {
  readonly round: Round;
  readonly decision: RecordedIdentity;
  readonly reveal: RecordedIdentity;
  readonly queries: readonly ReplayQuery[];
  readonly cumulativeAfterReveal: ReplayCumulative;
}
export interface ReplayHistory { readonly policy: Policy; readonly batches: readonly ReplayBatch[] }
export interface ReplayDataset extends DataEnvelope<`replay/seed-${ReplaySeed}`> {
  readonly seed: ReplaySeed;
  readonly scope: string;
  readonly sourceIds: readonly SourceId[];
  readonly histories: readonly ReplayHistory[];
}
export interface ReplayCurves extends DataEnvelope<"replay/curves"> {
  readonly seeds: readonly ReplaySeed[];
  readonly policies: readonly Policy[];
  readonly thresholds: {
    readonly nearStableEVPerAtom: 0.05; readonly referenceHullEVPerAtom: 0;
    readonly comparison: "less_than_or_equal"; readonly label: "historical signed hull distance";
  };
  readonly points: readonly ReplayPoint[];
  readonly zeroQueryOrigin: {
    readonly queries: 0; readonly nearStableHits: 0; readonly referenceHullHits: 0;
    readonly chemicalSystemCoverage: 0; readonly precision: null;
    readonly origin: "derived_zero_state"; readonly label: string;
  };
  readonly endpoints: readonly ReplayEndpoint[];
  readonly policyStatistics: PolicyStatistics;
  readonly fullMinusQualityHits: DescriptiveStatistics;
  readonly sourceIds: readonly SourceId[];
}

export interface EvaluationSnapshot {
  readonly seed: ReplaySeed; readonly policy: EvaluationPolicy; readonly queries: BatchBudget;
}
export interface EvaluationMetrics extends EvaluationSnapshot {
  readonly rows: number; readonly maeEVPerAtom: number; readonly rmseEVPerAtom: number;
  readonly disagreementAbsoluteErrorSpearman: number;
  readonly interval90EmpiricalCoverage: number; readonly meanIntervalWidthEVPerAtom: number;
  readonly calibrationScale: number;
}
export interface RiskCoverage extends EvaluationSnapshot {
  readonly requestedRetainedFraction: number; readonly retainedRows: number;
  readonly actualRetainedFraction: number; readonly maeEVPerAtom: number;
  readonly allRowsMaeEVPerAtom: number; readonly maeRelativeToAllRows: number;
  readonly interval90EmpiricalCoverage: number;
}
export interface UncertaintyDecile extends EvaluationSnapshot {
  readonly decile: number; readonly rows: number;
  readonly meanDisagreementEVPerAtom: number; readonly minDisagreementEVPerAtom: number;
  readonly maxDisagreementEVPerAtom: number; readonly maeEVPerAtom: number;
  readonly interval90EmpiricalCoverage: number; readonly meanIntervalWidthEVPerAtom: number;
}
export interface RoleDiagnostic {
  readonly seed: ReplaySeed; readonly role: "conservative" | "optimistic";
  readonly queries: number; readonly nearStableHits: number; readonly precision: number;
  readonly referenceHullHits: number; readonly meanPredictedMeanEVPerAtom: number;
  readonly meanCalibratedRadiusEVPerAtom: number; readonly meanDiversityDistance: number;
}
export interface EvaluationAggregate {
  readonly maeEVPerAtom: DescriptiveStatistics; readonly rmseEVPerAtom: DescriptiveStatistics;
  readonly disagreementAbsoluteErrorSpearman: DescriptiveStatistics;
  readonly interval90EmpiricalCoverage: DescriptiveStatistics;
  readonly meanIntervalWidthEVPerAtom: DescriptiveStatistics;
  readonly calibrationScale: DescriptiveStatistics;
}
export interface UncertaintyDataset extends DataEnvelope<"uncertainty"> {
  readonly evaluationMetrics: readonly EvaluationMetrics[];
  readonly riskCoverage: readonly RiskCoverage[];
  readonly deciles: readonly UncertaintyDecile[];
  readonly roles: readonly RoleDiagnostic[];
  readonly summary: {
    readonly endpointAggregates: Readonly<Record<EvaluationPolicy, EvaluationAggregate>>;
    readonly evaluationRowsPerSeed: number; readonly featureScope: string;
    readonly riskCoverageMethod: string; readonly decileMethod: string; readonly roleScope: string;
    readonly wholeChemicalSystemSeparationWithinSeed: boolean;
    readonly crossSeedPopulationsOverlap: true; readonly nominalIntervalCoverage: 0.9;
    readonly newModelFits: 0; readonly newOracleQueries: 0; readonly limits: readonly string[];
  };
  readonly sourceIds: readonly SourceId[];
}

export interface GenerationCohort {
  readonly scope: CohortScope; readonly kind: "control" | "new_composition";
  readonly control: Control | null; readonly arm: Arm | null; readonly formula: string;
  readonly draws: number; readonly exactValid: number; readonly exactValidUnique: number;
  readonly validRequestedSpacegroup: number; readonly excludedLargerCellDiagnostics: number;
}
export interface GenerationDraw {
  readonly candidateId: CandidateId; readonly scope: CohortScope;
  readonly kind: "control" | "new_composition"; readonly control: Control | null;
  readonly arm: Arm | null; readonly formula: string;
  readonly requestedSpacegroup: number | null; readonly measuredSpacegroup: number | null;
  readonly atoms: number; readonly requestedAtoms: number; readonly actualCounts: ElementCounts;
  readonly exactCountsMatch: boolean; readonly minimumPeriodicDistanceAngstrom: number | null;
  readonly geometryValid: boolean; readonly valid: boolean; readonly duplicateOf: CandidateId | null;
  readonly correctRatioGeometryWithinCapDiagnosticOnly: boolean;
  readonly differentCellCountDiagnosticExcluded: boolean; readonly largerCellDiagnosticExcluded: boolean;
  readonly sourceId: SourceId; readonly geometrySourceSha256: Sha256;
}
export interface PrototypeBaseline {
  readonly candidateId: CandidateId; readonly parentMaterialId: string; readonly targetFormula: string;
  readonly atoms: number; readonly initialGeometryValid: boolean; readonly chgnetConverged: boolean;
  readonly finalSpacegroup: number; readonly chgnetEnergyEVPerAtom: number;
  readonly freshDftSubmitted: boolean; readonly stableMaterialEstablished: boolean;
}
export interface RelaxedStructureRecord {
  readonly candidateId: CandidateId;
  readonly role: "symmetry" | "prototype" | "same_composition_reference";
  readonly control: Control | null; readonly arm: Arm | null; readonly atoms: number;
  readonly finalFormula: string; readonly chgnetEnergyEVPerAtom: number | null;
  readonly optimizerSteps: number | null; readonly converged: boolean;
  readonly filterFmaxEVPerAngstrom: number | null; readonly finalSpacegroup: number | null;
  readonly spacegroupSymprecAngstrom: 0.01;
  readonly matchesPinnedMpSameCompositionGeometryIds: readonly string[];
  readonly sameCompositionMpGeometriesTested: number;
  readonly globalStructureNoveltyEstablished: boolean; readonly newStableMaterialEstablished: boolean;
  readonly sourceId: SourceId; readonly geometrySourceId: SourceId | null;
  readonly geometrySourceSha256: Sha256;
}
export interface SymmetryPair {
  readonly control: Control; readonly scope: PairScope; readonly quotaPerArm: number;
  readonly nontrivialCandidateId: CandidateId; readonly p1CandidateId: CandidateId;
  readonly p1MinusNontrivialChgnetEVPerAtom: number; readonly relaxedPairStructureMatch: boolean;
  readonly energyDistributionEstablished: boolean; readonly dftStabilityComparison: boolean;
}
export interface CompositionNovelty {
  readonly formula: string; readonly counts: ElementCounts;
  readonly mpMatchingCompositionRecords: number; readonly wbmMatchingCompositionRecords: number;
  readonly absentFromBothPinnedSnapshots: boolean; readonly globalCompositionNoveltyEstablished: boolean;
  readonly generatorPretrainingOodEstablished: boolean; readonly dftConfirmedStability: boolean;
}
export interface GenerationDataset extends DataEnvelope<"generation"> {
  readonly cohorts: readonly GenerationCohort[]; readonly draws: readonly GenerationDraw[];
  readonly excluded: readonly GenerationDraw[]; readonly excludedScope: string;
  readonly prototypes: readonly PrototypeBaseline[]; readonly relaxedStructures: readonly RelaxedStructureRecord[];
  readonly modelEnergyScope: string; readonly modelNoveltyScope: string;
  readonly symmetryPairs: readonly SymmetryPair[]; readonly compositionNovelty: readonly CompositionNovelty[];
  readonly catalogScope: {
    readonly mpSnapshot: string; readonly wbmSnapshot: string;
    readonly populations: Readonly<Record<"mp" | "wbm", { readonly records: number; readonly uniqueCompositions: number }>>;
    readonly scope: string;
  };
  readonly summary: {
    readonly actualCrystalFormerDraws: number; readonly newFormulaDraws: number;
    readonly newFormulaExactValid: number; readonly modelSelectedStructures: number;
    readonly prototypeBaselines: number; readonly anataseMinusRutileChgnetEVPerAtom: number;
    readonly primaryYieldDenominatorsUnchanged: true; readonly scope: string; readonly limits: readonly string[];
  };
  readonly sourceIds: readonly SourceId[];
}

export type DftEvidenceLevel = "fixed_geometry_engine_readiness_only" |
  "accepted_relaxed_geometry_with_finite_sensitivity" | "fixed_geometry_SCF_sensitivity_only" |
  "SCF_passed_independent_stationarity_failed" | "preliminary_stationary_setting_only" |
  "incomplete_terminal_SCF_no_accepted_final_energy";
export interface DftJob {
  readonly jobId: string; readonly phase: number;
  readonly role: "known_MgO_engine_pilot" | "candidate" | "perturbation" | "reference" | "sensitivity";
  readonly formula: string; readonly atoms: number; readonly calculation: "scf" | "vc-relax";
  readonly exitCode: number | null; readonly jobDone: boolean; readonly terminalScfAccepted: boolean;
  readonly stationaryAtThisSetting: boolean; readonly acceptedWithFinalGeometrySensitivity: boolean;
  readonly energyEVPerAtom: number | null; readonly maxForceEVPerAngstrom: number | null;
  readonly maxFullStressKbar: number | null; readonly cutoffRy: number; readonly densityCutoffRy: number;
  readonly kMesh: Vec3; readonly elapsedWallSeconds: number; readonly evidenceLevel: DftEvidenceLevel;
  readonly sourceId: SourceId; readonly resultSourceId: SourceId | null;
}
export interface ReferenceMembership {
  readonly inventorySystem: InventorySystem; readonly materialId: string; readonly formula: string;
  readonly chemicalSystem: string; readonly executionAtoms: number; readonly spinReviewRequired: boolean;
  readonly expensiveReferenceFlag: boolean; readonly elementalEndpointEntry: boolean;
  readonly acceptedFreshCompatibleQe: boolean; readonly acceptedJobId: string | null;
  readonly status: "accepted_relaxed_and_finite_checked" | "uncomputed_fresh_compatible_QE";
  readonly blocksFullInventoryHull: boolean;
}
export interface ReferenceCoverage {
  readonly frozenEntries: number; readonly acceptedFreshCompatibleQe: number; readonly missing: number;
  readonly fullInventoryComplete: false; readonly missingSpinReviewEntries: number; readonly missingElementalEntries: number;
}
export interface AcceptedDftGeometry {
  readonly acceptedJobId: string; readonly energyEVPerAtom: number; readonly maxForceEVPerAngstrom: number;
  readonly maxFullStressKbar: number; readonly cutoffShiftEVPerAtom: number; readonly kpointShiftEVPerAtom: number;
}
export interface DftDataset extends DataEnvelope<"dft"> {
  readonly jobs: readonly DftJob[]; readonly referenceMemberships: readonly ReferenceMembership[];
  readonly missingMemberships: readonly ReferenceMembership[]; readonly acceptedGeometries: readonly AcceptedDftGeometry[];
  readonly coverage: Readonly<Record<InventorySystem, ReferenceCoverage>>;
  readonly membershipScope: string; readonly finiteCheckScope: string;
  readonly knownMgoControl: { readonly candidateMinusReferenceEVPerAtom: number;
    readonly energyOrderingResolved: boolean; readonly matchesReferenceStructure: boolean };
  readonly reaction: { readonly equation: string; readonly anchorWeightedEnergyEVPerAtom: number;
    readonly candidateEnergyAvailable: false; readonly reactionEnergyAvailable: false };
  readonly perturbationValidationComplete: boolean; readonly phononCalculationPerformed: boolean;
  readonly fullHullEstablished: boolean; readonly newStableMaterialEstablished: boolean;
  readonly decision: { readonly decision: string; readonly reason: string;
    readonly requiredAllowedUnfinishedJobs: number; readonly newNumericalJobsPhase6: number;
    readonly stopUtc: IsoUtc; readonly earlyClosureDoesNotRelaxFailedChecks: boolean };
  readonly sourceIds: readonly SourceId[];
}

export type StageKind = "generated" | "prototype_initial" | "catalog_initial" |
  "generated_excluded" | "model_relaxed" | "accepted_dft";
export type StageMethod = "crystalformer" | "prototype_substitution" | "catalog_reference" | "chgnet" | "quantum_espresso";
export interface EvidenceReference { readonly sourceId: SourceId; readonly field: string | null }
export interface SavedGeometry {
  readonly actualAtoms: number; readonly formula: string; readonly reducedFormula: string;
  readonly latticeRowsAngstrom: Matrix3; readonly fractionalCoordinates: readonly Vec3[];
  readonly sites: readonly { readonly siteIndex: number;
    readonly species: readonly { readonly element: string; readonly occupancy: number }[] }[];
  readonly pbc: Bool3; readonly volumeAngstrom3: number;
  readonly minimumPeriodicDistanceAngstrom: number | null;
  readonly displayWrappingApplied: false; readonly periodicImagesAdded: false;
}
export interface StageEligibility {
  readonly exactCellEligible: boolean | null; readonly workloadEligible: boolean | null;
  readonly queueSelected: boolean; readonly newPhase5DFTDispatchAuthorized: false;
  readonly excluded: boolean; readonly reasons: readonly string[]; readonly interpretation: string;
}
export interface StageDftValidation {
  readonly status: "not_performed_at_this_stage" | "accepted_numerical_control" | "accepted_numerical_reference";
  readonly jobId: string | null; readonly terminalSCFAccepted: boolean | null;
  readonly stationarityAccepted: boolean | null; readonly finiteSensitivityAccepted: boolean | null;
  readonly newStableMaterialEstablished: false; readonly fullHullEstablished: false;
}
export interface StageNovelty {
  readonly globalStructureNoveltyEstablished: false; readonly globalCompositionNoveltyEstablished: false;
  readonly generatorPretrainingOODEstablished: false; readonly matchesPinnedGeometryIds: readonly string[];
  readonly sameCompositionGeometriesTested: number | null; readonly scope: string;
}
export interface StageSymmetry {
  readonly spacegroupNumber: number | null; readonly requestedSpacegroupNumber: number | null;
  readonly symprecAngstrom: number | null; readonly angleToleranceDegrees: number | null;
  readonly evidenceSourceId: SourceId | null; readonly newSymmetryInferencePerformed: false;
}
export interface ChgnetSettings {
  readonly modelVersion: string; readonly checkpointSha256: Sha256; readonly packageVersion: string;
  readonly optimizer: string; readonly maxSteps: number; readonly forceThresholdEVPerAngstrom: number;
  readonly cellRelaxed: boolean; readonly filter: string; readonly imposedSymmetry: boolean;
}
export interface QeSettings {
  readonly functional: string; readonly wavefunctionCutoffRy: number; readonly densityCutoffRy: number;
  readonly kMesh: Vec3; readonly kSpacingTargetInverseAngstrom: number; readonly nspin: number;
  readonly occupations: string; readonly pseudoSha256ByElement: Readonly<Record<string, Sha256>>;
  readonly executableSha256: Sha256;
}
export type StageEnergy = {
  readonly value: number; readonly unit: "eV/atom"; readonly engine: "CHGNet";
  readonly settingsScope: string; readonly settings: ChgnetSettings; readonly interpretation: string;
} | {
  readonly value: number; readonly unit: "eV/atom"; readonly engine: "Quantum ESPRESSO PBE";
  readonly settingsScope: string; readonly settings: QeSettings; readonly interpretation: string;
};
export interface SavedStage extends DataEnvelope<`structures/${string}`> {
  readonly candidateId: CandidateId; readonly stageId: StageId; readonly parentStageId: StageId | null;
  readonly recordedParentSourceId: SourceId | null; readonly sourceId: SourceId; readonly sourceSha256: Sha256;
  readonly evidence: readonly EvidenceReference[]; readonly method: StageMethod; readonly stage: StageKind;
  readonly eligibility: StageEligibility; readonly dftValidation: StageDftValidation;
  readonly novelty: StageNovelty; readonly geometry: SavedGeometry; readonly symmetry: StageSymmetry;
  readonly energy: StageEnergy | null;
  readonly fallbackFigureLogicalName: string;
  readonly fallbackFigureDisplay: {
    readonly coordinatesWrappedIntoUnitCell: true;
    readonly periodicImagesAdded: false;
    readonly physicalAtoms: number;
  };
}
export interface CandidateEntity {
  readonly candidateId: CandidateId;
  readonly role: "symmetry" | "prototype" | "same_composition_reference" | "excluded_diagnostic" | "source_reference";
  readonly method: "crystalformer" | "prototype_substitution" | "catalog_reference";
  readonly formula: string; readonly actualAtoms: number; readonly stageIds: readonly StageId[];
  readonly defaultStageId: StageId; readonly eligible: boolean; readonly newStableMaterialEstablished: false;
  readonly evidence: readonly EvidenceReference[];
  readonly control?: Control | null; readonly arm?: Arm | null; readonly comparisonScope?: PairScope | null;
  readonly parentMaterialId?: string | null; readonly referenceMaterialId?: string | null;
  readonly referencePhase?: string | null; readonly cachedModelReuse?: boolean;
}
export interface StageIndexEntry {
  readonly candidateId: CandidateId; readonly stageId: StageId; readonly stage: StageKind;
  readonly parentStageId: StageId | null; readonly logicalFile: `structures/${string}.json`;
  readonly sourceId: SourceId; readonly sourceSha256: Sha256; readonly actualAtoms: number;
  readonly fallbackFigureLogicalName: string;
}
export interface IncompleteDftEvidence {
  readonly evidenceId: string; readonly candidateId: CandidateId; readonly kind: "incomplete_dft_perturbation";
  readonly sourceId: SourceId; readonly jobIds: readonly string[]; readonly acceptedTerminalStageId: null;
  readonly energy: null; readonly status: "time_limit_before_terminal_convergence";
  readonly explanation: string; readonly newStableMaterialEstablished: false;
}
export interface StructureIndex extends DataEnvelope<"structures/index"> {
  readonly candidates: readonly CandidateEntity[]; readonly stages: readonly StageIndexEntry[];
  readonly coreExamples: readonly { readonly id: string; readonly candidateId: CandidateId;
    readonly stageIds?: readonly StageId[] }[];
  readonly evidenceOnly: readonly IncompleteDftEvidence[];
  readonly counts: { readonly entities: number; readonly stages: number; readonly modelFinals: number;
    readonly acceptedQERelaxedGeometries: number; readonly excludedExamples: number };
  readonly geometryConvention: { readonly latticeVectors: "rows"; readonly latticeUnit: "angstrom";
    readonly coordinates: "fractional"; readonly cartesianFormula: "fractional @ lattice";
    readonly siteIndices: string; readonly displayWrappingApplied: false; readonly periodicImagesAdded: false;
    readonly physicalAtomsExcludeDisplayImages: true };
  readonly validation: { readonly nonOrthogonalStageIds: readonly StageId[];
    readonly newSymmetryInference: false; readonly newMatching: false;
    readonly newModelInference: false; readonly newRelaxations: false };
  readonly scope: string;
}

export interface NarrativeClaim {
  readonly id: string; readonly title: string; readonly text: string;
  readonly sourceIds: readonly SourceId[]; readonly claimStatus: "supported_with_stated_scope";
}
export interface ClaimsDataset extends DataEnvelope<"claims"> {
  readonly claims: readonly NarrativeClaim[]; readonly newStableMaterialEstablished: false;
  readonly notes: readonly string[];
}
export interface GlossaryDataset extends DataEnvelope<"glossary"> {
  readonly terms: readonly { readonly id: string; readonly label: string; readonly definition: string;
    readonly unit: string | null }[];
}
export interface ThemeDataset extends DataEnvelope<"theme"> {
  readonly palette: { readonly paper: string; readonly graphite: string; readonly copper: string; readonly selection: string };
  readonly policyColours: Readonly<Record<EvaluationPolicy, string>>;
  readonly policyLabels: Readonly<Record<EvaluationPolicy, string>>;
  readonly elementColours: Readonly<Record<string, string>>;
  readonly statusLabels: Readonly<Record<"generated" | "prototype_initial" | "catalog_initial" | "generated_excluded" |
    "model_relaxed" | "accepted_dft" | "excluded" | "incomplete" | "not_evaluated", string>>;
  readonly typography: { readonly heading: string; readonly body: string; readonly numeric: string };
  readonly motion: { readonly autoRotationDefault: false; readonly respectReducedMotion: true };
}
export interface Attribution {
  readonly name: string; readonly role: string; readonly licence: string; readonly credit: string;
  readonly url: string; readonly licenceUrl: string | null; readonly modifications: string;
}
export interface MethodsDataset extends DataEnvelope<"methods"> {
  readonly title: string; readonly headline: string; readonly description: string;
  readonly executionMode: "recorded_research_only"; readonly liveScientificCompute: false;
  readonly target: { readonly name: string; readonly unit: "eV/atom";
    readonly nearStableInclusive: 0.05; readonly referenceHullInclusive: 0; readonly freshQETargetCompatible: false };
  readonly workflow: readonly { readonly id: "propose" | "generate" | "screen" | "select" | "relax" | "validate" | "compare";
    readonly label: string; readonly description: string }[];
  readonly sourceIds: readonly SourceId[]; readonly attributions: readonly Attribution[];
  readonly externalPublicationLinks: readonly { readonly kind: "repository" | "writeup" | "video";
    readonly label: string; readonly url: null; readonly status: "not_published" }[];
  readonly sourceRegistryReference: string; readonly scope: readonly string[];
}
export interface PublicSource {
  readonly sourceId: SourceId; readonly label: string; readonly sha256: Sha256;
  readonly bytes: number; readonly description: string;
}
export interface ProvenanceDataset extends DataEnvelope<"provenance"> {
  readonly sources: readonly PublicSource[];
  readonly studyFrozenAt: IsoUtc;
  readonly sourceInventorySha256: Sha256;
  readonly sourceIdentityMeaning: string;
  readonly units: { readonly energy: "eV/atom"; readonly lattice: "angstrom";
    readonly force: "eV/angstrom"; readonly stress: "kbar"; readonly cutoff: "Ry";
    readonly time: "seconds"; readonly fraction: "0 to 1" };
  readonly newExperiments: 0;
  readonly scope: string;
  readonly attributionDataset: "methods.json";
  readonly claimDataset: "claims.json";
}

/** One immutable data release. File paths are relative to public/research/. */
export interface DataManifestFile {
  readonly logicalName: string; readonly path: string; readonly sha256: Sha256;
  readonly bytes: number; readonly mediaType: "application/json" | "image/png" | "text/plain; charset=utf-8";
}
export interface DataManifest {
  readonly schemaVersion: 1; readonly studyId: string; readonly dataReleaseId: string;
  readonly generatedAt: IsoUtc; readonly studyFrozenAt: IsoUtc | null;
  readonly sourceInventorySha256: Sha256; readonly files: readonly DataManifestFile[];
  readonly uiBuildId: string | null;
  readonly scope: string;
}
export type ExportManifest = DataManifest;
/** Generated src/data/release.ts pins the manifest; a future UI build has its own ID. */
export interface DataReleaseReference {
  readonly schemaVersion: 1; readonly studyId: string; readonly dataReleaseId: string;
  readonly manifestPath: string; readonly manifestSha256: Sha256;
}
export interface StaticDatasetMap {
  readonly "summary.json": StudySummary;
  readonly "replay/curves.json": ReplayCurves;
  readonly "uncertainty.json": UncertaintyDataset;
  readonly "generation.json": GenerationDataset;
  readonly "dft.json": DftDataset;
  readonly "structures/index.json": StructureIndex;
  readonly "claims.json": ClaimsDataset;
  readonly "glossary.json": GlossaryDataset;
  readonly "theme.json": ThemeDataset;
  readonly "methods.json": MethodsDataset;
  readonly "provenance.json": ProvenanceDataset;
}
export type JsonLogicalName = keyof StaticDatasetMap | `replay/seed-${ReplaySeed}.json` | `structures/${string}.json`;
export type DatasetFor<Name extends JsonLogicalName> = Name extends keyof StaticDatasetMap
  ? StaticDatasetMap[Name] : Name extends `replay/seed-${ReplaySeed}.json`
  ? ReplayDataset : Name extends `structures/${string}.json` ? SavedStage : never;
export type ResearchDataset = StaticDatasetMap[keyof StaticDatasetMap] | ReplayDataset | SavedStage;
