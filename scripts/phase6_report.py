"""Render the integrated Phase 6 report from closed analysis lanes."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def descriptive(value, scale=1, digits=3):
    return f"{scale * value['mean']:.{digits}f} +/- {scale * value['sample_std']:.{digits}f}"


def main():
    u = read("artifacts/phase6/uncertainty/summary.json")
    s = read("artifacts/phase6/structures/summary.json")
    e = read("artifacts/phase6/evidence/summary.json")
    b = read("artifacts/budget_ledger.json")
    audits = {lane: read(f"artifacts/phase6/{lane}/audit.json") for lane in ("uncertainty", "structures", "evidence")}
    if not all(a["status"] == "passed" for a in audits.values()):
        raise RuntimeError("All independent analysis lanes must pass before the final report")
    endpoints = u["evaluation_endpoint_aggregates"]
    roles = {role: [row for row in u["full_policy_role_diagnostics"] if row["role"] == role]
             for role in ("conservative", "optimistic")}
    role_totals = {role: (sum(row["near_stable_hits"] for row in values), sum(row["queries"] for row in values),
                         sum(row["mean_calibrated_radius_eV_atom"] * row["queries"] for row in values) / sum(row["queries"] for row in values))
                   for role, values in roles.items()}
    cov = endpoints["full"]["interval_90_empirical_coverage"]
    initial_cov = endpoints["initial_shared"]["interval_90_empirical_coverage"]
    low_risk = u["risk_coverage_aggregates"]["full"]["0.1"]["MAE_eV_atom"]["mean"]
    lines = [
        "# Phase 6: frozen results and scientific conclusions",
        "",
        f"Completed analysis from saved evidence at {datetime.now(timezone.utc).isoformat()}. Phases 1-6 are executed and audited; the numerical experiments are closed. Phases 7-8 retain the write-up, demonstration, reproducibility package and submission.",
        "",
        "## Main scientific finding",
        "",
        "The prototype implements a symmetry-conditioned crystal-generation workflow, a calibrated ensemble selector, a retrospective active-learning benchmark, model relaxations and genuine QE validation. **The proposed improvement in discovering new DFT-stable materials is not demonstrated.** Under the frozen 50-query historical benchmark, the full uncertainty/diversity policy retrieves fewer near-stable records than quality ranking in all five splits. Nontrivial symmetry conditioning improves exact-cell validity for the two tested controls, but six new formulas produce no exact-cell eligible transformer candidates. Fresh DFT recovers a known MgO phase and validates compatible oxide anchors, with an additional perturbation check left incomplete.",
        "",
        "This is an executed research prototype with a useful negative acquisition result and identified calibration, representation and reference-coverage limits. The observed number of newly established, DFT-confirmed stable novel materials is zero. Because no eligible new-formula candidate entered QE, this does not estimate a general discovery rate or compare fresh DFT discovery efficiency across acquisition policies.",
        "",
        "![Four-panel scientific overview](../artifacts/phase6/figures/research_overview.png)",
        "",
        "[Standalone overview PDF](../artifacts/phase6/figures/research_overview.pdf). Panel (a) uses historical WBM labels and descriptive mean/sample SD; panel (b) shows held-out empirical coverage; panel (c) retains primary first-eight denominators; panel (d) depicts the actual accepted eight-atom DFT control. All five splits share one source dataset and overlap.",
        "",
        "## What was implemented",
        "",
        "| Component | Executed scope |",
        "|---|---|",
        "| Material family | Binary and ternary metal oxides; two known control compositions and six catalog-absent composition proposals |",
        "| Generator | Frozen pretrained CrystalFormer v0.6 with matched nontrivial-group/P1 conditioning; no new architecture training |",
        "| Predictor | Five outer-bootstrap ExtraTrees members, each 128 trees; 408 initial-geometry/composition descriptors |",
        "| Historical target | Signed distance to the fixed WBM historical MP hull; near-stable threshold <=0.05 eV/atom |",
        "| Uncertainty | Interval radius = q times max(member disagreement, 0.01 eV/atom), with the frozen calibration residual quantile q; empirical held-out evaluation |",
        "| Acquisition | Five unchanged policies, five chemical-system splits, five batches of ten labels per policy |",
        "| Fresh model screening | Four symmetry selections, four prototype baselines and three same-composition references; all 11 converged |",
        "| Fresh validation | Native QE/PBE oxide control/reference relaxations and finite cutoff/k-point checks; no new-formula candidate result |",
        "",
        "The research architecture is a composition of an existing symmetry-aware transformer and separate uncertainty/selection machinery. It is not a newly trained uncertainty-aware transformer architecture. The active-learning updates use the historical replay target only. Fresh QE outputs are not fed back as if they had compatible WBM hull labels.",
        "",
        "## Acquisition, uncertainty and calibration",
        "",
        "| Policy | Historical near-stable hits / 50: mean +/- sample SD | Mean precision | Mean chemical systems queried |",
        "|---|---:|---:|---:|",
    ]
    names = {"random": "Random", "quality": "Quality", "quality_diversity": "Quality + diversity",
             "uncertainty": "Uncertainty", "full": "Full"}
    for policy, name in names.items():
        row = u["policy_endpoint_aggregates"][policy]
        lines.append(f"| {name} | {descriptive(row['near_stable_hits'], digits=2)} | {100 * row['precision_at_50']['mean']:.1f}% | {row['chemical_system_coverage']['mean']:.1f} |")
    lines += [
        "",
        f"The paired full-minus-quality differences are **-9, -8, -19, -10 and -13 hits**, averaging **{descriptive(u['full_minus_quality_hits'], digits=2)}**. Quality plus diversity yields 41.6 hits on average, a small descriptive difference from quality's 41.2; this is not an independently established improvement. Full covers more chemical systems (42.2 versus 32.8) while finding fewer near-stable records. Retain this negative result without choosing a new best seed, retuning coefficients or changing the query budget.",
        "",
        "There are 1,250 historical policy-query events and 720 distinct queried IDs across all policies/splits. These are existing labels revealed retrospectively, not 1,250 fresh DFT calculations or independent new structures. Each policy starts from the same 2,400 labels within a split; the shared initial labels are separate from its 50-query budget.",
        "",
        "| Held-out endpoint | MAE (eV/atom) | RMSE (eV/atom) | Disagreement/error Spearman | Empirical nominal-90% coverage | Mean interval width (eV/atom) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for policy, name in (("initial_shared", "Initial"), ("quality", "Quality at 50"), ("full", "Full at 50")):
        v = endpoints[policy]
        lines.append(f"| {name} | {v['MAE_eV_atom']['mean']:.5f} | {v['RMSE_eV_atom']['mean']:.5f} | {v['Spearman_disagreement_absolute_error']['mean']:.4f} | {100 * v['interval_90_empirical_coverage']['mean']:.2f}% | {v['mean_interval_width_eV_atom']['mean']:.4f} |")
    lines += [
        "",
        f"Initial coverage averages **{100 * initial_cov['mean']:.3f}%**, ranging **{100 * initial_cov['min']:.3f}-{100 * initial_cov['max']:.3f}%**. Final full coverage averages **{100 * cov['mean']:.3f}%**, ranging **{100 * cov['min']:.3f}-{100 * cov['max']:.3f}%**. Some splits over-cover and others under-cover. The fixed chemical-system shift and adaptive reuse of the calibration population support an empirical reliability assessment, not arbitrary-OOD coverage guarantees. Narrower intervals and small MAE changes do not establish an improved predictor or calibrated uncertainty for generated crystals, CHGNet energies or fresh QE energies.",
        "",
        f"The ensemble disagreement has positive error-ranking association (full endpoint mean Spearman {endpoints['full']['Spearman_disagreement_absolute_error']['mean']:.4f}). On already untouched evaluation rows, retaining the least-disagreeing 10% gives mean MAE **{low_risk:.5f} eV/atom**, compared with **{endpoints['full']['MAE_eV_atom']['mean']:.5f}** over all rows. This is a posthoc selective-risk diagnostic on a different retained subset; it neither improves predictions on the complete population nor defines a newly evaluated acquisition policy.",
        "",
        "| Full-policy role | Historical hits / queries, pooled across splits | Precision | Mean calibrated radius (eV/atom) |",
        "|---|---:|---:|---:|",
    ]
    for role, (hits, queries, radius) in role_totals.items():
        lines.append(f"| {role.capitalize()} | {hits}/{queries} | {100 * hits / queries:.2f}% | {radius:.4f} |")
    lines += [
        "",
        "The optimistic allocation selects very uncertain candidates and has low immediate near-stable retrieval in this run. This helps describe where the frozen policy's queries went; the two roles are not randomized and select different candidates, so the breakdown does not isolate causality or prove a general failure of exploration. No replacement mixing ratio or scoring rule was tested after inspecting it.",
        "",
        "![Uncertainty and selective-risk diagnostics](../artifacts/phase6/uncertainty/uncertainty_reliability.png)",
        "",
        "[Reliability PDF](../artifacts/phase6/uncertainty/uncertainty_reliability.pdf), [recomputed metrics](../artifacts/phase6/uncertainty/evaluation_metrics.csv), [risk/retention rows](../artifacts/phase6/uncertainty/risk_coverage.csv), [role diagnostics](../artifacts/phase6/uncertainty/full_policy_role_diagnostics.csv).",
        "",
        "## Label-leakage and OOD audit",
        "",
        "- 8,294 eligible records have 408 initial-only descriptors. All 78 reserved chemical systems remain excluded from every predictor split; 74 are observed, comprising 476 rows. The remaining 7,818 rows form 2,000 training, 400 calibration, 2,000 hidden-pool and 3,418 untouched evaluation records per seed.",
        "- Complete chemical systems are disjoint across those four partitions within each seed. Initial normalization/diversity anchors use training rows only. Descriptors exclude target, final relaxed geometry, formation energies, band gap, identifiers and initial/final differences.",
        "- All 125 adapted policy rounds preserve initial training plus only that policy's own revealed labels. Fixed calibration rows do not become training or diversity anchors. Each decision precedes its own label reveal; evaluation labels and metrics are not returned to the learner.",
        "- The initial seed-20261022 selector precedes every replay query/evaluation read and remains byte-identical. Neither a best-performing seed nor an adapted replay model replaces it for fresh selection. Fresh CHGNet/QE outcomes do not change it.",
        f"- Phase 6 recomputes all **{u['saved_prediction_sets_recomputed']} saved evaluation prediction sets** from their original predictions. It decodes only **{u['distinct_already_evaluated_target_IDs_decoded_posthoc']:,} distinct previously evaluated target IDs** from the hash-verified historical label CSV, after every decision has finished. No new fit, inference, calibration fit, pool query or reserved target is used. This evaluator-only target re-use is explicitly recorded; it is not a claim that the label file was never opened.",
        "- Cross-seed partitions and evaluation IDs overlap. Models and revealed labels remain independent in lineage, but the five reported outcomes are dependent splits of one dataset. No independent-dataset significance test or general-purpose OOD claim is made. Predictor chemical-system withholding does not establish that CrystalFormer's pretraining excludes those compositions or elements.",
        "",
        "Evidence: [125-round lineage table](../artifacts/phase6/uncertainty/lineage_by_round.csv), [cross-seed overlaps](../artifacts/phase6/uncertainty/cross_seed_overlap.csv), [posthoc target-access record](../artifacts/phase6/uncertainty/posthoc_target_access.json), [uncertainty summary and scope](../artifacts/phase6/uncertainty/summary.json).",
        "",
        "## Symmetry, composition and structural novelty",
        "",
        "| Primary control | Nontrivial exact-cell valid / 8 | P1 exact-cell valid / 8 | Nontrivial / P1 valid unique |",
        "|---|---:|---:|---:|",
        "| MgO | 7 | 0 | 1 / 0 |",
        "| TiO2 | 6 | 1 | 1 / 1 |",
        "",
        "Both arms use the same pretrained symmetry-aware architecture. This is a matched conditioning comparison, not a training ablation removing symmetry constraints. Nontrivial conditioning improves raw exact-cell validity for these two controls, while unique yield does not improve for TiO2. Reduced-composition diagnostics and the actual executed-cell requirement remain separate from primary success.",
        "",
        "The one-per-arm relaxed pairs have CHGNet P1-minus-nontrivial differences **+356.879234 meV/atom MgO** and **+55.806478 meV/atom TiO2**. MgO uses the separately labelled supplementary pool; TiO2 uses its primary pools. The nontrivial outputs match known rocksalt and rutile. These pairs describe two selected outcomes, not an energy distribution or architecture-causal stability advantage. CHGNet ranks the anatase reference **19.908905 meV/atom below rutile**; the generated rutile-conditioned structure is not the lowest even in the limited TiO2 model reference set.",
        "",
        "A broader saved-geometry check compares final structures with **15/23 MgO** and **34/44 TiO2** entries in the pinned MP composition snapshot. The saved geometry extraction used a 30-source-site cap; 18 larger-source-cell entries have no geometry in this checked subset, and their IDs remain listed. Both relaxed P1 outputs are unmatched to this saved subset only. Absence of a match does not establish global novelty.",
        "",
        "| Proposed formula | Primary exact-cell valid / draws | Excluded larger-cell, reduced-formula/geometry diagnostics |",
        "|---|---:|---:|",
    ]
    for row in s["generation"]["new_formula_cohorts"]:
        lines.append(f"| {row['formula']} | {row['exact_valid']}/{row['draws']} | {row['excluded_larger_cell_diagnostics']} |")
    lines += [
        "",
        "All six compositions remain absent from the complete pinned composition indexes: **154,718 MP records** and **256,963 WBM records**. This means new-to-those-historical-snapshots only; global composition novelty and absence from generator pretraining remain unproven. The twelve larger-cell diagnostics span all six formulas but do not pass the original exact evaluated-cell gate. No primitive reduction, admission, reserve substitution or extra draw changes the 0/48 result.",
        "",
        "The four original prototype baselines (SnSrO2, BaSnO2, CaMg2O3, Mg2SrO3) have valid 4/4/6/6-atom cells and converged CHGNet results. They remain a distinct method baseline, not transformer outputs or substitutes in its empty DFT queue. There is only one relaxed prototype per formula; cross-composition raw energies and convergence do not establish formation energy, polymorph ranking, stability or novelty. Brookite's 24-atom model-reference input remains excluded, without using its spare slot for a replacement.",
        "",
        "![Representative saved structures and evidence levels](../artifacts/phase6/structures/representative_structures.png)",
        "",
        "[Structure PDF](../artifacts/phase6/structures/representative_structures.pdf), [figure geometry provenance](../artifacts/phase6/structures/figure_provenance.json), [all generation draws](../artifacts/phase6/structures/generation_draws.csv), [composition novelty checks](../artifacts/phase6/structures/composition_novelty.csv), [all relaxed structures and catalog matches](../artifacts/phase6/structures/relaxed_structures.csv).",
        "",
        "## Fresh DFT evidence and reference completeness",
        "",
        "All 19 QE jobs, including pilots, failed stationarity, continuations, sensitivity probes and the incomplete perturbation, were independently reparsed and reconciled. Three distinct relaxed geometries have accepted final-setting force/full-stress and finite cutoff/k-point checks: the generated known MgO control, its source MgO reference and the source CaO reference.",
        "",
        "| Accepted geometry | Force max (eV/angstrom) | Full-stress max (kbar) | Cutoff shift (meV/atom) | K-point shift (meV/atom) |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in e["fresh_QE_relaxed_geometries_with_final_finite_checks"]:
        lines.append(f"| {row['accepted_job_id']} | {row['force_eV_A']:.6g} | {row['full_stress_kbar']:.6f} | {1000 * row['cutoff_shift_eV_atom']:.6f} | {1000 * row['kpoint_shift_eV_atom']:.6f} |")
    lines += [
        "",
        "All accepted geometries use the frozen compatible PBE pseudopotentials, 90/720 Ry, 0.35 inverse-angstrom k spacing, released atomic/cell coordinates and no imposed symmetry. Actual grids differ with cell geometry. Their stationarity and same-final-geometry single-variable sensitivities pass the stated criteria. These finite changes quantify measured numerical sensitivity; they do not provide a rigorous total DFT error bound.",
        "",
        f"The accepted eight-atom generated MgO matches the independently relaxed two-atom source reference, both SG225. Their difference is **{1000 * e['known_MgO_candidate_minus_reference_eV_atom']:.6f} meV/atom**, far below the recorded numerical sensitivity and finite 10-meV/atom interpretation tolerance. This is numerically indistinguishable known-phase recovery, with no resolved energy advantage.",
        "",
        "The Phase 5 symmetry-breaking probe reached its 900-second internal time limit in SCF call nine, after eight converged SCF calls and seven BFGS steps. Exit code zero and `JOB DONE` do not provide accepted terminal electronic/ionic convergence or final force/stress evidence. The frozen rule therefore permits no continuation or sensitivity probes. The probe remains incomplete; it neither disproves the prior accepted unperturbed geometry nor proves instability, a local minimum or phonon stability.",
        "",
        "| Reference inventory | Frozen entries | Accepted source entries | Missing |",
        "|---|---:|---:|---:|",
    ]
    for system, row in e["reference_coverage"].items():
        lines.append(f"| {system} | {row['frozen_entries']} | {row['accepted_fresh_compatible_QE']} | {row['missing']} |")
    lines += [
        "",
        "The source references are two distinct IDs, not three: the generated MgO control is not another reference entry. Missing inventories include elemental endpoints, oxygen and spin-review cases. The 215 missing CSV rows are 159 primary plus 56 fallback inventory memberships, with overlap; they are not 215 unique phases. No missing phase is silently dropped from the retained inventory.",
        "",
        "Compatible CaO+2MgO anchors have weighted energy -607.632128522 eV/atom, but no primary CaMg2O3 candidate energy exists to subtract. No reaction energy or full reference-only/combined hull is computed. CHGNet, MP/VASP and QE energies remain separate. Known-phase recovery, static numerical convergence and catalog absence cannot establish a new stable material, finite-temperature behavior, dynamical stability or synthesis feasibility.",
        "",
        "Evidence: [fresh DFT evidence table](../artifacts/phase6/evidence/fresh_DFT_evidence_table.csv), [full reference inventory](../artifacts/phase6/evidence/reference_inventory_completeness.csv), [missing reference memberships](../artifacts/phase6/evidence/missing_reference_inventory.csv), [claim matrix](../artifacts/phase6/evidence/claim_matrix.csv).",
        "",
        "## Why numerical work closes now",
        "",
        "No required eligible unfinished job remains in the frozen executable queues. Accepted oxide geometries have their final checks; no new-formula transformer candidate is eligible; the perturbation's terminal-SCF failure triggers its stop rule. The larger reference inventory retains uncomputed metal/O2/spin cases outside the executed oxide queues, with no promised complete-hull outcome. Opening another queue, changing eligibility or replacing the candidate method after outcomes would be a separate study. Remaining compute capacity is a ceiling, not a reason to invent extra work or revise a failed acceptance criterion.",
        "",
        "The [numerical closure decision](../artifacts/phase6/evidence/numerical_stop_decision.json), [final numerical freeze](../artifacts/phase6/numerical_freeze.json) and [hash manifest](../artifacts/phase6/manifest.json) bind the existing evidence. Numerical experiments finish early, before the unchanged **22 October 2026, 18:24:44 Singapore time** stop. Read-only analysis and packaging may continue. The canonical job ledger correctly remains at Phase 5, the last phase with actual experiment dispatch; Phase 6 creates no fake job or ledger rewrite.",
        "",
        "| Resource | Charged | Unused | Original ceiling |",
        "|---|---:|---:|---:|",
        f"| Structure slots | {b['generation']['charged_attempts']} | {b['generation']['remaining_attempts']} | 128 |",
        f"| CHGNet launch slots | {b['chgnet']['charged_attempts']} | {b['chgnet']['remaining_attempts']} | 40 |",
        f"| CHGNet whole-job seconds | {b['chgnet']['charged_wall_seconds']:.6f} | {b['chgnet']['remaining_seconds']:.6f} | 14,400 |",
        f"| QE whole-job seconds | {b['qe']['charged_wall_seconds']:.6f} | {b['qe']['remaining_seconds']:.6f} | 21,600 |",
        "",
        "The 96 structure charges include 88 actual CrystalFormer draws, four original prototypes and four un-emitted engineering charges. The 19 CHGNet charges include 15 actual model relaxations and four pre-model rejections; one selected cached result is not charged twice. All 19 QE jobs consume actual whole subprocess walltime. Lane times may overlap and are not summed into elapsed project time. All active reservations and locks are closed; Phase 6 introduces no new fit, inference, generation, relaxation or QE experiment.",
        "",
        "## Audit, reproducibility and presentation handoff",
        "",
        f"Independent analysis lanes passed **{audits['uncertainty']['checks_total']:,} uncertainty/lineage checks**, **{audits['structures']['checks_total']:,} structure/novelty checks** and **{audits['evidence']['checks_total']:,} DFT/budget checks**. The [consolidated audit](../artifacts/phase6/audit.json) additionally checks cross-stream agreement, latest immutable Phase 1-5 manifests, archived prior root documents, current links and unchanged ledgers. The [readiness record](../artifacts/phase6/readiness.json) records the Phase 7 handoff. Checks are integrity assertions, not independent statistical evidence.",
        "",
        "Audit saved evidence without opening label values, refitting, inference or experiment dispatch:",
        "",
        "```powershell",
        ".envs/analysis/Scripts/python.exe scripts/phase6_finalize.py",
        "```",
        "",
        "The separate posthoc uncertainty script explicitly reuses already evaluated targets; its target-access log and source hashes document that scope. Source scripts, all result CSVs, raw structures and earlier failed outputs remain available. The earlier reports and phase closure files are preserved; Phase 6 archives their root README/proposal versions before updating current documentation.",
        "",
        "The four presentation assets are the [five-seed acquisition figure](../artifacts/phase4/replay_figures/five_seed_acquisition.png), [uncertainty diagnostics](../artifacts/phase6/uncertainty/uncertainty_reliability.png), [primary generation figure](../artifacts/phase4/figures/primary_generation.png) with [model-energy comparison](../artifacts/phase5/figures/within_composition_energies.png), and [representative structures](../artifacts/phase6/structures/representative_structures.png) with the fresh DFT evidence table. The overview provides a compact four-panel starting point for the one-page account.",
        "",
        "The [official submission requirements checked during Phase 6](../artifacts/phase6/current_submission_requirements.md) supersede the earlier stale-page warning. Prepare the Moment team entry, video/public post, one-page write-up and repository link in Phases 7-8; the worldwide deadline remains 23 October 2026, 08:00 Singapore time. No account, team, public publication or submission action was performed in this phase.",
        "",
        "## Frozen conclusions for the write-up",
        "",
        "1. The frozen full uncertainty/diversity policy underperformed quality ranking in immediate historical near-stable retrieval at 50 queries in every tested split, while covering more chemical systems.",
        "2. Uncertainty disagreement ranked error to a useful degree, but empirical interval coverage varied across chemical-system splits and did not guarantee calibration for fresh generated structures.",
        "3. Nontrivial space-group conditioning improved exact-cell validity on two known controls under the same architecture. One selected relaxed energy pair per composition does not establish a general energy distribution, architecture-causal benefit or DFT symmetry advantage.",
        "4. Six proposals are absent from two pinned historical catalogs, but exact-cell eligibility rejected all 48 transformer draws. Twelve larger-cell matches expose a representation-sensitive bottleneck and remain excluded. Four prototype baselines converged at the model level only.",
        "5. Genuine QE validation recovered known MgO and compatible oxide anchors with finite numerical checks. The perturbation and competing-phase inventory remain incomplete; no new stable material or complete hull is established.",
        "",
        "Future experiments may predeclare a broader executed-cell policy, test improved exploration scores on independent chemistry, or allocate a fresh compatible DFT reference plan to a valid new candidate. These are follow-up hypotheses, not retroactive modifications to this completed study.",
        "",
    ]
    destination = ROOT / "reports/phase6_report.md"
    destination.write_text("\n".join(lines), encoding="utf-8")
    print(destination.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
