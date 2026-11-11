"""Audit frozen replay lineage and describe saved, already evaluated predictions.

This script never fits a model, generates predictions, selects a batch, changes
calibration, or reads a previously unrevealed pool label. It decodes target values
only for IDs already present in the five original isolated evaluator access logs.
The union is used solely for post hoc scoring of saved prediction arrays.
"""
from __future__ import annotations

import ast
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
os.environ["OMP_NUM_THREADS"] = "2"
import joblib
import numpy as np
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = ROOT / "artifacts/phase6/uncertainty"
SEEDS = tuple(range(20261022, 20261027))
POLICIES = ("random", "quality", "quality_diversity", "uncertainty", "full")
PARTITIONS = ("train", "calibration", "pool", "unused", "fresh_reserved")
TARGET = "e_above_hull_mp2020_corrected_ppd_mp"
PROTOCOL_SHA = "b71724ad4e9a940de090d4163bc6a23a10ed9bfb957fb656b50222b884d36c94"
FRESH_SHA = "b7cbae9c54cdc486bac5d9de743f3e75e2322bf7bf01a3f03f7b92acfa3e8359"
CHECKS, SOURCES = [], {}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def source(path):
    path = Path(path)
    value = sha(path)
    SOURCES[rel(path)] = {"sha256": value, "size_bytes": path.stat().st_size}
    return value


def read(path):
    source(path)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def lines(path):
    source(path)
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def check(name, condition, details=None):
    item = {"name": name, "passed": bool(condition)}
    if details is not None:
        item["details"] = details
    CHECKS.append(item)
    if not condition:
        raise AssertionError(name)


def close(a, b):
    return bool(np.allclose(a, b, rtol=1e-12, atol=1e-12))


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def utc(value):
    return datetime.fromisoformat(value)


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def table(name, rows):
    with (OUT / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def describe(values):
    values = np.asarray(values, dtype=float)
    return {"values": values.tolist(), "mean": float(values.mean()),
            "sample_std": float(values.std(ddof=1)), "min": float(values.min()), "max": float(values.max())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source(Path(__file__))
    protocol_path = ROOT / "config/phase2_protocol.json"
    protocol = read(protocol_path)
    check("frozen_protocol_digest", source(protocol_path) == PROTOCOL_SHA)
    check("frozen_acquisition_digest", source(ROOT / "research_acquisition.py") == protocol["acquisition_implementation_sha256"])
    source(ROOT / "research_models.py")
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden = [node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr in ("fit", "predict", "partial_fit", "select_batch")]
    check("analysis_has_no_fit_predict_or_batch_selection_calls", not forbidden)

    feature_root = ROOT / "artifacts/phase2/features"
    manifest = read(feature_root / "feature_manifest.json")
    schema = read(feature_root / "feature_schema.json")
    validation = read(feature_root / "validation_report.json")
    check("feature_source_matches_committed_initial_only_extractor", source(ROOT / "research_features.py") == manifest["implementation"]["module_sha256"])
    for name in ("features.npz", "row_metadata.csv", "feature_schema.json", "validation_report.json", "initial_structures.jsonl.gz"):
        check("feature_output_hash_" + name, source(feature_root / name) == manifest["outputs"][name]["sha256"])
    with np.load(feature_root / "features.npz", allow_pickle=False) as features:
        X, feature_ids = features["X"].copy(), features["material_ids"].tolist()
        feature_names = features["feature_names"].tolist()
        check("feature_archive_contains_no_labels", set(features.files) == {"X", "material_ids", "feature_names"})
    check("408_initial_only_features_and_finite_8294_rows", X.shape == (8294, 408) and len(feature_names) == 408 and np.isfinite(X).all())
    check("feature_names_match_initial_only_schema", feature_names == [row["name"] for row in schema["features"]])
    check("feature_schema_explicit_initial_allowlist", schema["input_allowlist"] == ["initial_structure.lattice.matrix", "initial_structure.sites[].species (element identities)", "initial_structure.sites[].abc (fractional positions)"])
    check("saved_feature_property_injection_and_invariance_checks_passed", validation["passed"] and not validation["summary_files_read_by_extractor"] and not validation["summary_or_target_arguments_accepted"])
    with (feature_root / "row_metadata.csv").open(encoding="utf-8", newline="") as stream:
        metadata_rows = list(csv.DictReader(stream))
    metadata = {row["material_id"]: row for row in metadata_rows}
    check("feature_metadata_ids_exact_and_unique", [row["material_id"] for row in metadata_rows] == feature_ids and len(metadata) == 8294)
    position = {mid: i for i, mid in enumerate(feature_ids)}
    reserved = read(ROOT / "artifacts/phase2/splits/reserved_systems.json")
    reserved_systems = set(reserved["chemical_systems"])
    observed_reserved = {row["chemical_system"] for row in metadata_rows} & reserved_systems
    reserved_ids = {mid for mid, row in metadata.items() if row["chemical_system"] in reserved_systems}
    check("all_78_palette_systems_reserved_74_observed_476_rows", len(reserved_systems) == 78 and len(observed_reserved) == 74 and len(reserved_ids) == 476)

    fresh_path = ROOT / "artifacts/phase3/models/fresh_selector_seed_20261022.joblib"
    fresh_manifest = read(fresh_path.with_suffix(".manifest.json"))
    check("original_fresh_selector_immutable", source(fresh_path) == fresh_manifest["sha256"] == FRESH_SHA)
    shortlist = read(ROOT / "artifacts/phase4/selection/fresh_shortlist.json")
    check("fresh_shortlist_binds_original_selector_only", shortlist["fresh_selector_sha256"] == FRESH_SHA and shortlist["selected_count"] == 0)

    runs, endpoints, curves, lineage_rows, overlap, role_queries = [], [], [], [], [], []
    seen_evaluation_ids = set()
    for seed in SEEDS:
        phase = 3 if seed == SEEDS[0] else 4
        directory = ROOT / f"artifacts/phase{phase}/replay/seed_{seed}"
        split_path = ROOT / f"artifacts/phase2/splits/seed_{seed}.json"
        split_doc = read(split_path)
        split = split_doc["material_ids"]
        partitions = {name: set(split[name]) for name in PARTITIONS}
        groups = {name: {metadata[mid]["chemical_system"] for mid in split[name]} for name in PARTITIONS}
        check(f"seed_{seed}_partition_covers_every_row_once", set.union(*partitions.values()) == set(feature_ids) and sum(map(len, partitions.values())) == len(feature_ids))
        for i, first in enumerate(PARTITIONS):
            check(f"seed_{seed}_{first}_declared_groups_match_metadata", groups[first] == set(split_doc["groups"][first]))
            for second in PARTITIONS[i+1:]:
                check(f"seed_{seed}_{first}_{second}_whole_system_separation", not groups[first] & groups[second] and not partitions[first] & partitions[second])
        check(f"seed_{seed}_reserved_exclusion", partitions["fresh_reserved"] == reserved_ids and not reserved_systems & set.union(*(groups[name] for name in PARTITIONS[:-1])))
        check(f"seed_{seed}_exact_partition_counts", [len(split[name]) for name in PARTITIONS] == [2000, 400, 2000, 3418, 476])
        training_elements = {element for system in groups["train"] for element in system.split("-")}
        check(f"seed_{seed}_all_palette_elements_seen_individually", set(reserved["palette"]) | {"O"} <= training_elements)
        model_path = fresh_path if phase == 3 else ROOT / f"artifacts/phase4/models/seed_{seed}/initial_paired_seed_{seed}.joblib"
        initial_manifest = read(model_path.with_suffix(".manifest.json"))
        check(f"seed_{seed}_initial_model_hash", source(model_path) == initial_manifest["sha256"])
        check(f"seed_{seed}_initial_commit_before_any_queries_or_evaluation", initial_manifest["pool_queries_revealed_before_snapshot"] == initial_manifest["evaluation_labels_read_before_snapshot"] == 0)
        check(f"seed_{seed}_initial_provenance", initial_manifest["provenance"]["protocol_sha256"] == PROTOCOL_SHA and initial_manifest["provenance"]["split_sha256"] == source(split_path))
        # Trusted local checkpoint inspection only; no estimator method is called.
        initial = joblib.load(model_path)
        train_X = np.asarray(X[[position[mid] for mid in split["train"]], :150], dtype=float)
        scale = train_X.std(axis=0)
        scale[scale < 1e-12] = 1
        check(f"seed_{seed}_initial_only_diversity_normalizer", np.array_equal(initial["normalization"]["center"], train_X.mean(axis=0)) and np.array_equal(initial["normalization"]["scale"], scale))
        check(f"seed_{seed}_initial_model_ids", initial["train_ids"] == split["train"] and initial["calibration_ids"] == split["calibration"])
        if phase == 4:
            check(f"seed_{seed}_adapted_seed_never_fresh_selector", not initial["immutable_fresh_selector"] and initial_manifest["provenance"]["original_fresh_selector_sha256"] == FRESH_SHA and not initial_manifest["provenance"]["this_seed_initial_model_used_for_fresh_generation"])
        del initial
        access = lines(directory / "label_access.jsonl")
        query_access = {row["role"]: row for row in access if row["role"].endswith("_query")}
        check(f"seed_{seed}_original_label_access_exact", len(access) == 27 and len(query_access) == 25 and all(row["unrequested_numeric_values_decoded"] == 0 for row in access))
        check(f"seed_{seed}_initial_commit_precedes_all_pool_label_access", utc(initial_manifest["completed_at_utc"]) < min(utc(row["utc_started"]) for row in query_access.values()))
        check(f"seed_{seed}_original_fresh_commit_precedes_pool_access", utc(fresh_manifest["completed_at_utc"]) < min(utc(row["utc_started"]) for row in query_access.values()))
        all_complete = read(directory / "all_policy_queries_complete.json")
        eval_access = lines(directory / "evaluation_label_access.jsonl")
        check(f"seed_{seed}_only_original_untouched_evaluator_ids", len(eval_access) == 1 and eval_access[0]["material_ids"] == split["unused"] and eval_access[0]["count"] == 3418)
        check(f"seed_{seed}_evaluation_begins_after_all_policies_finish", utc(all_complete["completed_at_utc"]) <= utc(eval_access[0]["utc_started"]) and all_complete["evaluator_labels_read_so_far"] == 0)
        evaluator = read(directory / "evaluation_summary.json")
        check(f"seed_{seed}_evaluation_has_no_learner_feedback", evaluator["policy_decisions_finished_before_label_access"] and all(row["labels_returned_to_learner"] == 0 for row in evaluator["evaluated_predictions"]))
        old_summary = read(directory / "summary.json")
        check(f"seed_{seed}_saved_decision_metric_feedback_disabled", not old_summary["evaluator_metric_feedback_to_decisions"])
        prior_audit = read(ROOT / f"artifacts/phase4/replay/audits/seed_{seed}.json")
        check(f"seed_{seed}_saved_bootstrap_calibration_decision_audit_passed", prior_audit["status"] == "passed" and prior_audit["recomputed_calibrations"] == 26 and prior_audit["decisions_replayed_from_pre_reveal_predictions"] == 25)
        predictions = [{"policy": "initial_shared", "queries": 0, "path": directory / "initial_eval_predictions.npz", "calibration": initial_manifest["calibration"]}]
        for policy in POLICIES:
            queried, labels = [], []
            old_policy = next(row for row in old_summary["policies"] if row["policy"] == policy)
            for round_index in range(1, 6):
                round_dir = directory / policy / f"round_{round_index:02d}"
                completion = read(round_dir / "complete.json")
                decision, reveal, fit = [read(round_dir / name) for name in ("decision.json", "reveals.json", "fit_audit.json")]
                for name, key in (("decision.json", "decision_sha256"), ("reveals.json", "reveal_sha256"), ("fit_audit.json", "fit_audit_sha256"), ("adapted_model.joblib", "model_sha256")):
                    check(f"{seed}_{policy}_{round_index}_hash_{name}", source(round_dir / name) == completion[key])
                chosen = reveal["material_ids"]
                entry = query_access[f"{policy}_round_{round_index}_query"]
                check(f"{seed}_{policy}_{round_index}_decision_before_reveal", decision["material_ids"] == chosen == entry["material_ids"] and utc(decision["committed_at_utc"]) <= utc(entry["utc_started"]) <= utc(entry["utc_complete"]) <= utc(reveal["revealed_at_utc"]))
                if policy == "full":
                    check(f"{seed}_{policy}_{round_index}_frozen_seven_three_roles", [info["role"] for info in decision["decisions"]] == ["conservative"] * 7 + ["optimistic"] * 3)
                    for info, label in zip(decision["decisions"], reveal["labels_eV_atom"], strict=True):
                        role_queries.append({"seed": seed, "round": round_index, "role": info["role"], "label_eV_atom": label, "predicted_mean_eV_atom": info["predicted_mean_eV_atom"], "calibrated_radius_eV_atom": info["calibrated_radius_eV_atom"], "diversity_distance": info["diversity_distance_at_selection"]})
                check(f"{seed}_{policy}_{round_index}_selection_is_pool_only_and_unique", len(chosen) == len(set(chosen)) == 10 and set(chosen) <= partitions["pool"] and not set(chosen) & set(queried))
                check(f"{seed}_{policy}_{round_index}_pre_reveal_own_model_lineage", decision["model_training_ids_sha256"] == canonical(split["train"] + queried) and decision["oracle_labels_supplied_to_acquisition"] == 0)
                queried.extend(chosen)
                labels.extend(reveal["labels_eV_atom"])
                check(f"{seed}_{policy}_{round_index}_post_reveal_own_labels_only", fit["training_ids"] == split["train"] + queried and fit["calibration_ids"] == split["calibration"] and not set(fit["training_ids"]) & (partitions["unused"] | reserved_ids))
                check(f"{seed}_{policy}_{round_index}_frozen_hyperparameters", fit["estimator_kwargs"] == protocol["ensemble"]["estimator_kwargs"] and not fit["normalization_refitted"])
                check(f"{seed}_{policy}_{round_index}_fit_completed_before_evaluator_access", utc(reveal["revealed_at_utc"]) <= utc(fit["started_at_utc"]) <= utc(fit["completed_at_utc"]) <= utc(eval_access[0]["utc_started"]))
                pool_commit = read(round_dir / "pool_predictions_before_reveal.commit.json")
                check(f"{seed}_{policy}_{round_index}_pool_prediction_commit", source(round_dir / "pool_predictions_before_reveal.npz") == pool_commit["sha256"] == decision["pool_prediction_sha256"] and utc(pool_commit["created_at_utc"]) <= utc(decision["committed_at_utc"]))
                point = {"seed": seed, "policy": policy, "queries": len(queried), "near_stable_hits": int(np.sum(np.asarray(labels) <= .05)), "reference_hull_hits": int(np.sum(np.asarray(labels) <= 0)), "chemical_system_coverage": len({metadata[mid]["chemical_system"] for mid in queried})}
                check(f"{seed}_{policy}_{round_index}_recomputed_curve", all(point[key] == old_policy["curve"][round_index-1][key] for key in ("queries", "near_stable_hits", "reference_hull_hits", "chemical_system_coverage")))
                curves.append(point)
                lineage_rows.append({"seed": seed, "policy": policy, "round": round_index, "training_rows": len(fit["training_ids"]), "only_own_query_labels": True, "calibration_rows": 400, "evaluation_rows": 3418, "decision_before_reveal": True, "all_fits_before_evaluation_access": True})
                predictions.append({"policy": policy, "queries": 10*round_index, "path": round_dir / "evaluation_predictions.npz", "calibration": fit["calibration"]})
            check(f"{seed}_{policy}_endpoint_fifty_unique", len(queried) == len(set(queried)) == 50 and queried == old_policy["queried_ids"])
            endpoints.append({**point, "precision_at_50": point["near_stable_hits"] / 50})
        for prediction in predictions:
            path = prediction["path"]
            commit = read(path.with_suffix(".commit.json"))
            check(f"{seed}_{prediction['policy']}_{prediction['queries']}_evaluation_prediction_precedes_label_access", source(path) == commit["sha256"] and utc(commit["created_at_utc"]) <= utc(eval_access[0]["utc_started"]) and not commit["oracle_labels_in_file"])
            with np.load(path, allow_pickle=False) as values:
                check(f"{seed}_{prediction['policy']}_{prediction['queries']}_exact_untouched_ids", values["material_ids"].tolist() == split["unused"] and all(np.isfinite(values[key]).all() for key in ("mean", "std", "radius")))
                check(f"{seed}_{prediction['policy']}_{prediction['queries']}_saved_radius_matches_frozen_calibration", close(values["radius"], prediction["calibration"]["q"] * np.maximum(values["std"], .01)))
        runs.append({"seed": seed, "directory": directory, "split": split, "predictions": predictions, "eval_access": eval_access[0]})
        seen_evaluation_ids.update(split["unused"])

    for i, first in enumerate(runs):
        for second in runs[i+1:]:
            overlap.append({"seed_1": first["seed"], "seed_2": second["seed"], "evaluation_ID_overlap": len(set(first["split"]["unused"]) & set(second["split"]["unused"])), "training_ID_overlap": len(set(first["split"]["train"]) & set(second["split"]["train"]))})
    check("all_requested_posthoc_targets_were_already_evaluated_and_no_reserved_targets", len(seen_evaluation_ids) > 3418 and not seen_evaluation_ids & reserved_ids)
    # Every decoding request is authorized by at least one original evaluator log.
    # Unrequested numeric text is left opaque, including all 476 reserved rows.
    oracle_path = ROOT / "artifacts/phase2/splits/oracle_labels.csv"
    oracle_sha = source(oracle_path)
    check("frozen_original_oracle_digest", oracle_sha == fresh_manifest["provenance"]["oracle_file_sha256"])
    target = {}
    with oracle_path.open(encoding="utf-8", newline="") as stream:
        check("historical_target_schema", stream.readline().strip() == "material_id," + TARGET)
        for line in stream:
            mid, separator, opaque = line.rstrip("\r\n").partition(",")
            if mid in seen_evaluation_ids:
                check("posthoc_unique_target_" + mid, bool(separator) and mid not in target)
                target[mid] = float(opaque)
    check("posthoc_target_join_exact_and_finite", set(target) == seen_evaluation_ids and all(math.isfinite(v) for v in target.values()))

    evaluations, bins, risks = [], [], []
    for run in runs:
        y = np.asarray([target[mid] for mid in run["split"]["unused"]])
        for prediction in run["predictions"]:
            path = prediction["path"]
            saved_metrics = read(path.with_suffix(".metrics.json"))
            with np.load(path, allow_pickle=False) as values:
                error = np.abs(y - values["mean"])
                row = {"seed": run["seed"], "policy": prediction["policy"], "queries": prediction["queries"], "n": len(y), "MAE_eV_atom": float(error.mean()), "RMSE_eV_atom": float(np.sqrt(np.mean(error**2))), "Spearman_disagreement_absolute_error": float(spearmanr(values["std"], error).statistic), "interval_90_empirical_coverage": float(np.mean(error <= values["radius"])), "mean_interval_width_eV_atom": float(2*values["radius"].mean()), "calibration_q": prediction["calibration"]["q"]}
                check(f"{run['seed']}_{prediction['policy']}_{prediction['queries']}_all_metrics_reproduced", all(close(row[key], saved_metrics[key]) for key in ("n", "MAE_eV_atom", "RMSE_eV_atom", "Spearman_disagreement_absolute_error", "interval_90_empirical_coverage", "mean_interval_width_eV_atom")))
                evaluations.append(row)
                if prediction["queries"] not in (0, 50):
                    continue
                order = np.lexsort((values["material_ids"], values["std"]))
                for decile, indices in enumerate(np.array_split(order, 10), start=1):
                    bins.append({"seed": run["seed"], "policy": prediction["policy"], "queries": prediction["queries"], "uncertainty_decile": decile, "n": len(indices), "mean_disagreement_eV_atom": float(values["std"][indices].mean()), "min_disagreement_eV_atom": float(values["std"][indices].min()), "max_disagreement_eV_atom": float(values["std"][indices].max()), "MAE_eV_atom": float(error[indices].mean()), "interval_90_empirical_coverage": float(np.mean(error[indices] <= values["radius"][indices])), "mean_interval_width_eV_atom": float(2*values["radius"][indices].mean())})
                for decile in range(1, 11):
                    k = math.ceil(len(order) * decile / 10)
                    indices = order[:k]
                    risks.append({"seed": run["seed"], "policy": prediction["policy"], "queries": prediction["queries"], "requested_retained_fraction": decile/10, "retained_rows": k, "actual_retained_fraction": k/len(order), "MAE_eV_atom": float(error[indices].mean()), "all_rows_MAE_eV_atom": float(error.mean()), "MAE_relative_to_all_rows": float(error[indices].mean()/error.mean()), "interval_90_empirical_coverage": float(np.mean(error[indices] <= values["radius"][indices]))})
    check("all_130_saved_prediction_sets_scored", len(evaluations) == 130 and len(endpoints) == 25 and len(curves) == 125)
    check("all_30_endpoint_or_initial_sets_binned", len(bins) == len(risks) == 300)
    policies = {policy: {key: describe([row[key] for row in endpoints if row["policy"] == policy]) for key in ("near_stable_hits", "precision_at_50", "reference_hull_hits", "chemical_system_coverage")} for policy in POLICIES}
    paired = []
    for seed in SEEDS:
        by_policy = {row["policy"]: row for row in endpoints if row["seed"] == seed}
        paired.append({"seed": seed, "full_minus_quality_hits": by_policy["full"]["near_stable_hits"]-by_policy["quality"]["near_stable_hits"], "full_minus_quality_diversity_hits": by_policy["full"]["near_stable_hits"]-by_policy["quality_diversity"]["near_stable_hits"], "full_minus_quality_chemical_system_coverage": by_policy["full"]["chemical_system_coverage"]-by_policy["quality"]["chemical_system_coverage"]})
    endpoint_evaluation = {}
    for policy in ("initial_shared", *POLICIES):
        rows = [row for row in evaluations if row["policy"] == policy and row["queries"] == (0 if policy == "initial_shared" else 50)]
        endpoint_evaluation[policy] = {key: describe([row[key] for row in rows]) for key in ("MAE_eV_atom", "RMSE_eV_atom", "Spearman_disagreement_absolute_error", "interval_90_empirical_coverage", "mean_interval_width_eV_atom", "calibration_q")}
    role_diagnostics = []
    for seed in SEEDS:
        for role, count in (("conservative", 35), ("optimistic", 15)):
            rows = [row for row in role_queries if row["seed"] == seed and row["role"] == role]
            check(f"seed_{seed}_full_{role}_query_allocation", len(rows) == count)
            role_diagnostics.append({"seed": seed, "role": role, "queries": count, "near_stable_hits": sum(row["label_eV_atom"] <= .05 for row in rows), "precision": sum(row["label_eV_atom"] <= .05 for row in rows)/count, "reference_hull_hits": sum(row["label_eV_atom"] <= 0 for row in rows), "mean_predicted_mean_eV_atom": float(np.mean([row["predicted_mean_eV_atom"] for row in rows])), "mean_calibrated_radius_eV_atom": float(np.mean([row["calibrated_radius_eV_atom"] for row in rows])), "mean_diversity_distance": float(np.mean([row["diversity_distance"] for row in rows]))})
    risk_aggregates = {}
    for policy in ("initial_shared", *POLICIES):
        risk_aggregates[policy] = {str(fraction): {key: describe([row[key] for row in risks if row["policy"] == policy and row["requested_retained_fraction"] == fraction]) for key in ("MAE_eV_atom", "MAE_relative_to_all_rows", "interval_90_empirical_coverage")} for fraction in (.1, .5, 1.0)}
    plot(endpoints, evaluations, bins, risks)
    table("policy_endpoints.csv", endpoints)
    table("learning_curves.csv", curves)
    table("paired_differences.csv", paired)
    table("evaluation_metrics.csv", evaluations)
    table("uncertainty_deciles.csv", bins)
    table("risk_coverage.csv", risks)
    table("lineage_by_round.csv", lineage_rows)
    table("cross_seed_overlap.csv", overlap)
    table("full_policy_role_diagnostics.csv", role_diagnostics)
    summary = {
        "status": "completed", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": list(SEEDS), "historical_query_events": 1250, "new_pool_queries": 0, "new_model_fits": 0,
        "new_model_predictions": 0, "new_calibration_fits": 0, "saved_prediction_sets_recomputed": 130,
        "untouched_evaluation_rows_per_seed": 3418, "distinct_already_evaluated_target_IDs_decoded_posthoc": len(target),
        "target_access_scope": "Only union of IDs in original isolated evaluator logs; unrequested numeric values left opaque. This is post hoc evaluation, with no learner feedback or fresh oracle reveals.",
        "target_source": {"path": rel(oracle_path), "sha256": oracle_sha, "column": TARGET},
        "policy_endpoint_aggregates": policies, "paired_differences": paired,
        "full_minus_quality_hits": describe([row["full_minus_quality_hits"] for row in paired]),
        "evaluation_endpoint_aggregates": endpoint_evaluation,
        "risk_coverage_aggregates": risk_aggregates,
        "full_policy_role_diagnostics": role_diagnostics,
        "full_policy_role_scope": "Descriptive decomposition of the frozen sequential seven-conservative/three-optimistic allocation. Roles were not randomized; this does not estimate a causal effect of either role.",
        "fresh_selector_sha256": FRESH_SHA, "fresh_selector_snapshot_precedes_every_pool_and_evaluation_label_read": True,
        "fresh_shortlist_uses_original_selector": True, "fresh_shortlist_selected_count": 0,
        "reserved_chemical_systems": 78, "observed_reserved_systems": 74, "reserved_rows": 476,
        "unobserved_reserved_systems": sorted(reserved_systems - observed_reserved),
        "whole_chemical_system_separation_within_every_seed": True,
        "normalization_fitted_only_initial_training_and_checked_without_model_inference": True,
        "policy_own_label_lineage_rounds_verified": 125, "cross_seed_evaluation_overlaps": overlap,
        "feature_scope": "408 descriptors computed only from initial structure composition, cell, periodic distances and recomputed initial symmetry; no released relaxed structures, energies, hull labels, CHGNet or QE outputs.",
        "risk_coverage_method": "For each seed and initial/final saved model, sort untouched rows by ensemble disagreement ascending, material ID tie break; retain ceil(n*f) for f=0.1,...,1.0. No threshold optimization or retraining.",
        "uncertainty_bins_method": "Ten equal-count bins (numpy.array_split) ordered by saved disagreement and material ID within each seed/model; purely descriptive post hoc diagnostics.",
        "scientific_limits": [
            "Five splits reuse one overlapping WBM population; mean and sample SD are descriptive, with no independent-seed significance claim.",
            "Prediction intervals are empirically scaled using chemical-system calibration groups. Group shift and repeated adaptive reuse prevent an arbitrary-OOD coverage guarantee.",
            "The fixed full policy lost to quality on all five near-stable-hit endpoints; coefficients, models and calibration remain unchanged after this result.",
            "Historical signed hull-distance hits are retrieval from existing DFT labels, not newly calculated, novel or DFT-confirmed stable material discoveries.",
            "Calibration and evaluation groups are disjoint within a seed; pretrained generator or CHGNet training-set contamination is outside this supervised replay audit.",
            "Uncertainty-error association and selective risk diagnostics do not establish calibrated uncertainty for fresh generated crystals or QM energy predictions."
        ],
        "figures": ["uncertainty_reliability.png", "uncertainty_reliability.pdf"],
    }
    write(OUT / "summary.json", summary)
    write(OUT / "posthoc_target_access.json", {"completed_at_utc": summary["completed_at_utc"], "role": "Phase6_posthoc_only_already_evaluated_targets", "source_path": rel(oracle_path), "source_sha256": oracle_sha, "target_IDs": sorted(target), "target_IDs_sha256": canonical(sorted(target)), "previously_evaluated_IDs_decoded": len(target), "new_pool_labels_revealed": 0, "reserved_labels_decoded": 0, "unrequested_numeric_values_decoded": 0, "decisions_complete_before_this_analysis": True, "original_evaluator_access_logs": [rel(run["directory"] / "evaluation_label_access.jsonl") for run in runs]})
    # Hash every input again; no pre-existing evidence may be changed by analysis.
    unchanged = all(sha(ROOT / path) == entry["sha256"] for path, entry in SOURCES.items())
    check("all_analysis_inputs_unchanged_after_analysis", unchanged)
    write(OUT / "source_manifest.json", {"status": "verified_unchanged", "files": SOURCES, "all_preexisting_inputs_unchanged": unchanged, "method": "SHA256 before use and after completed posthoc analysis"})
    write(OUT / "audit.json", {"status": "passed", "checks_passed": len(CHECKS), "checks_total": len(CHECKS), "failed_checks": [], "checks": CHECKS, "new_pool_queries": 0, "new_model_fits": 0, "new_model_predictions": 0, "source_manifest_sha256": sha(OUT / "source_manifest.json"), "summary_sha256": sha(OUT / "summary.json"), "all_preexisting_inputs_unchanged": unchanged})
    print(json.dumps({"status": "completed", "checks": len(CHECKS), "decoded_already_evaluated_ids": len(target), "full_minus_quality": summary["full_minus_quality_hits"], "initial_coverage": endpoint_evaluation["initial_shared"]["interval_90_empirical_coverage"], "final_full_coverage": endpoint_evaluation["full"]["interval_90_empirical_coverage"]}, indent=2))


def plot(endpoints, evaluations, bins, risks):
    colors = {"initial_shared": "#555555", "quality": "#0072B2", "full": "#CC79A7", "random": "#999999", "quality_diversity": "#009E73", "uncertainty": "#E69F00"}
    names = {"initial_shared": "Initial", "quality": "Quality", "full": "Full", "random": "Random", "quality_diversity": "Quality + diversity", "uncertainty": "Uncertainty"}
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42}):
        figure, axes = plt.subplots(2, 2, figsize=(11, 8.3), constrained_layout=True)
        ax = axes[0, 0]
        for i, seed in enumerate(SEEDS):
            by_policy = {row["policy"]: row for row in endpoints if row["seed"] == seed}
            delta = by_policy["full"]["near_stable_hits"] - by_policy["quality"]["near_stable_hits"]
            ax.bar(i, delta, color=colors["quality"], width=.65)
            ax.text(i, delta-.6, str(delta), ha="center", va="top", fontsize=9)
        ax.axhline(0, color="#444444", lw=.8)
        ax.set_xticks(range(5), [str(seed)[-2:] for seed in SEEDS])
        ax.set(title="A  Every paired endpoint favors quality", xlabel="Frozen split seed (202610xx)", ylabel="Full minus quality near-stable hits / 50", ylim=(-22, 1))
        ax = axes[0, 1]
        for i, policy in enumerate(("initial_shared", *POLICIES)):
            rows = [row for row in evaluations if row["policy"] == policy and row["queries"] == (0 if policy == "initial_shared" else 50)]
            vals = np.asarray([row["interval_90_empirical_coverage"] for row in rows])
            ax.scatter(np.full(5, i)+np.linspace(-.12, .12, 5), vals, s=18, alpha=.7, color=colors[policy])
            ax.scatter(i, vals.mean(), marker="_", s=160, color="black", zorder=5)
        ax.axhline(.9, ls="--", lw=1, color="#444444", label="Nominal 90%")
        ax.set_xticks(range(6), [names[p] for p in ("initial_shared", *POLICIES)], rotation=24, ha="right")
        ax.set(title="B  Empirical interval coverage by split", ylabel="Untouched evaluation-row coverage", ylim=(.7, 1))
        ax.legend(frameon=False, fontsize=8, loc="lower left")
        ax = axes[1, 0]
        for policy in ("initial_shared", "quality", "full"):
            matrix = np.asarray([[row["MAE_eV_atom"] for row in risks if row["seed"] == seed and row["policy"] == policy] for seed in SEEDS])
            x = np.arange(1, 11)/10
            for values in matrix:
                ax.plot(x, values, color=colors[policy], alpha=.15, lw=.7)
            ax.plot(x, matrix.mean(axis=0), color=colors[policy], marker="o", ms=3, label=names[policy])
        ax.set(title="C  Risk when retaining low-disagreement rows", xlabel="Fraction of untouched rows retained", ylabel="Mean absolute error (eV/atom)", xlim=(.08, 1.02))
        ax.legend(frameon=False, fontsize=8)
        ax = axes[1, 1]
        for policy in ("initial_shared", "quality", "full"):
            xmat = np.asarray([[row["mean_disagreement_eV_atom"] for row in bins if row["seed"] == seed and row["policy"] == policy] for seed in SEEDS])
            ymat = np.asarray([[row["MAE_eV_atom"] for row in bins if row["seed"] == seed and row["policy"] == policy] for seed in SEEDS])
            ax.plot(xmat.mean(axis=0), ymat.mean(axis=0), marker="o", ms=3, color=colors[policy], label=names[policy])
        ax.set(title="D  Equal-count uncertainty deciles", xlabel="Mean ensemble disagreement (eV/atom)", ylabel="Mean absolute error (eV/atom)")
        ax.legend(frameon=False, fontsize=8)
        for ax in axes.flat:
            ax.grid(axis="y", alpha=.17)
        figure.suptitle("Frozen WBM replay: uncertainty diagnostics after every decision finished", fontsize=12)
        figure.supxlabel("Five overlapping chemical-system splits; all aggregates descriptive. No retuning, new labels, model fits or inference.", fontsize=8)
        for extension in ("png", "pdf"):
            figure.savefig(OUT / f"uncertainty_reliability.{extension}", dpi=220)
        plt.close(figure)


if __name__ == "__main__":
    main()
