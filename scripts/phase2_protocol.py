"""Freeze replay/acquisition/numerical allocations; verify synthetic decisions only."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import numpy as np
import research_acquisition as acquisition


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_checks():
    checks = []
    # Known residual ratios1..400 imply rank361 and q361 at 90% calibration.
    calibration = acquisition.calibrate_uncertainty(np.arange(1, 401)*.01, np.zeros(400), np.full(400, .01))
    assert calibration["rank_1_based"] == 361 and abs(calibration["q"]-361) < 1e-10
    checks.append("Finite-sample calibration rank and known residual quantile")
    assert np.allclose(acquisition.uncertainty_radius(np.array([0, .02]), {"q": 2}), [.02, .04])
    checks.append("Uncertainty floor applies before residual scaling")
    train = np.vstack([np.zeros(408), np.ones(408)])
    normalization = acquisition.fit_diversity_normalization(train)
    transformed = acquisition.transform_diversity(train, normalization)
    distances = acquisition.distances_to_labeled(transformed, transformed[:1])
    assert np.allclose(distances, [0, 1])
    checks.append("Diversity is zero for identical features and capped at one")
    assert np.allclose(normalization["center"], .5) and np.allclose(normalization["scale"], .5)
    checks.append("Normalizer derives solely from supplied initial-training features")
    ids = np.array([f"synthetic-{i:02d}" for i in range(20)])
    mean = np.full(20, .1)
    radius = np.zeros(20)
    radius[-1] = .2
    features = np.zeros((20, 150))
    distance = np.zeros(20)
    chosen, evidence = acquisition.select_batch("full", ids, mean, radius, features, distance, np.random.default_rng(7))
    assert [row["role"] for row in evidence] == ["conservative"]*7 + ["optimistic"]*3
    assert 19 not in chosen[:7] and chosen[7] == 19
    checks.append("Full policy avoids high uncertainty conservatively and explores it optimistically, with seven/three quotas")
    for policy in acquisition.POLICIES:
        a, trace_a = acquisition.select_batch(policy, ids, mean, radius, features, distance, np.random.default_rng(9))
        b, trace_b = acquisition.select_batch(policy, ids, mean, radius, features, distance, np.random.default_rng(9))
        assert len(a) == len(set(a.tolist())) == 10 and np.array_equal(a, b) and trace_a == trace_b
    checks.append("All five policies choose ten unique rows deterministically for paired inputs/seeds")
    _, tie_trace = acquisition.select_batch("quality", ids[::-1], mean, radius, features, distance, np.random.default_rng(7))
    assert [x["material_id"] for x in tie_trace] == list(ids[:10])
    checks.append("Equal-score tie breaks use material ID independent of candidate input order")
    try:
        acquisition.select_batch("quality", ids, mean, -np.ones(20), features, distance, np.random.default_rng(1))
    except ValueError:
        checks.append("Invalid negative uncertainty is rejected")
    else:
        raise AssertionError("Negative uncertainty was accepted")
    # Redundant near-duplicate features lose the diversity bonus after the first choice.
    features[10:] = 1
    _, diversity_trace = acquisition.select_batch("quality_diversity", ids, mean, np.zeros(20), features,
                                                   np.ones(20), np.random.default_rng(1))
    assert diversity_trace[0]["material_id"] == ids[0] and diversity_trace[1]["material_id"] == ids[10]
    checks.append("Greedy within-batch diversity updates favor a different feature cluster")
    fresh, trace = acquisition.select_fresh_pair(ids, mean, radius, features, np.zeros(20))
    assert len(set(fresh.tolist())) == 2 and fresh[1] == 19 and [r["role"] for r in trace] == ["conservative", "optimistic"]
    checks.append("Fresh within-formula pair uses conservative then optimistic selection without energies")
    empty, _ = acquisition.select_fresh_pair([], [], [], np.empty((0, 150)), [])
    single, trace = acquisition.select_fresh_pair(["one"], [.1], [.2], np.zeros((1, 150)), [0])
    assert len(empty) == 0 and list(single) == [0] and trace[0]["role"] == "conservative"
    checks.append("Zero/one eligible fresh candidates produce zero/one selections without fabricated alternatives")
    return {"status": "passed", "checks": checks, "real_labels_read": 0,
            "model_fits": 0, "real_query_reveals": 0, "new_model_or_DFT_jobs": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amend-before-training", metavar="REASON")
    args = parser.parse_args()
    out = ROOT / "artifacts/phase2/protocol"
    out.mkdir(parents=True, exist_ok=True)
    config_dir = ROOT / "config"
    config_dir.mkdir(exist_ok=True)
    checks = synthetic_checks()
    record = {
        "schema_version": 1, "frozen_utc": datetime.now(timezone.utc).isoformat(), "status": "frozen_before_model_fit_and_replay",
        "seeds": [20261022, 20261023, 20261024, 20261025, 20261026], "fresh_selector_seed": 20261022,
        "fresh_selector": "Save the first seed's initial fitted/calibrated ensemble, normalization and checkpoint before ANY pool-label reveal; never choose best seed or adapted replay snapshot.",
        "fresh_shortlist": {
            "implementation": "research_acquisition.select_fresh_pair; no CHGNet/DFT energy input",
            "default": "Up to2validuniqueinitialstructuresperselectedformula; maximum12prerelaxationattempts, including earlyDFTcohort",
            "within_formula_order": ["conservative: (0.05-mu-u)/0.05+0.5D", "optimistic: (0.05-mu+u)/0.05+0.5D"],
            "diversity_anchors": "Frozen initialtraining plus alreadychosen sameformula candidate; formulas ranked independently",
            "tie_break": "lexicographic candidateID; originalorder saved before relaxation",
            "early_DFT_cohort": "First8CaMg2O3SG2attempts,2batchesof4, before the other default new-formula cohorts; report earlycohort provenance, not bestoflaterfullpool",
            "early_DFT_selection": "Select atmost2fromthatcohort with frozenpairfunction; pre-relax eachonce inselectororder; firstDFTjob retains initialselectororder among eligibleconverged results",
            "DFT_pre_relaxation_eligibility": {
                "exact_formula_and_atom_count": "CaMg2O3,6atoms", "CHGNet_must_converge": True,
                "volume_per_atom_A3_inclusive": [4, 40], "max_cell_vector_length_A": 20,
                "max_lattice_matrix_condition_number": 10,
                "max_initial_full_kmesh_points_nosym": 216,
                "max_refinement_full_kmesh_points_nosym": 1000,
                "kmesh_budget_rationale": "Boundedengineeringgate: Phase1full4x4x4mesh=64points(8irreducible); initialcap216allowsatmost3.375timesfullpilotmesh, refinedcap1000onlywithremainingjobtimebudget; nosym and sixatomcostmuststillbemeasured",
                "geometry_checks": "Same stoichiometry, finite validcell, minimumperiodicseparation>=0.75A",
                "classification": "Representation-sensitive workloadfilters onactualexecutedcell, not physicalphaseclassification or evidence of thermodynamicinstability; retainallrejectionsandreason"},
            "no_outcome_reordering": "Do not reprioritize using CHGNetenergies; if two selected structures collapse intoonephase, reportoneunique rather than chase replacements",
            "known_MgO_DFT_fallback": {
                "trigger": "Onlyif firstCaMg2O3cohorthasnovaliduniquecandidate or noneofthechosenmaximum2isconvergedandeligible; documentoriginalfailures; never switch becausecandidateDFTenergyisundesirable",
                "candidate_id": "phase1_mgo_attempt_000", "source_attempt_id": 0,
                "source_structure": "artifacts/phase1/generator/structure_000.json",
                "source_structure_sha256": digest(ROOT / "artifacts/phase1/generator/structure_000.json"),
                "evaluated_formula": "Mg4O4", "evaluated_atoms": 8,
                "CHGNet_allocation": "Oneoftwoexplicitcontingencylaunches; ifanidenticalcompletedrelaxationiscached,recordreusewithoutdoublecharging; donotconsumeaninvisible13thshortlistslot",
                "evidence_scope": "Known-phase recovery/controlcalculation, not novel discovery"},
            "stretch": "For8formulas, firstoneconservativecandidateeach; up4secondcandidates rankedbytheir optimisticpairscore withcandidateIDties; total12maximum",
            "reserves": "Admitinrecordedreserveorder onlywithinremainingbudgets; retain originaldefaultfailures as distinctcohorts. No outcome-dependentmanualreserveordering",
            "calibration_and_model_snapshot": "Samefixedinitialseed20261022snapshotforallfreshcohorts; no refit from replay or freshQEoutcomes"},
        "target": {"name": "e_above_hull_mp2020_corrected_ppd_mp", "units": "eV/atom", "signed_negative_preserved": True,
                   "near_stable_inclusive": .05, "on_or_below_historical_reference_hull_inclusive": 0.0,
                   "fresh_QE_labels_compatible_with_target": False},
        "population": {"source": "artifacts/phase1/data/eligible_population.csv", "total_rows": 8294,
                       "initial_training": 2000, "calibration": 400, "hidden_pool": 2000,
                       "fixed_untouched_evaluation": 3418, "evaluation_partition_key_in_split_files": "unused",
                       "group": "sorted complete chemical system", "whole_group_assignment": True,
                       "reserved_systems": "artifacts/phase2/splits/reserved_systems.json"},
        "features": {"module": "research_features.py", "function": "describe_structure", "dimension": 408,
                     "source": "initial coordinates and composition only", "fit_columns": "all408finitecolumns",
                     "forbidden": ["target", "post_DFT_geometry", "relaxed_volume", "relaxed_symmetry", "formation_energies", "band_gap", "unique_prototype_flag", "material_id", "WBM_substitution_round", "initial_final_differences"]},
        "ensemble": {"members": 5, "outer_bootstrap": True, "outer_bootstrap_sample_size": "current_training_size with replacement",
                     "estimator": "sklearn.ensemble.ExtraTreesRegressor", "estimator_kwargs": {
                         "n_estimators": 128, "criterion": "squared_error", "max_depth": None,
                         "min_samples_split": 2, "min_samples_leaf": 2, "max_features": 1.0,
                         "bootstrap": False, "n_jobs": 2},
                     "seed_rule": "numpy.random.SeedSequence([paired_seed,round_index,member_index,11]); separate generated uint32 seeds for outer bootstrap and ExtraTrees",
                     "prediction": "arithmetic mean of five member predictions", "disagreement": "sample standard deviation across five member means, ddof=1",
                     "refit": "Fit all five new members after each batch using initial training plus only that policy's revealed IDs; no cross-policy sharing of queried labels"},
        "calibration": {"population": "fixed400whole-system-held-out rows", "nominal_coverage": .9,
                        "uncertainty_floor_eV_atom": .01, "residual_score": "abs(y_cal-mu_cal)/max(ensemble_std_cal,0.01)",
                        "quantile_rank_1_based": "ceil((n_cal+1)*0.9), sorted observed residual scores", "rank_for_400": 361,
                        "interval_half_width": "u=q90*max(ensemble_std,0.01)",
                        "recalibration": "Recompute residual quantile after each policy refit on the same calibration population; never tune model/scoring coefficients from pool outcomes",
                        "coverage_claim": "Empirical only; chemical-system shift and repeated adaptive use do not establish arbitrary-OOD coverage"},
        "diversity": {"feature_slice": [0, 150], "columns": "118composition fractions,20elementalstatistics,8initialcell,4initialPBCdistance",
                      "normalize": "Column mean and population std fitted ONCE on initial training only; std<1e-12 replaced by1; clip z to[-5,5]",
                      "distance": "min(1,min_RMS_Euclidean_distance_to_labeled_or_current_batch)",
                      "known_set": "initial training plus previously queried rows and current within-batch choices; calibration is not a diversity anchor",
                      "weight": .5, "remains_frozen_across_rounds": True},
        "acquisition": {"policies": list(acquisition.POLICIES), "rounds": 5, "queries_per_round": 10, "queries_per_policy_seed": 50,
                        "shared_initial_label_budget": 2400, "energy_scale_eV_atom": .05, "threshold_eV_atom": .05,
                        "maximize_scores": {"random": "uniform without replacement", "quality": "(0.05-mu)/0.05",
                                            "quality_diversity": "(0.05-mu)/0.05+0.5*D", "uncertainty": "u/0.05",
                                            "full_conservative_first7": "(0.05-mu-u)/0.05+0.5*D", "full_optimistic_last3": "(0.05-mu+u)/0.05+0.5*D"},
                        "tie_break": "lexicographically ascending material ID", "random_generator": "numpyPCG64; SeedSequence([paired_seed,round_index,101])",
                        "label_boundary": "select_batch accepts IDs,predictions,radii,features,distances,RNG only; no oracle label argument; reveal labels only after decision is serialized",
                        "evaluation_only_metrics": ["nearstable_hits_vs_queries", "precision_at50", "historical_hull_hits", "queried_chemical_system_coverage", "MAE", "RMSE", "Spearman_disagreement_absolute_error", "90percent_interval_coverage", "mean_interval_width"],
                        "evaluation_population": {
                            "yield_and_query_coverage": "That policy's selected50poolrows, with cumulative metrics at each10-query batch",
                            "MAE_RMSE_Spearman_interval_coverage_and_width": "Fixed3418rows in each seed's existing unused partition; neverqueried or used for training, calibration, normalization or diversity anchors",
                            "paired_policies": "Identical evaluation IDs for allfive policies within each seed",
                            "evaluation_label_access": "Separate evaluator only; log predictions/decisions first. No evaluator label or metric may affect a fit, selection, hyperparameter or early-stop decision",
                            "queried_training_rows_in_evaluation": False,
                            "additional_training_or_query_labels_from_evaluation": 0},
                        "metrics_may_influence_later_decisions": False},
        "generation": {"global_ceiling": 128, "already_charged": 12, "remaining": 116,
                       "CrystalFormer_sample_attempts": 8, "deterministic_prototype_attempts": 4,
                       "prototype_accounting": "Charge each of the four original prepared substitution candidates once; copies/conversions do not create attempts",
                       "default_CF_attempts": 80, "default_total_including_prototypes": 84, "default_headroom": 44,
                       "stretch_CF_attempts": 96, "stretch_total_including_prototypes": 100, "stretch_headroom": 28,
                       "default_new_formula_count": 6, "conditional_stretch_formula_count": 8,
                       "new_formula_attempts_each": 8, "controls": 2, "arms_each": ["fixed_nontrivial", "P1"], "primary_attempts_per_arm": 8,
                       "formula_free_branch": "disabled", "control_settings": "artifacts/phase2/controls/matched_protocol.json",
                       "pilot_reuse": "MgO SG225 first8 reused only if exact frozen settings preserved; otherwise all8 remain charged engineering attempts"},
        "chgnet_reallocation": {"global_ceiling": 40, "already_charged_including_failed_launches": 8, "remaining_ceiling": 32,
                                "symmetry_max": 10, "symmetry_reason": "MgO at most1uniqueperarm=2; secondcontrol atmost4perarm=8; always q=min(4,nvalidSG,nvalidP1)",
                                "new_composition_shortlist_and_DFT_prerelax_max": 12,
                                "prototype_substitution_max": 4, "same_composition_reference_max": 4,
                                "explicit_retry_contingency_max": 2,
                                "remaining_suballocations_sum": 32, "unused_slots_not_automatically_spent": True,
                                "per_job": {"model": "0.3.0", "package": "0.4.2", "steps_max": 200, "fmax_eV_A": .05, "relax_cell": True, "imposed_symmetry": False},
                                "global_time_seconds": 14400, "already_charged_seconds": 23.862674800002424},
        "qe": {"global_cumulative_seconds": 21600, "already_charged_seconds": 2.103912800001126,
               "plan": "artifacts/phase2/dft/reference_plan.json", "one_job_at_a_time": True, "omp_mkl_threads": 4,
               "all_jobs_and_failures_charged": True, "numerical_stop_utc": "2026-10-22T10:24:44+00:00"},
        "budget_aggregation_requirement": "All new phase ledgers must be explicitly registered in the cumulative ledger; Phase1 finalizer alone does not discover future ledgers.",
        "sources": ["https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html",
                    "https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.GroupShuffleSplit.html"],
        "acquisition_implementation_sha256": digest(ROOT / "research_acquisition.py"),
        "freezer_script_sha256": digest(Path(__file__))}
    target = config_dir / "phase2_protocol.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        comparable_existing = {k: v for k, v in existing.items() if k != "frozen_utc"}
        comparable_new = {k: v for k, v in record.items() if k != "frozen_utc"}
        if comparable_existing != comparable_new:
            if not args.amend_before_training:
                raise RuntimeError("Frozen protocol differs. Do not silently replace it after outcomes exist.")
            phase3 = ROOT / "artifacts/phase3"
            if phase3.exists() and any(phase3.rglob("*")):
                raise RuntimeError("Pre-training amendment is unavailable once Phase3 artifacts exist")
            previous_sha = digest(target)
            revisions = out / "revisions"
            revisions.mkdir(exist_ok=True)
            archive = revisions / f"protocol_{previous_sha}.json"
            archive.write_bytes(target.read_bytes())
            target.write_text(json.dumps(record, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            amendment = {"utc": record["frozen_utc"], "reason": args.amend_before_training,
                         "previous_sha256": previous_sha, "new_sha256": digest(target),
                         "previous_copy": archive.relative_to(ROOT).as_posix(),
                         "verified_no_phase3_artifacts": True, "model_fits_and_queries_before_amendment": 0}
            with (out / "amendments.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(amendment)+"\n")
    else:
        target.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out / "synthetic_checks.json").write_text(json.dumps(checks, indent=2)+"\n", encoding="utf-8")
    manifest = {"status": "frozen", "protocol": {"path": target.relative_to(ROOT).as_posix(), "sha256": digest(target)},
                "acquisition_module": {"path": "research_acquisition.py", "sha256": digest(ROOT / "research_acquisition.py")},
                "synthetic_check_count": len(checks["checks"]), "actual_model_fits": 0, "actual_replay_query_reveals": 0}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
