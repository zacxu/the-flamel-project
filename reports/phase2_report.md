# Phase 2 execution report

Phase 2 prepares the frozen inputs for the research experiments. The dataset, descriptors, group splits, acquisition rules, composition proposals, symmetry controls and DFT reference plan are saved. The machine-readable completion decision is [readiness.json](../artifacts/phase2/readiness.json); all integrity checks are in [audit.json](../artifacts/phase2/audit.json).

No predictor was fitted, no replay query was revealed, and no CrystalFormer sampling, CHGNet relaxation or QE job ran during Phase 2. Four deterministic prototype-substitution candidates were prepared and conservatively charged once each under the broad 128-structure ceiling. Geometry analysis and parsing input templates are preparation, not DFT calculations.

## Dataset, descriptors and five paired splits

The original eligibility definition remains unchanged: **8,294 oxide records across 1,866 chemical systems**, selected from the audited 256,963-record WBM release. Every eligible initial structure now has **408 finite float32 descriptors**, extracted in approximately 11 seconds with four workers. No structure failed extraction and no symmetry fallback was needed.

The shared `research_features.describe_structure(structure)` function uses composition fractions, elemental statistics, initial cell/periodic-distance descriptors, recomputed initial space group and Wyckoff information. The first 150 columns provide the diversity basis. The feature archive contains no target labels. Material IDs are join keys only; relaxed geometry, energy, band gap, prototype-population flags and substitution-round information are excluded from predictors. Wrapping/site-permutation, injected label/property, fallback and shared-function checks passed.

All **78 possible binary/ternary oxide chemical systems in the fixed 12-metal palette** are reserved. This excludes 476 eligible rows and covers every selected formula, stretch/reserve formula and control. It leaves **7,818 rows in 1,792 systems** for predictor partitions. This stronger reservation prevents a later reserve substitution from introducing chemistry already seen during predictor training or calibration.

| Partition, identical across policies within a seed | Rows per seed | Use |
|---|---:|---|
| Initial training | 2,000 | Initial predictor fitting |
| Calibration | 400 | Empirical uncertainty scaling |
| Hidden query pool | 2,000 | Five batches of ten retrospective label queries |
| Fixed untouched evaluation | 3,418 | Error, uncertainty/error association and interval coverage/width |
| Reserved fresh chemistry | 476 | Excluded from all four predictor partitions |

The five seeds are **20261022–20261026**. Each partition contains whole chemical systems, with no system or ID shared between partitions. Training covers all **68 individually occurring elements** in the nonreserved population, so query/evaluation chemistry withholds combinations rather than introducing entirely unseen elements. No target values influenced splitting.

The fixed evaluation cohort uses the existing split-file partition key `unused`. This role was clarified before any model fit or query, preserving every original split ID. The initial protocol and amendment reason are archived. Evaluation labels are available only to the separate evaluator; they cannot affect fitting, calibration, selection, hyperparameters or stopping. Queried rows never enter these out-of-sample metrics. Query-yield metrics use the selected pool rows separately.

Files: [features](../artifacts/phase2/features/feature_manifest.json), [splits](../artifacts/phase2/splits/manifest.json), [reservations](../artifacts/phase2/splits/reserved_systems.json), [separate oracle labels](../artifacts/phase2/splits/oracle_labels.csv).

## Frozen predictor and acquisition rules

The [protocol](../config/phase2_protocol.json) specifies five independently bootstrapped ExtraTrees regressors with 128 trees each, minimum leaf size two and two workers. All 408 descriptors enter the predictors. Hyperparameters and scoring coefficients are fixed; Phase 3 will measure their actual fitting cost.

Disagreement is the sample standard deviation of the five member predictions. Its floor is **0.01 eV/atom**. Calibration uses the 361st ordered normalized absolute residual among the 400 calibration records for a nominal 90% interval. The resulting half-width is `u = q90 * max(std, 0.01)`. This is empirical calibration under chemical-system shift; no arbitrary-OOD coverage guarantee is claimed.

Diversity uses the first 150 features, standardized once from initial training only, clipped to [-5,5]. Distance is the nearest root-mean-square Euclidean distance to initial training, already queried structures or current-batch choices, capped at one. Calibration/evaluation rows are not diversity anchors.

All policies maximize the following scores; `mu` and `u` are in eV/atom and `D` is the frozen diversity distance:

| Policy | Rule |
|---|---|
| Random | Uniform selection without replacement |
| Quality | `(0.05 - mu) / 0.05` |
| Quality plus diversity | `(0.05 - mu) / 0.05 + 0.5 D` |
| Uncertainty | `u / 0.05` |
| Full: first seven choices | `(0.05 - mu - u) / 0.05 + 0.5 D` |
| Full: last three choices | `(0.05 - mu + u) / 0.05 + 0.5 D` |

Nonrandom ties use material ID; diversity updates after each choice. All policies receive the same initial 2,400 labels and 50 additional query opportunities per seed. Each policy refits only on its own revealed labels. Eleven synthetic checks verify calibration rank, uncertainty floor, reproducibility, unique selections, ties, diversity updates, the seven/three exploration split and small fresh-cohort selection.

The fresh selector is the **initial seed-20261022 ensemble**, saved with calibration and normalization **before any replay pool label is revealed**. An adapted model or best-performing replay seed cannot replace it. The executable acquisition functions accept no oracle-label argument. The estimator settings were checked against [scikit-learn 1.7 documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html).

## Catalogs, compositions, controls and baselines

The full checked catalogs contain:

| Snapshot | Records | Unique reduced compositions |
|---|---:|---:|
| WBM released summary | 256,963 | 168,150 |
| MP 2023-02-07 archive, database release 2022.10.28 | 154,718 | 105,583 |

The MP archive's published MD5, observed SHA256, schema and record counts are verified. Composition screening uses the complete snapshots, not only the filtered oxide benchmark. Source energies, hull distances and band gaps do not enter formula ranking.

The fixed oxidation palette produced **1,372 distinct reduced formulas: 13 binary and 1,359 ternary**, all charge balanced and at most 20 atoms. **1,135** are absent from both snapshots. Ranking uses atom count, a Sn redox-ambiguity penalty, atomic-number cost proxy and canonical formula, with one chemical system represented before repeats.

| Default proposal | Reduced cell atoms | Assigned cation oxidation states | Generation group |
|---|---:|---|---|
| SnSrO2 | 4 | Sn +2, Sr +2 | P-1, SG2 |
| BaSnO2 | 4 | Ba +2, Sn +2 | P-1, SG2 |
| CaMg2O3 | 6 | Ca +2, Mg +2 | P-1, SG2 |
| Mg2SrO3 | 6 | Mg +2, Sr +2 | P-1, SG2 |
| Ca2ZnO3 | 6 | Ca +2, Zn +2 | P-1, SG2 |
| Ca2SrO3 | 6 | Ca +2, Sr +2 | P-1, SG2 |

Oxygen is -2. Eight reserves are frozen, including the two conditional stretch formulas. Each default formula receives eight attempted samples. SG2, exact cell counts, seeds and Wyckoff-multiplicity witnesses are fixed before generation; these witnesses prove count compatibility, not generation success or stable chemistry. The formula-free branch remains disabled.

Catalog absence means **new to these checked snapshots**. It does not establish global novelty, absence from the Alexandria generator training set, a distinct ordered phase rather than a possible solid-solution ratio, or stability. No proposal has yet passed fresh structural or DFT validation.

The matched controls are **Mg4O4/SG225** from mp-1265 and **Ti2O4/SG136 rutile** from mp-2657, each compared with P1 using exact expanded cells and the Phase 1 checkpoint/settings. The first eight attempts per arm are the primary denominator. MgO's existing SG225 pilot is reusable; its seven valid samples deduplicate to one rocksalt topology. Rutile has an internal oxygen coordinate, but multiple unique outcomes are not guaranteed. Random balanced relaxation quotas and deduplication tolerances are frozen.

Four prototype-substitution baselines are prepared for the first four formulas, with composition-correct template CIFs. Three same-composition reference plans are available: MgO, rutile and anatase. Brookite's 24-atom conventional cell exceeds the chosen reference-screening cap; that slot stays unused. These are plans and geometries, not completed CHGNet comparisons.

Files: [catalog manifest](../artifacts/phase2/catalogs/catalog_manifest.json), [selected formulas/reserves](../artifacts/phase2/compositions/selection.json), [generation settings](../artifacts/phase2/compositions/generation_protocol.json), [matched controls](../artifacts/phase2/controls/matched_protocol.json), [prototype plan](../artifacts/phase2/compositions/prototype_plan.json).

## DFT reference plan and numerical protocol

The primary DFT system is **Ca-Mg-O**, targeting **CaMg2O3**. The first early cohort is frozen as its first eight SG2 attempts, in two batches of four, before the other default new-formula cohorts. It is an early subset of the six-formula program, not the best of a later full pool. Candidate IDs will be recorded during Phase 3 generation.

Within each default formula, `select_fresh_pair` chooses at most two valid unique structures: first by the conservative score, then by the optimistic score, with diversity anchored to initial training and the first choice. This uses the same initial seed-20261022 selector throughout. Subsequent CHGNet energies do not reorder the DFT queue. Two initial structures that relax to the same phase yield one unique result; no unbudgeted replacement is implied. For an eight-formula stretch, one conservative choice per formula comes first, followed by at most four optimistic second choices ranked across formulas.

The post-CHGNet CaMg2O3 workload gate requires convergence, six composition-correct atoms, valid finite geometry, 4–40 A^3/atom, longest cell vector at most20 A and lattice-matrix condition number at most10. The starting full nosym mesh may have at most216 points; refinement may have at most1,000, subject to the remaining time budget. These are explicit, representation-sensitive workload limits, not physical instability labels. Preserve every excluded candidate and reason. The first real jobs must measure actual costs; the tiny pilot is not a production runtime prediction.

If the early cohort yields no valid unique structure, or neither of the selected maximum two passes pre-relaxation/eligibility, the fixed fallback is **Phase 1 MgO attempt000** (`structure_000.json`, eight atoms). Any required relaxation consumes one of the two explicit contingency launches, with cached identical work reused transparently. It is a known-phase control. An undesirable DFT energy cannot trigger a different candidate or fallback.

All **161 MP entries** across the primary system and its subsystems are inventoried, with **57 entries** in the Mg-O fallback subset. Shared identical reference jobs can be reused with recorded hashes; the two inventories do not imply218 distinct phases. Every source geometry is retained. Some phases are large or require spin review, so a full recalculation is not promised within six hours. This reference inventory is MP2022-scoped; WBM's additional structures are not silently included in its hull.

Independent review found that a loose primitive-cell reduction altered the distorted CaMg entry mp-1183575. The corrected preparation uses **original source cells for QE execution** and preserves primitive copies only as explicitly unverified informational derivatives. Source-to-template geometry checks prevent that reduction from silently changing the evaluated phase. All **221 input templates**, including O2 box variants, are parsed and checked; no electronic calculation is implied by this validation.

The first reference queue includes rocksalt CaO and MgO, followed by elemental Mg/Ca controls as feasible. The initial reaction test is:

```text
CaMg2O3 -> CaO + 2 MgO
delta = e_candidate - e_CaO/3 - 2 e_MgO/3    [eV/atom]
```

A resolved positive value demonstrates instability against that explicit decomposition. A resolved negative value only beats those anchors. It does not establish stability against all 161 entries. Candidate polymorphs must also be compared with one another. Missing, failed, large or spin-ambiguous competitors remain visible and block a complete-inventory claim.

The numerical protocol fixes PBE and checksum-identified SSSP1.3.0 pseudopotentials per element; initial 50/400-Ry cutoffs; reciprocal-spacing-based meshes; electronic convergence 1e-8 Ry; maximum atomic force-vector norm about 0.02057 eV/A; and both pressure and full residual stress-component tolerances of 0.5 kbar. Solid atomic/cell relaxation releases imposed symmetry. Spin, metallic-smearing and O2 vacuum checks are explicit.

Starting cutoffs and meshes require later convergence tests. Forces and stress must be checked again at the final accepted cutoff/k-point settings, with further relaxation if stationarity fails. Relevant energy shifts should reach approximately 5 meV/atom or better; comparison margins near observed sensitivity remain unresolved. No MP/VASP, WBM or CHGNet energy substitutes for compatible fresh QE energies.

Files: [reference plan](../artifacts/phase2/dft/reference_plan.json), [numerical criteria](../artifacts/phase2/dft/numerical_protocol.json), [DFT handoff](../artifacts/phase2/dft/README.md).

## Budgets and Phase 3 handoff

The cumulative structure count is **eight CrystalFormer pilot attempts plus four deterministic prototype-substitution candidates = 12**, leaving **116 of the 128 attempts**. The four original substitutions are charged once; conversions, copies, audits and reuse do not incur extra attempts. The pre-outcome accounting amendment preserves every symmetry sampling denominator. The default program is 80 CrystalFormer attempts plus four prototype candidates =84 structures, with 44 attempts of headroom; the conditional stretch is96+4=100, with28 remaining.

No additional CHGNet or QE job ran. **32 conservatively charged CHGNet launches remain.** The four-hour CHGNet cap has 14,376.137 seconds remaining; the six-hour QE cap has 21,597.896 seconds remaining. [Accounting amendment and provenance](../artifacts/phase2/budgets/accounting_amendment.json) and [cumulative ledger](../artifacts/budget_ledger.json) retain the distinction between sampled and deterministic candidates. Historical Phase 1 auditing is guarded against resetting later cumulative budgets.

The 32 future CHGNet launches are reallocated as follows:

| Use | Maximum launches |
|---|---:|
| Balanced symmetry comparison: MgO up to two, rutile up to eight | 10 |
| New-formula shortlist including DFT pre-relaxation | 12 |
| Prototype-substitution baselines | 4 |
| Same-composition references | 4 |
| Explicit retry contingency | 2 |

Unused slots are not automatically spent. The QE forecast reserves 9,000 seconds for references, 5,400 for candidates, 5,400 for numerical checks and the remainder for failures/restarts. These are planning envelopes. First production jobs must establish realistic workload-specific timings. All numerical work stops at **2026-10-22 18:24:44 Singapore time**.

Phase 3 starts by fitting/calibrating the five-member initial ensemble and saving the seed-20261022 fresh-selector snapshot. It then completes the first retrospective replay, generates the early CaMg2O3 pool, saves selection evidence and launches eligible candidate/reference jobs within the shared ledgers. New phase ledgers must be explicitly included in cumulative accounting; the historical Phase 1 finalizer does not discover future ledgers automatically.

To audit the saved Phase 2 package without fitting or running numerical jobs:

```powershell
.envs/analysis/Scripts/python.exe scripts/phase2_finalize.py
```

Preparation entry points are `phase2_features.py`, `phase2_splits.py`, `phase2_protocol.py`, `phase2_catalogs.py`, `phase2_catalogs_finalize.py`, `phase2_dft.py`, `phase2_dft_finalize.py` and `phase2_budget.py` under `scripts/`. Their artifacts retain inputs, hashes, rules and commands. Rebuilding descriptors/catalogs is not needed to resume Phase 3. Preserve all frozen manifests, candidate-attempt records and archived pre-training protocol amendments.
