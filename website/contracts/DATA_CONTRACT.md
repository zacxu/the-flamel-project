# Frozen research data contract

Schema version **1**. The authoritative TypeScript shapes are in [contracts.ts](../src/data/contracts.ts). The website consumes curated exports of the frozen 22 October 2026 study; export performs no training, predictor inference, generation, relaxation, oracle query or QE dispatch.

## Identity, release and loading

Every JSON dataset has `schemaVersion`, `dataset` and `studyId`. `dataset` is the logical filename without `.json`, such as `replay/curves` or `structures/prototype_CaMg2O3--model_relaxed`. `studyId` identifies the numerical study, not an individual website build.

The generated `src/data/release.ts` pins `schemaVersion`, `studyId`, `dataReleaseId`, `manifestPath` and `manifestSha256`. Load that exact manifest, then resolve each logical name through its `files` entry. Each entry records `logicalName`, immutable relative `path`, SHA-256, byte count and media type. Paths are relative to the public `research/` directory. Never construct a guessed hashed filename or fetch an unrelated fixed-name dataset. Study freeze time, export generation time and the future UI build ID are distinct. `studyFrozenAt` may be null if unavailable; an unavailable date is not invented.

`DatasetFor<LogicalName>` maps fixed datasets, the five seed shards and structure-stage shards to their corresponding types. Types do not authenticate network JSON: runtime checks must reject a mismatched schema/study/release, missing manifest entry, wrong hash/size or malformed record. Do not replace unavailable or corrupt evidence with a plausible value.

## Dataset inventory

| Logical dataset | Records / purpose |
|---|---|
| `summary.json` | Study question, frozen counts, independently recomputed policy statistics, claim matrix and four budget lanes |
| `replay/curves.json` | Five seeds, five policies, 125 measured nonzero batch points, 25 endpoints and inclusive thresholds |
| `replay/seed-{seed}.json` | Five policy histories, each containing five batches of ten selected queries |
| `uncertainty.json` | 130 evaluation snapshots; 300 risk/retention rows; 300 decile rows; ten role rows; scoped aggregate diagnostics |
| `generation.json` | Twelve cohorts; 88 emitted draws; twelve excluded new-formula diagnostics; four prototypes; eleven model result records; two symmetry pairs; six scoped composition proposals |
| `dft.json` | All nineteen QE attempts, three accepted relaxed geometries, 218 reference memberships and 215 missing memberships |
| `structures/index.json` | Fourteen distinct candidate/reference entities; 26 saved stages; valid parent relations; six core examples; incomplete evidence without an accepted stage |
| `structures/{stageId}.json` | One verified saved geometry plus stage-specific method, energy, symmetry, eligibility and validation metadata |
| `claims.json`, `glossary.json`, `methods.json`, `theme.json` | Scoped explanations, units, seven workflow steps, attribution, publication availability and shared presentation values |
| `provenance.json` | Public source IDs, safe labels, SHA-256, byte counts and descriptions; no local paths or source-file contents |
| `figures/*.png` | Real saved research figures, located through the same manifest |

Counts describe the current frozen release. Arrays are readonly in TypeScript. Runtime validation additionally enforces uniqueness, source joins and the listed counts; an array type alone does not enforce a population size.

## Numbers, booleans, missing values and units

- Numeric JSON values are finite and retain source precision. Formatting or eV-to-meV conversion belongs to presentation; one eV/atom is 1,000 meV/atom. `NaN`, infinities and numeric strings are not public measurements.
- Booleans are JSON booleans. CSV `False` becomes `false`; JavaScript truthiness must never parse a CSV boolean. Unknown settings are explicit nulls, not inferred defaults.
- A missing optional measurement is `null`, not zero. Random-policy acquisition scores are null. A zero-step optimizer result is valid if the saved initial structure already satisfies its convergence criterion.
- Energy fields ending `EVPerAtom` use eV per actual physical atom. Force fields use eV/angstrom, stress uses kbar, lattice and distances use angstrom, volumes use angstrom cubed, QE cutoffs use Ry, and k-spacing uses inverse angstrom.
- Coverage, precision and retained fractions use the range zero to one, not percentage points. UI percentages multiply by 100. Reported sample standard deviations use the five split outcomes with denominator `n-1`; they are descriptive because the populations overlap.

## Replay and historical labels

Seeds are `20261022` through `20261026`. Policies are `full`, `quality`, `quality_diversity`, `random` and `uncertainty`. `initial_shared` is an evaluation snapshot, never a sixth acquisition policy. It occurs once per seed at zero queries.

Each seed shard groups a history into recorded batches. `decision` and `reveal` retain original UTC timestamps and hashes. Each query has selected material ID, formula/system, physical atom count, recorded mean/radius, role, diversity, optional score and the historical revealed label. Only the 720 distinct queried IDs were joined to local metadata; the full metadata table, oracle and evaluation target-ID population are absent.

Near-stable hits use the signed historical label **<= 0.05 eV/atom** and reference-hull hits use **<= 0**. Negative values are preserved. Export independently reconstructs cumulative hits and distinct selected chemical-system coverage at all 125 batch boundaries, then checks the frozen curves and 25 endpoints. Selected query IDs cannot repeat within one policy history; overlap across policies/seeds remains legitimate.

The 125 stored curve points exclude a zero-query origin. The separate `zeroQueryOrigin` is labelled `derived_zero_state`, with hits/coverage zero and precision **null**. It is a display origin with no acquired labels, not a measured extra snapshot. At intermediate unmeasured budgets, do not invent refits or interpolate individual research outcomes. Pre-reveal hiding applies consistently to visible and accessible labels; the outcomes are already present in public static data, so this is a teaching state, not access control. Aggregate mode has no individual history.

## Uncertainty diagnostics

There are 3,418 untouched evaluation rows per seed. `evaluationMetrics` contains the shared initial snapshot and five policy snapshots at each nonzero batch boundary. Risk curves and deciles use the shared initial snapshot plus each policy's 50-query endpoint. Risk data retain requested fraction, actual retained rows/fraction, absolute MAE and MAE relative to all rows. Retained rows follow `ceil(n * requestedFraction)`; actual fractions may differ slightly from requested values.

The nominal interval coverage is fixed at 0.9. Empirical coverage, disagreement/error Spearman association and retained-risk results are distinct. They do not guarantee calibration for arbitrary OOD chemistry, fresh generated crystals or QE energies. Conservative versus optimistic full-policy slots are observational, with 35 versus 15 selections per seed; no causal role effect is established.

## Generation, model records and composition scope

Keep `primary_first8` and `supplementary_topup_only` cohorts separate. The twelve exported `excluded` records are new-formula diagnostics; control diagnostics remain in the full 88-row draw table. None of the 48 new-formula draws passed the frozen exact-cell gate. A correct reduced ratio in a different expanded cell does not pass that gate.

`relaxedStructures` retains all eleven selected model results, including optimizer steps, filter force criterion, measured final SG with its recorded tolerance, catalog matches and verified final-geometry source IDs. A null measurement stays null; zero steps stays zero. Four prototypes are a separate method baseline and do not replace the empty transformer shortlist. Absolute CHGNet energies across different compositions are not formation energies or a stability ranking.

Each symmetry energy pair has one selected unique structure per arm. MgO uses the supplementary combined pool; TiO2 uses the primary pool. The P1-minus-conditioned difference is computed within composition, not across chemistries. This contrast does not isolate a trained architecture effect or establish an energy distribution.

The six composition proposals are absent only from the two pinned historical catalogs. Catalog absence and unmatched saved geometry subsets do not establish global novelty or absence from generator pretraining. Catalog populations and scope remain visible with the results.

## Saved geometry and stage lineage

`latticeRowsAngstrom` is a three-by-three matrix of **row vectors**. `fractionalCoordinates[i]` corresponds to `sites[i]` in saved zero-based order. Cartesian coordinates follow:

```text
cartesian = fractional @ latticeRowsAngstrom
fractional = cartesian @ inverse(latticeRowsAngstrom)
```

`sites` retains element/occupancy information; `pbc` retains three explicit periodic flags. The current release has ordered sites with one element at full occupancy. `actualAtoms` counts physical saved sites and excludes any later display images. No export wrapping, extra periodic images or symmetry inference is performed. Export validates conversion/periodic-distance round trips, including non-orthogonal saved cells.

Stage enums are `generated`, `prototype_initial`, `catalog_initial`, `generated_excluded`, `model_relaxed` and `accepted_dft`. Each stage points to its actual candidate and recorded parent stage/source. A same-formula structure is not automatically a parent. In particular the eight-atom model rocksalt reference and separately executed two-atom accepted source-QE reference remain distinct entities.

Every stage and stage-index row identifies a verified `fallbackFigureLogicalName` through the release manifest. `fallbackFigureDisplay` records that the static figure wraps the saved coordinates into the unit cell for display only, adds no periodic images and retains the physical atom count. This figure display transform does not change exported geometry, stage identity or atom count.

`energy` is null before a saved energy exists. Its `engine` discriminates CHGNet settings from QE settings. Preserve its unit, settings scope and interpretation; do not overlay incompatible engines or chemistry as though their absolute energies were interchangeable. Unknown symmetry metadata stays null. DFT acceptance, workload eligibility, queue selection and thermodynamic stability remain separate fields. The excluded twelve-atom CaMg2O3 draw stays separate from the six-atom prototype.

## QE evidence and overlapping inventories

Every attempted job remains accessible, including the pilot, sensitivities, independently nonstationary settings and failed terminal perturbation. `jobDone` or process exit zero does not imply `terminalScfAccepted`, stationarity or final-geometry sensitivity acceptance. The incomplete perturbation has no accepted energy or terminal geometry stage.

Three accepted relaxed geometries comprise known generated MgO, source-reference MgO and source-reference CaO. They cover **two** original source-reference IDs. Reference membership rows overlap between inventory systems: 218 memberships are not 218 distinct materials. Coverage is 2/161 in Ca-Mg-O and 1/57 in Mg-O; the 215 missing memberships remain accessible.

The known generated MgO matches its reference; the tiny energy ordering is unresolved. Finite adjacent cutoff/k-point checks are measured sensitivities, not a rigorous total error bound. No candidate CaMg2O3 QE energy, complete hull, accepted perturbation recovery, phonons, synthesis or newly established stable material is provided. A source hash proves file identity, not scientific acceptance.

## Sources, attribution and publication

Use public `sourceId` joins into `provenance.json`. Row-level table sources remain available where an original individual result reference is unsupported; for example the old engine pilot has a null `resultSourceId` and its `dft_jobs` source plus job ID. Do not reconstruct local filesystem paths from labels. Public payloads contain no full oracle, target-ID evaluation set, model checkpoints, executable environments, credentials, admin links or login/session URLs.

Methods include attributions, original source/licence URLs, modifications and unavailable publication links. A null publication URL with `not_published` is a visible unavailable state, never a clickable placeholder. Theme colours and labels aid interpretation; statuses also need text so meaning does not depend on colour.

Breaking field/meaning changes require a schema-version change and regenerated verified release. New UI builds may reuse an unchanged data release; they must retain that release's manifest and source-study identity. W1 supplies contracts and data, not an implemented website or verified hosting deployment.
