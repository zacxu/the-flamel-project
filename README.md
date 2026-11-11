> Phase 6 CI complete: [CI guide](CI.md) and [Phase 6 report](reports/GITHUB_PUBLICATION_PHASE6.md). Routine website/research checks preserve accepted evidence; manual workflows prepare verified packages. The live website remains hosted on InfinityFree.

# Crystal discovery hackathon prototype
Repository: [zacxu/the-flamel-project](https://github.com/zacxu/the-flamel-project) (private). [Publication verification](reports/GITHUB_PUBLICATION_PHASE5.md).

Current setup and use: [standalone installation guide](INSTALLATION.md). It separates the website, read-only saved-evidence verification and research environments. [GitHub publication progress](GITHUB_CICD_PUBLICATION_PLAN.md) is separate from the frozen research phases below.

Phases 1–6 are complete. Numerical evidence is frozen; the fixed experiments and cross-stream analysis are executed and audited. The write-up, demonstration, reproduction package and submission remain in Phases 7–8. The additional DFT robustness check and competing-phase inventory remain incomplete.

- [Research proposal and eight-phase schedule](one_day_research_proposal.md)
- [Phase 1 runtime and data verification](reports/phase1_report.md)
- [Phase 2 frozen experimental inputs](reports/phase2_report.md)
- [Phase 3 first replay and known-MgO DFT recovery](reports/phase3_report.md)
- [Phase 4 results, figures and scientific limits](reports/phase4_report.md)
- [Phase 5 relaxations, comparisons and DFT robustness limits](reports/phase5_report.md)
- [Phase 6 integrated analysis and frozen conclusions](reports/phase6_report.md)
- [Four-panel research overview](artifacts/phase6/figures/research_overview.png)
- [Current readiness and Phase 7 requirements](artifacts/phase6/readiness.json)
- [Phase 6 consolidated audit](artifacts/phase6/audit.json)
- [Final numerical freeze](artifacts/phase6/numerical_freeze.json)
- [Current official submission requirements](artifacts/phase6/current_submission_requirements.md)
- [Shared attempt and runtime budgets](artifacts/budget_ledger.json)

Across five paired splits, quality ranking found **41.2 +/- 2.17 near-stable historical records per 50 queries**, compared with **29.4 +/- 3.65** for the full policy. The full policy retrieved fewer hits in every seed while covering more chemical systems. These descriptive results from overlapping splits do not support a yield improvement for the frozen full policy. Settings were retained unchanged.

All **130 saved evaluation snapshots** and **125 policy-round label lineages** were rechecked. Disagreement tracked absolute error (full endpoint mean Spearman 0.357), but nominal-90% coverage averaged **88.88%**, varying **84.84–92.10%** by split. The full policy's conservative selections found 140/175 historical hits versus 7/75 for its optimistic selections; these roles were not randomized. No coefficient or calibration rule was retuned.

Primary exact-cell validity was **7/8 versus 0/8 for MgO SG225 versus P1**, and **6/8 versus 1/8 for TiO2 SG136 versus P1**. TiO2 yielded one unique structure in each arm. One separate supplementary MgO batch of four attempts per arm enabled a balanced pair for Phase 5; primary denominators remain fixed.

The six default formulas yielded **0/48 exact-cell eligible outputs**. Twelve outputs across all six formulas matched the requested reduced compositions and passed basic geometry/20-atom checks in larger cells; these remain diagnostic exclusions. The fresh shortlist is empty. Composition stretch is disabled under the original gates.

All six proposed compositions remain absent from the complete pinned MP2022 and WBM composition indexes. Final structural matching covers the saved 15/23 MgO and 34/44 TiO2 MP geometries; larger source cells are absent from that geometry subset. The P1 outputs remain unmatched only to this subset. Historical catalog absence does not establish global novelty or generator-pretraining OOD.

All **11 selected CHGNet calculations converged**: four symmetry selections, four prototype baselines and three eligible same-composition references, using ten new launches and one identical cached MgO result. Selected nontrivial-arm structures are lower in model energy than their P1 partners by **356.879 meV/atom for MgO** and **55.806 meV/atom for TiO2**. There is one structure per arm; MgO uses the supplementary pool. These descriptive comparisons do not establish an architectural causal effect. The nontrivial outputs match known rocksalt and rutile. CHGNet places the anatase reference 19.909 meV/atom below rutile.

Fresh DFT previously recovered known rocksalt MgO and completed compatible CaO reference refinement with final force/stress and numerical checks. Phase 5's deterministic MgO perturbation reached its 900-second internal limit without terminal electronic/ionic acceptance; the frozen rules allowed no continuation or probes. That robustness check remains incomplete. No primary CaMg2O3 candidate entered QE; accepted reference coverage remains 2/161, with 159 entries uncomputed. No new stable material or complete hull is claimed.

Verify saved source/payload checksums and the numerical freeze without loading models or rewriting historical reports:

```powershell
python -I -B scripts/github_publication/audit_saved_evidence.py
```

This verifies recorded evidence integrity; it does not repeat the historical scientific checks or recompute their metrics. The historical phase6_finalize.py writes closure reports and belongs only in a disposable reproduction copy with its required inputs.

The workspace retains historical isolated environments, runtime, checkpoint, package locks and raw/failed outputs. Follow [INSTALLATION.md](INSTALLATION.md) for clean, hash-pinned installation and the separate maintenance environment. scripts/setup_environments.ps1 is retained as historical provenance; its absolute generator reference and mixed-index installation are superseded by the publication installers.

The dataset retains 408 initial-only descriptors for 8,294 records. Excluding 476 rows in 74 observed reserved systems leaves 7,818 rows per whole-chemical-system split, including 3,418 untouched evaluation rows; the reservation list contains 78 systems. Fresh selection retains the original pre-query seed-20261022 snapshot. Phase 6 reuses only already evaluated target IDs for posthoc diagnostics, with no new fits, predictions, calibration fits, pool queries or physical/model experiments.

The ledger charges **96/128 structure slots**, with **32 unused**, including all eight supplementary draws and four earlier un-emitted engineering charges. **19/40 CHGNet launches are charged**, with **21 unused**; cumulative CHGNet walltime is **159.01 seconds**. All 19 QE jobs charged **2,558.92 seconds**, with **19,041.08 seconds unused**. The numerical evidence closed early under the unchanged caps and **22 October 2026, 18:24:44 Singapore time** stop. No required eligible unfinished job or active reservation remains. Later work packages these frozen results.
