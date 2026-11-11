# Crystal discovery hackathon prototype

Phases 1–5 are complete. The fixed acquisition and generation experiments, selected model relaxations and bounded oxide-reference DFT work are executed and audited. Phase 5 includes an incomplete DFT robustness check whose failed acceptance is retained explicitly.

- [Research proposal and eight-phase schedule](one_day_research_proposal.md)
- [Phase 1 runtime and data verification](reports/phase1_report.md)
- [Phase 2 frozen experimental inputs](reports/phase2_report.md)
- [Phase 3 first replay and known-MgO DFT recovery](reports/phase3_report.md)
- [Phase 4 results, figures and scientific limits](reports/phase4_report.md)
- [Phase 5 relaxations, comparisons and DFT robustness limits](reports/phase5_report.md)
- [Current readiness and Phase 6 requirements](artifacts/phase5/readiness.json)
- [Phase 5 consolidated audit](artifacts/phase5/audit.json)
- [Shared attempt and runtime budgets](artifacts/budget_ledger.json)

Across five paired splits, quality ranking found **41.2 +/- 2.17 near-stable historical records per 50 queries**, compared with **29.4 +/- 3.65** for the full policy. The full policy retrieved fewer hits in every seed while covering more chemical systems. These descriptive results from overlapping splits do not support a yield improvement for the frozen full policy. Settings were retained unchanged.

Primary exact-cell validity was **7/8 versus 0/8 for MgO SG225 versus P1**, and **6/8 versus 1/8 for TiO2 SG136 versus P1**. TiO2 yielded one unique structure in each arm. One separate supplementary MgO batch of four attempts per arm enabled a balanced pair for Phase 5; primary denominators remain fixed.

The six default formulas yielded **0/48 exact-cell eligible outputs**. Twelve outputs across all six formulas matched the requested reduced compositions and passed basic geometry/20-atom checks in larger cells; these remain diagnostic exclusions. The fresh shortlist is empty. Composition stretch is disabled under the original gates.

All **11 selected CHGNet calculations converged**: four symmetry selections, four prototype baselines and three eligible same-composition references, using ten new launches and one identical cached MgO result. Selected nontrivial-arm structures are lower in model energy than their P1 partners by **356.879 meV/atom for MgO** and **55.806 meV/atom for TiO2**. There is one structure per arm; MgO uses the supplementary pool. These descriptive comparisons do not establish an architectural causal effect. The nontrivial outputs match known rocksalt and rutile. CHGNet places the anatase reference 19.909 meV/atom below rutile.

Fresh DFT previously recovered known rocksalt MgO and completed compatible CaO reference refinement with final force/stress and numerical checks. Phase 5's deterministic MgO perturbation reached its 900-second internal limit without terminal electronic/ionic acceptance; the frozen rules allowed no continuation or probes. That robustness check remains incomplete. No primary CaMg2O3 candidate entered QE; accepted reference coverage remains 2/161, with 159 entries uncomputed. No new stable material or complete hull is claimed.

Audit saved evidence without new fits, sampling, relaxation or QE jobs:

```powershell
.envs/analysis/Scripts/python.exe scripts/phase5_finalize.py
```

The workspace retains the tested isolated environments, standalone Python runtime, frozen checkpoint, package locks and all raw/failed outputs. Restore environments with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_environments.ps1
```

The dataset retains 408 initial-only descriptors for 8,294 records, whole-chemical-system partitions, 78 reserved oxide systems, and 3,418 untouched evaluation rows per seed. Fresh selection uses the original pre-query seed-20261022 snapshot. Phase 6 integrates the fixed results and audits uncertainty, label leakage, novelty, reference completeness and budgets. Any allowed numerical follow-up must retain the frozen protocol and caps; a changed eligibility gate or candidate method requires a separately labelled supplementary experiment.

The ledger charges **96/128 structure slots**, leaving **32**, including all eight supplementary draws and four earlier un-emitted engineering charges. **19/40 CHGNet launches are charged**, leaving **21**; cumulative CHGNet walltime is **159.01 seconds**. QE has charged **2,558.92 seconds**, leaving **19,041.08 seconds** of its six-hour cap. The four-hour CHGNet cap and **22 October 2026, 18:24:44 Singapore time** numerical stop remain binding. No numerical jobs remain active.
