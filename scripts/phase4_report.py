"""Build the Phase 4 account from completed, saved evidence only."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|"*len(headers)] +
                     ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def main():
    aggregate = load("artifacts/phase4/replay/aggregate_summary.json")
    primary = load("artifacts/phase4/generation/summary.json")
    supplementary = load("artifacts/phase4/generation/supplementary_mgo/summary.json")
    qe = load("artifacts/phase4/qe/summary.json")
    anchors = load("artifacts/phase4/qe/oxide_reaction_anchors.json")
    handoff = load("artifacts/phase4/selection/symmetry_relaxation_plan.json")
    budget = load("artifacts/budget_ledger.json")
    gate = load("artifacts/phase4/gates/composition_stretch.json")
    assert aggregate["status"] == "completed" and not any(budget[k]["active_reservations"] for k in ["generation", "chgnet", "qe"])
    with (ROOT / "artifacts/phase4/replay/per_seed_policy_metrics.csv").open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    policies = ["random", "quality", "quality_diversity", "uncertainty", "full"]
    names = {"random": "Random", "quality": "Quality", "quality_diversity": "Quality + diversity",
             "uncertainty": "Uncertainty", "full": "Full"}
    seed_rows = []
    for seed in aggregate["seeds"]:
        by_policy = {r["policy"]: r for r in records if int(r["seed"]) == seed}
        values = [int(by_policy[p]["near_stable_hits"]) for p in policies]
        seed_rows.append([seed, *values, values[-1]-values[1]])
    endpoints = aggregate["policy_endpoint_aggregates"]
    endpoint_rows = []
    for policy in policies:
        d = endpoints[policy]
        hits = d["near_stable_hits"]
        endpoint_rows.append([names[policy], f'{hits["mean"]:.1f} +/- {hits["sample_std"]:.2f}',
                              f'{100*d["precision_at_50"]["mean"]:.1f}%',
                              f'{d["reference_hull_hits"]["mean"]:.1f}',
                              f'{d["chemical_system_coverage_at_50"]["mean"]:.1f}'])
    delta = aggregate["full_minus_quality_near_stable_hits"]
    control_rows = [[r["formula"], r["spacegroup"], f'{r["valid_count"]}/8', r["valid_unique_count"],
                     f'{r["reduced_formula_geometry_valid_within_atom_cap_diagnostic_only"]}/8'] for r in primary["controls"]]
    formula_rows = [[r["formula"], f'{r["valid_count"]}/8',
                     f'{r["reduced_formula_geometry_valid_within_atom_cap_diagnostic_only"]}/8'] for r in primary["new_compositions"]]
    eval_rows = []
    for policy in ["initial_shared", "quality", "full"]:
        metrics = aggregate["evaluation_endpoint_aggregates"][policy]
        eval_rows.append(["Initial shared" if policy == "initial_shared" else names[policy],
                          f'{metrics["MAE_eV_atom"]["mean"]:.5f}', f'{metrics["RMSE_eV_atom"]["mean"]:.5f}',
                          f'{100*metrics["interval_90_empirical_coverage"]["mean"]:.2f}%',
                          f'{metrics["mean_interval_width_eV_atom"]["mean"]:.4f}'])
    cao = load(next(r["path"] for r in qe["jobs"] if r["job_id"] == qe["accepted_CaO_job_id"]))["result"]
    shifts = {r["kind"]: r["absolute_energy_shift_eV_per_atom"]*1000 for r in qe["final_geometry_sensitivity_checks"]}
    text = f'''# Phase 4 execution report

**Phase 4 is complete: all five paired replay seeds, the matched primary symmetry cohorts, all six default formula cohorts, one bounded supplementary MgO pair and compatible CaO reference refinement are executed.** The full acquisition policy found fewer near-stable records than quality ranking in {delta["losses"]} of five seeds. No new-formula output passed the frozen exact-cell gate; the resulting fresh shortlist is empty. All failures and negative findings remain in the evidence.

## Five-seed acquisition experiment

Each seed uses 2,000 initial training labels, 400 calibration labels and a hidden 2,000-row pool, with complete chemical systems kept disjoint within that seed. Every policy receives the same starting resources and five batches of ten additional labels. The untouched evaluation cohort has 3,418 rows per seed. The five fixed ExtraTrees bootstrap members, 408 initial-only descriptors, uncertainty floor, residual calibration, diversity normalization, acquisition coefficients and tie-breaking remain unchanged from the [frozen Phase 2 protocol](../config/phase2_protocol.json).

Phase 4 added **1,000 retrospective query events** across the four remaining seeds. Together with the unchanged Phase 3 run, there are **1,250 events**, covering {aggregate["distinct_pool_ids_queried_across_all_seeds_and_policies"]} distinct pool IDs. Events can reuse historical records across policies or splits; they are not fresh DFT calculations. The 2,400 initial labels per seed are a separate shared resource.

Near-stable hits at 50 queries, using signed historical WBM hull distance <=0.05 eV/atom:

{table(["Seed", "Random", "Quality", "Quality + diversity", "Uncertainty", "Full", "Full minus quality"], seed_rows)}

{table(["Policy", "Hits: mean +/- sample SD", "Mean precision", "Mean on/below reference hull", "Mean chemical systems queried"], endpoint_rows)}

The paired full-minus-quality difference averages **{delta["mean"]:.1f} hits**, with sample SD **{delta["sample_std"]:.2f}**; wins/ties/losses are **{delta["wins"]}/{delta["ties"]}/{delta["losses"]}**. This supports a negative result for the frozen full policy under this 50-query benchmark. It does not show that uncertainty-aware acquisition generally fails. These are five overlapping splits of one dataset; means and sample SD are descriptive, without a significance or independent-dataset claim. No seed, policy, coefficient or stopping rule was changed to reverse the outcome.

![Acquisition curves across the five paired seeds](../artifacts/phase4/replay_figures/five_seed_acquisition.png)

All decisions were committed before their selected labels were revealed. Each policy refit on only its initial training set plus its own queries, using the fixed calibration set. Evaluation labels entered a separate evaluator after all five policies for that seed finished; metrics never returned to acquisition. Other seeds' partitions can overlap, but models and revealed labels are not shared between seeds. The original seed-20261022 initial snapshot remains the sole fresh-candidate selector, unchanged before and after these runs.

Mean untouched-evaluation metrics across seeds (initial model or the policy endpoint at 50 queries):

{table(["Model", "MAE, eV/atom", "RMSE, eV/atom", "Empirical coverage (nominal 90%)", "Mean interval width, eV/atom"], eval_rows)}

Intervals are empirically calibrated under chemical-system shift, with no arbitrary-OOD coverage guarantee. The [aggregate metrics](../artifacts/phase4/replay/aggregate_summary.json) and [all endpoint metrics](../artifacts/phase4/replay/per_seed_evaluation_metrics.csv) retain every policy's errors, uncertainty/error association, coverage and widths. Artifact audits reproduced all 125 batch decisions, 625 adapted plus 25 initial bootstrap plans, 130 calibration values and 130 model/evaluation snapshots. Phase 4 added 104 ensemble snapshots. New-seed fitting/calibration used **{aggregate["phase4_new_fit_calibration_seconds"]:.1f} seconds**; measured replay invocations used **{aggregate["phase4_new_sum_measured_invocation_elapsed_seconds"]:.1f} seconds**. These are wall durations excluding imports/audits, not new DFT cost.

## Matched primary symmetry sampling

The four primary arms each retain their first eight attempts. Phase 1 MgO SG225 is reused with source/hash proof, including its failed attempt; the other three arms ran in Phase 4. Checkpoint, temperature, top-p, eligibility, exact evaluated cells and deduplication are frozen. Both arms use the same symmetry-aware architecture, so this tests the sampling condition rather than an architecture trained without symmetry.

{table(["Evaluated formula", "Requested SG", "Exact-cell valid", "Valid unique", "Reduced composition + geometry diagnostic"], control_rows)}

Nontrivial-group conditioning improved raw exact-cell validity for these controls. Unique yield was not uniformly higher: TiO2 yielded one unique structure in each arm. The reduced-composition diagnostic also shows that the evaluated-cell requirement contributes to the contrast. It never replaces the primary exact-cell metric. Eight draws per arm and two known compositions do not establish broad stability, novelty or generator-architecture benefits.

![Primary symmetry and composition generation results](../artifacts/phase4/figures/primary_generation.png)

One predeclared supplementary MgO batch added four draws per arm using unused batch index 2, before random relaxation selection. SG225 yielded **4/4 valid**, P1 **1/4**; each combined primary-plus-supplementary pool has one unique structure. The additional attempts remain separate from the primary denominator. This enables one supplemented MgO pair for Phase 5, while TiO2 supports one pair from its primary pools. Neither comparison estimates an energy distribution from several independent structures. No further top-ups were authorized or run.

The [frozen random relaxation plan](../artifacts/phase4/selection/symmetry_relaxation_plan.json) selects equal quotas without surrogate or observed-energy ranking. Four experimental selections are recorded. The MgO SG225 representative matches the prior CHGNet control source and may reuse that calculation only after Phase 5 verifies identical settings/checkpoint; it is not charged a second time as compute. No new symmetry relaxation ran in Phase 4.

## Six proposed compositions and exact-cell bottleneck

The full default pool contains **48 attempts across six formulas**, including the unchanged Phase 3 CaMg2O3 cohort. Composition absence remains scoped to the pinned MP2022 and full WBM catalogs; global novelty and generator-training absence are unproven.

{table(["Formula", "Primary exact-cell valid", "Reduced composition + basic geometry + <=20 atoms: diagnostic only"], formula_rows)}

There are **zero primary-eligible structures**, but **12 diagnostic outputs across all six formulas** match their reduced compositions and pass the basic geometry/20-atom checks in larger cells. These are generated proposals, not stable materials. The exact small evaluated-cell requirement is a practical bottleneck in this run; zero eligible yield does not establish a general inability to generate these compositions or their physical instability. The pinned [sampling code](../vendor/CrystalFormer/crystalformer/src/sample.py) uses composition conditioning and an element-identity mask; our exact expanded-count gate is an additional post-generation filter. The [fresh shortlist](../artifacts/phase4/selection/fresh_shortlist.json) preserves six empty formula entries and the original model hash. No posthoc cell-count admission, reserve substitution, CHGNet energy ranking or replacement draw was used.

The optional composition stretch is **disabled**. {gate["reason"]} The [gate record](../artifacts/phase4/gates/composition_stretch.json) retains the budget and clock checks. A broader evaluated-cell follow-up would need its own protocol and must remain separate from these completed primary outcomes.

## Fresh DFT reference work

Phase 4 ran **three genuine QE jobs**, totaling **{qe["phase4_QE_wall_seconds"]:.2f} seconds (7.52 minutes)**: CaO variable-cell relaxation and two final-geometry sensitivity probes. Accepted CaO uses PBE, the frozen pseudopotentials, 90/720 Ry and 0.35 inverse-angstrom spacing (7x7x7 mesh), four threads and no imposed symmetry. Final maximum force is **{cao["max_force_vector_norm_eV_per_angstrom"]:.3g} eV/angstrom**, full-stress maximum **{cao["max_absolute_residual_stress_component_kbar"]:.5f} kbar**, with converged final electronic and ionic flags. The cutoff and k-point shifts are **{shifts["cutoff"]:.4f}** and **{shifts["kpoint"]:.4f} meV/atom**, both below 5. The 75 Ry probe's nonstationary stress remains identified; it is a sensitivity calculation, while the accepted 90 Ry geometry passes all stationarity checks.

The [compatible oxide anchors](../artifacts/phase4/qe/oxide_reaction_anchors.json) combine accepted CaO and the reused accepted Phase 3 MgO reference. Their shared functional, O pseudopotential, cutoffs and spacing are verified. The CaO + 2MgO weighted product energy is **{anchors["weighted_product_energy_eV_per_atom"]:.9f} eV/atom**. No eligible primary CaMg2O3 candidate exists to subtract, so no candidate reaction energy is reported. Of 161 frozen reference IDs, **159 remain uncomputed**. These two anchors do not establish a complete hull or a new stable material. Metal, O2 and spin-ambiguous references remain outside this completed queue.

## Budgets, audit and Phase 5 handoff

Phase 4 made **72 actual new CrystalFormer draws**: 64 primary plus eight supplementary. Across all phases there are 88 actual model draws, four prepared prototype candidates and four un-emitted engineering charges, totaling **96/128 charged structure slots**, with **32 remaining**. The four Phase 3 engineering charges remain intact; Phase 4 introduced no generation retry overhead. CHGNet remains **9/40 charged launches**, leaving **31**, with {budget["chgnet"]["remaining_seconds"]:.2f} seconds remaining. Cumulative QE is **{budget["qe"]["charged_wall_seconds"]:.2f} seconds**, leaving **{budget["qe"]["remaining_seconds"]:.2f} seconds**. Per-lane times can overlap and should not be summed into elapsed project time. All caps and the **22 October 2026, 18:24:44 Singapore time** numerical stop remain binding. No numerical job remains active.

Primary generation passed 1,629 artifact checks; the supplementary audit passed 141 and the QE audit 83. The consolidated [Phase 4 audit](../artifacts/phase4/audit.json), [manifest](../artifacts/phase4/manifest.json) and [readiness record](../artifacts/phase4/readiness.json) bind the lane evidence and final handoff. Auditing did not fit models, draw candidates, relax structures or run QE. A CIF roundtrip audit disabled parser fractional-coordinate idealization to compare stored coordinates accurately; original CIF/JSON/raw outputs and eligibility were unchanged.

Audit saved results without launching further numerical work:

```powershell
.envs/analysis/Scripts/python.exe scripts/phase4_finalize.py
```

Phase 5 can execute the frozen balanced symmetry selections, validate the four already-prepared prototype baselines and the predeclared reference subset, and continue only supported, bounded DFT work. The primary new-formula shortlist contributes zero candidates. Keep supplemented MgO and primary TiO2 energy comparisons distinct, preserve failures and avoid comparing QE with WBM/CHGNet energy conventions. No newly stable material, complete hull or symmetry-related energy advantage has been established.
'''
    path = ROOT / "reports/phase4_report.md"
    path.write_text(text, encoding="utf-8")
    print(json.dumps({"report": str(path), "words": len(text.split())}))


if __name__ == "__main__":
    main()
