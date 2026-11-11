"""Execute one remaining frozen paired replay seed without changing Phase 3 evidence.

Each seed initial model is exclusively for its paired retrospective replay. The
original seed-20261022 Phase 3 checkpoint remains the only fresh selector. Existing
committed work requires explicit --resume and is never silently refit or queried.
"""

from __future__ import annotations

import os
for _name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "2"

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits
import research_acquisition as acquisition
import research_models

SEED = 20261023
PROTOCOL = ROOT / "config" / "phase2_protocol.json"
MODEL_ROOT = ROOT / "artifacts" / "phase4" / "models" / f"seed_{SEED}"
LOG_ROOT = ROOT / "artifacts" / "phase4" / "model_logs" / f"seed_{SEED}"
RUN = ROOT / "artifacts" / "phase4" / "replay" / f"seed_{SEED}"
FEATURE_FILE = ROOT / "artifacts" / "phase2" / "features" / "features.npz"
FEATURE_MANIFEST = FEATURE_FILE.parent / "feature_manifest.json"
SPLIT_FILE = ROOT / "artifacts" / "phase2" / "splits" / f"seed_{SEED}.json"
ORACLE = ROOT / "artifacts" / "phase2" / "splits" / "oracle_labels.csv"
TARGET = "e_above_hull_mp2020_corrected_ppd_mp"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path, value, exclusive=False):
    path = Path(path)
    if exclusive and path.exists():
        raise FileExistsError(f"Refusing to overwrite immutable evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def append(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def log(message):
    line = f"{now()} {message}"
    print(line, flush=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    with (LOG_ROOT / "run.log").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def read_authorized_labels(material_ids, allowed_ids, role, access_log, commit=None):
    """Decode numeric labels only for authorized IDs; unrelated values stay opaque.

    The source is a simple two-column, unquoted ID/numeric CSV. We inspect its ID
    prefix before decoding a requested value, rather than loading an oracle map.
    """
    ids = list(material_ids)
    wanted = set(ids)
    if len(wanted) != len(ids) or not wanted <= set(allowed_ids):
        raise ValueError(f"Unauthorized or duplicate label access: {role}")
    if commit is not None and not Path(commit).exists():
        raise ValueError("Label access requires an already serialized decision/prediction commit")
    started = now()
    result = {}
    with ORACLE.open("r", encoding="utf-8", newline="") as stream:
        header = stream.readline().strip()
        if header != "material_id," + TARGET:
            raise ValueError("Unexpected oracle schema")
        for line in stream:
            mid, separator, opaque_value = line.rstrip("\r\n").partition(",")
            if mid in wanted:
                if not separator or mid in result:
                    raise ValueError(f"Malformed/duplicate requested oracle row {mid}")
                value = float(opaque_value)
                if not math.isfinite(value):
                    raise ValueError(f"Nonfinite authorized label {mid}")
                result[mid] = value
    if set(result) != wanted:
        raise ValueError(f"Oracle missing authorized IDs for {role}")
    append(access_log, {
        "utc_started": started, "utc_complete": now(), "role": role,
        "material_ids": ids, "count": len(ids), "ids_sha256": canonical_sha(ids),
        "authorization_partition_size": len(set(allowed_ids)),
        "prior_commit_path": str(Path(commit).relative_to(ROOT)) if commit else None,
        "prior_commit_sha256": sha256(commit) if commit else None,
        "unrequested_numeric_values_decoded": 0,
    })
    return np.asarray([result[mid] for mid in ids], dtype=np.float64)


def dump_bundle(path, bundle):
    if path.exists():
        raise FileExistsError(f"Model checkpoint already exists: {path}")
    temporary = path.with_suffix(path.suffix + ".partial")
    joblib.dump(bundle, temporary, compress=3)
    temporary.replace(path)


def save_predictions(path, ids, bundle, X, stage):
    if path.exists():
        raise FileExistsError(f"Prediction file already exists: {path}")
    mean, std, radius = research_models.predict_bundle(bundle, X)
    np.savez_compressed(path, material_ids=np.asarray(ids), mean=mean, std=std, radius=radius)
    commit = {
        "created_at_utc": now(), "stage": stage, "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path), "material_ids_sha256": canonical_sha(list(ids)),
        "rows": len(ids), "oracle_labels_in_file": False,
        "model_training_ids_sha256": canonical_sha(bundle["train_ids"]),
    }
    write_json(path.with_suffix(".commit.json"), commit, exclusive=True)
    return mean, std, radius


def fit_bundle(X, y, train_ids, cal_X, cal_y, cal_ids, round_index, protocol, normalization, provenance, audit_path):
    start = time.perf_counter()
    started = now()
    members, bootstrap_audit = research_models.fit_ensemble(
        X, y, SEED, round_index,
        estimator_kwargs=protocol["ensemble"]["estimator_kwargs"],
        members=protocol["ensemble"]["members"],
    )
    calibration = research_models.calibrate_members(members, cal_X, cal_y)
    bundle = {
        "schema_version": 1, "members": members, "calibration": calibration,
        "normalization": normalization, "train_ids": list(train_ids),
        "calibration_ids": list(cal_ids), "paired_seed": SEED,
        "round_index": round_index, "feature_names": provenance["feature_names"],
        "provenance": {key: value for key, value in provenance.items() if key != "feature_names"},
        "fitted_at_utc": now(),
    }
    audit = {
        "started_at_utc": started, "completed_at_utc": now(),
        "fit_calibration_seconds": time.perf_counter()-start,
        "paired_seed": SEED, "round_index": round_index,
        "training_ids": list(train_ids), "training_ids_sha256": canonical_sha(list(train_ids)),
        "calibration_ids": list(cal_ids), "calibration": calibration,
        "members": bootstrap_audit,
        "normalization_refitted": False, "estimator_kwargs": protocol["ensemble"]["estimator_kwargs"],
        "provenance": {key: value for key, value in provenance.items() if key != "feature_names"},
    }
    write_json(audit_path, audit, exclusive=True)
    log(f"fit/calibrate round={round_index} rows={len(train_ids)} seconds={audit['fit_calibration_seconds']:.3f} q={calibration['q']:.6f}")
    return bundle, audit


def initial_snapshot(protocol, split, all_X, ids_to_position, provenance, resume):
    path = MODEL_ROOT / f"initial_paired_seed_{SEED}.joblib"
    marker = MODEL_ROOT / f"initial_paired_seed_{SEED}.manifest.json"
    train_ids, cal_ids = split["train"], split["calibration"]
    if marker.exists():
        if not resume:
            raise FileExistsError("Initial snapshot exists; use --resume to load verified committed work")
        manifest = json.loads(marker.read_text(encoding="utf-8"))
        if sha256(path) != manifest["sha256"]:
            raise ValueError("Immutable fresh-selector checksum mismatch")
        if manifest["provenance"] != {key: value for key, value in provenance.items() if key != "feature_names"}:
            raise ValueError("Fresh selector provenance differs from current frozen inputs/source")
        return joblib.load(path), manifest
    if path.exists() or (MODEL_ROOT / "initial_fit_started.json").exists():
        raise RuntimeError("An incomplete initial fit exists; no automatic duplicate fit is permitted")
    write_json(MODEL_ROOT / "protocol_snapshot.json", protocol, exclusive=True)
    write_json(MODEL_ROOT / "initial_fit_started.json", {"utc": now(), "provenance": provenance}, exclusive=True)
    train_X = all_X[[ids_to_position[mid] for mid in train_ids]]
    cal_X = all_X[[ids_to_position[mid] for mid in cal_ids]]
    train_y = read_authorized_labels(train_ids, train_ids, "initial_training", RUN / "label_access.jsonl")
    cal_y = read_authorized_labels(cal_ids, cal_ids, "fixed_calibration", RUN / "label_access.jsonl")
    normalization = acquisition.fit_diversity_normalization(train_X)
    bundle, audit = fit_bundle(train_X, train_y, train_ids, cal_X, cal_y, cal_ids, 0, protocol, normalization, provenance, LOG_ROOT / "initial_fit_audit.json")
    bundle["initial_training_diversity_features"] = acquisition.transform_diversity(train_X, normalization)
    bundle["initial_training_labels"] = train_y
    bundle["calibration_labels"] = cal_y
    bundle["immutable_fresh_selector"] = False
    bundle["immutable_paired_initial_snapshot"] = True
    dump_bundle(path, bundle)
    manifest = {
        "status": "committed_before_any_pool_query", "completed_at_utc": now(),
        "path": str(path.relative_to(ROOT)), "sha256": sha256(path),
        "paired_seed": SEED, "train_ids": train_ids, "calibration_ids": cal_ids,
        "role": "paired replay initial model only; never a fresh selector",
        "initial_training_labels": len(train_ids), "calibration_labels": len(cal_ids),
        "pool_queries_revealed_before_snapshot": 0, "evaluation_labels_read_before_snapshot": 0,
        "calibration": bundle["calibration"], "fit_calibration_seconds": audit["fit_calibration_seconds"],
        "provenance": {key: value for key, value in provenance.items() if key != "feature_names"},
        "package_versions": {name: importlib.metadata.version(name) for name in ("numpy", "scikit-learn", "joblib", "scipy")},
    }
    write_json(marker, manifest, exclusive=True)
    log(f"IMMUTABLE_PAIRED_INITIAL_READY path={path.relative_to(ROOT)} sha256={manifest['sha256']}")
    return bundle, manifest


def evaluate_all():
    """Isolated evaluator: executed only once replay decisions/fits are complete."""
    split = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))["material_ids"]
    evaluation_ids = split["unused"]
    complete = RUN / "all_policy_queries_complete.json"
    if not complete.exists():
        raise ValueError("Evaluator cannot run before all policy queries and fits complete")
    outputs = [RUN / "initial_eval_predictions.npz"]
    outputs.extend(RUN / policy / f"round_{round_index:02d}" / "evaluation_predictions.npz" for policy in acquisition.POLICIES for round_index in range(1, 6))
    # Verify every immutable prediction exists before decoding any evaluation label.
    for path in outputs:
        commit = json.loads(path.with_suffix(".commit.json").read_text(encoding="utf-8"))
        if sha256(path) != commit["sha256"]:
            raise ValueError(f"Evaluator prediction checksum mismatch: {path}")
    y = read_authorized_labels(evaluation_ids, evaluation_ids, "isolated_evaluator_unused_partition", RUN / "evaluation_label_access.jsonl", commit=complete)
    metrics = []
    for path in outputs:
        with np.load(path, allow_pickle=False) as values:
            if values["material_ids"].tolist() != evaluation_ids:
                raise ValueError("Evaluator population order changed")
            error = np.abs(y-values["mean"])
            correlation = float(spearmanr(values["std"], error).statistic)
            row = {
                "prediction_path": str(path.relative_to(ROOT)), "prediction_sha256": sha256(path),
                "evaluated_at_utc": now(), "n": len(y),
                "MAE_eV_atom": float(error.mean()),
                "RMSE_eV_atom": float(np.sqrt(np.mean(error**2))),
                "Spearman_disagreement_absolute_error": correlation if math.isfinite(correlation) else None,
                "interval_90_empirical_coverage": float(np.mean(error <= values["radius"])),
                "mean_interval_width_eV_atom": float(2*values["radius"].mean()),
                "labels_returned_to_learner": 0,
            }
        write_json(path.with_suffix(".metrics.json"), row, exclusive=True)
        metrics.append(row)
    write_json(RUN / "evaluation_summary.json", {"status": "completed", "evaluation_ids": evaluation_ids, "evaluated_predictions": metrics, "evaluated_at_utc": now(), "policy_decisions_finished_before_label_access": True}, exclusive=True)
    return 0


def run_replay(protocol, split, initial, all_X, ids_to_position, provenance, resume):
    train_ids, cal_ids, pool_ids, eval_ids = (split[key] for key in ("train", "calibration", "pool", "unused"))
    train_X = all_X[[ids_to_position[mid] for mid in train_ids]]
    cal_X = all_X[[ids_to_position[mid] for mid in cal_ids]]
    eval_X = all_X[[ids_to_position[mid] for mid in eval_ids]]
    train_y = initial["initial_training_labels"]
    cal_y = initial["calibration_labels"]
    initial_eval = RUN / "initial_eval_predictions.npz"
    if not initial_eval.exists():
        save_predictions(initial_eval, eval_ids, initial, eval_X, "initial_shared")
    query_summaries = []
    for policy in acquisition.POLICIES:
        log(f"policy start {policy}")
        queried_ids, queried_labels, reveals = [], [], []
        bundle = initial
        for round_index in range(1, 6):
            check_numerical_stop(protocol)
            directory = RUN / policy / f"round_{round_index:02d}"
            completion = directory / "complete.json"
            if completion.exists():
                if not resume:
                    raise RuntimeError("Committed replay round exists; explicit --resume required")
                done = json.loads(completion.read_text(encoding="utf-8"))
                model_path = ROOT / done["model_path"]
                if sha256(model_path) != done["model_sha256"]:
                    raise ValueError("Committed adapted model checksum mismatch")
                for filename, key in (("decision.json", "decision_sha256"), ("reveals.json", "reveal_sha256"), ("fit_audit.json", "fit_audit_sha256")):
                    if sha256(directory / filename) != done[key]:
                        raise ValueError(f"Committed replay evidence checksum mismatch: {filename}")
                reveal = json.loads((directory / "reveals.json").read_text(encoding="utf-8"))
                if set(reveal["material_ids"]) & set(queried_ids) or not set(reveal["material_ids"]) <= set(pool_ids):
                    raise ValueError("Committed replay queries violate the frozen pool boundary")
                queried_ids.extend(reveal["material_ids"])
                queried_labels.extend(reveal["labels_eV_atom"])
                reveals.extend(reveal["records"])
                bundle = joblib.load(model_path)
                continue
            if directory.exists() and any(directory.iterdir()):
                raise RuntimeError(f"Incomplete round evidence exists: {directory}; no silent duplicate query/refit allowed")
            directory.mkdir(parents=True, exist_ok=True)
            remaining_ids = [mid for mid in pool_ids if mid not in set(queried_ids)]
            remaining_X = all_X[[ids_to_position[mid] for mid in remaining_ids]]
            remaining_D = acquisition.transform_diversity(remaining_X, initial["normalization"])
            known_ids = train_ids + queried_ids
            known_D = acquisition.transform_diversity(all_X[[ids_to_position[mid] for mid in known_ids]], initial["normalization"])
            with threadpool_limits(limits=2):
                distance = acquisition.distances_to_labeled(remaining_D, known_D)
            pool_prediction_path = directory / "pool_predictions_before_reveal.npz"
            mean, std, radius = save_predictions(pool_prediction_path, remaining_ids, bundle, remaining_X, f"{policy}_round_{round_index}_before_reveal")
            rng = np.random.default_rng(np.random.SeedSequence([SEED, round_index, 101]))
            selected, decisions = acquisition.select_batch(policy, remaining_ids, mean, radius, remaining_D, distance, rng, batch_size=10)
            chosen = [remaining_ids[int(index)] for index in selected]
            if len(set(chosen)) != 10 or set(chosen) & set(queried_ids):
                raise ValueError("Duplicate replay query")
            decision_path = directory / "decision.json"
            decision = {
                "committed_at_utc": now(), "paired_seed": SEED, "policy": policy,
                "round_index": round_index, "material_ids": chosen, "decisions": decisions,
                "pool_prediction_sha256": sha256(pool_prediction_path),
                "model_training_ids_sha256": canonical_sha(bundle["train_ids"]),
                "known_ids_sha256": canonical_sha(known_ids),
                "random_seed_sequence": [SEED, round_index, 101],
                "oracle_labels_supplied_to_acquisition": 0,
            }
            write_json(decision_path, decision, exclusive=True)
            labels = read_authorized_labels(chosen, set(pool_ids)-set(queried_ids), f"{policy}_round_{round_index}_query", RUN / "label_access.jsonl", commit=decision_path)
            reveal = {
                "revealed_at_utc": now(), "policy": policy, "round_index": round_index,
                "material_ids": chosen, "labels_eV_atom": labels.tolist(),
                "prior_decision_sha256": sha256(decision_path),
                "records": [{"material_id": mid, "label_eV_atom": float(value), "round_index": round_index, "policy": policy} for mid, value in zip(chosen, labels, strict=True)],
            }
            write_json(directory / "reveals.json", reveal, exclusive=True)
            queried_ids.extend(chosen)
            queried_labels.extend(labels.tolist())
            reveals.extend(reveal["records"])
            current_ids = train_ids + queried_ids
            if set(current_ids) & (set(cal_ids) | set(eval_ids) | set(split["fresh_reserved"])):
                raise ValueError("Training/calibration/evaluation/reserve label boundary violation")
            current_X = all_X[[ids_to_position[mid] for mid in current_ids]]
            current_y = np.concatenate([train_y, np.asarray(queried_labels)])
            write_json(directory / "fit_started.json", {"utc": now(), "training_ids": current_ids, "training_ids_sha256": canonical_sha(current_ids), "prior_reveal_sha256": sha256(directory / "reveals.json")}, exclusive=True)
            bundle, fit_audit = fit_bundle(current_X, current_y, current_ids, cal_X, cal_y, cal_ids, round_index, protocol, initial["normalization"], provenance, directory / "fit_audit.json")
            model_path = directory / "adapted_model.joblib"
            dump_bundle(model_path, bundle)
            save_predictions(directory / "evaluation_predictions.npz", eval_ids, bundle, eval_X, f"{policy}_round_{round_index}_after_refit")
            write_json(completion, {
                "completed_at_utc": now(), "policy": policy, "round_index": round_index,
                "cumulative_queries": len(queried_ids), "training_rows": len(current_ids),
                "model_path": str(model_path.relative_to(ROOT)), "model_sha256": sha256(model_path),
                "decision_sha256": sha256(decision_path), "reveal_sha256": sha256(directory / "reveals.json"),
                "fit_audit_sha256": sha256(directory / "fit_audit.json"),
                "fit_calibration_seconds": fit_audit["fit_calibration_seconds"],
            }, exclusive=True)
            log(f"policy={policy} round={round_index} complete cumulative_queries={len(queried_ids)}")
        if len(queried_ids) != 50 or len(set(queried_ids)) != 50:
            raise ValueError("Policy query budget not exactly50")
        query_summaries.append({"policy": policy, "queried_ids": queried_ids, "queried_labels": queried_labels, "reveals": reveals})
    complete_path = RUN / "all_policy_queries_complete.json"
    if not complete_path.exists():
        write_json(complete_path, {"status": "complete", "completed_at_utc": now(), "policies": list(acquisition.POLICIES), "queries_per_policy": 50, "total_policy_queries": 250, "evaluator_labels_read_so_far": 0}, exclusive=True)
    # Model/scoring decisions are all finished before any unused-partition labels
    # enter this isolated subprocess. No labels or metrics return during fitting.
    if not (RUN / "evaluation_summary.json").exists():
        command = [sys.executable, str(Path(__file__).resolve()), "--seed", str(SEED), "--evaluate-only"]
        with (LOG_ROOT / "evaluation.log").open("w", encoding="utf-8") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError("Isolated evaluator failed; inspect model_logs/evaluation.log")
    with (ROOT / "artifacts" / "phase2" / "features" / "row_metadata.csv").open(encoding="utf-8", newline="") as stream:
        chemical_systems = {row["material_id"]: row["chemical_system"] for row in csv.DictReader(stream)}
    policy_results = []
    for data in query_summaries:
        values = np.asarray(data["queried_labels"])
        curve = []
        for count in (10, 20, 30, 40, 50):
            curve.append({"queries": count, "near_stable_hits": int(np.sum(values[:count] <= .05)), "reference_hull_hits": int(np.sum(values[:count] <= 0)), "chemical_system_coverage": len({chemical_systems[mid] for mid in data["queried_ids"][:count]})})
        policy_results.append({"policy": data["policy"], "queries": 50, "near_stable_hits": int(np.sum(values <= .05)), "precision_at_50": float(np.mean(values <= .05)), "reference_hull_hits": int(np.sum(values <= 0)), "curve": curve, "queried_ids": data["queried_ids"]})
    write_json(RUN / "summary.json", {"status": "completed", "completed_at_utc": now(), "paired_seed": SEED, "policies": policy_results, "total_policy_queries": 250, "initial_shared_label_count": 2400, "evaluation_rows": len(eval_ids), "evaluator_metric_feedback_to_decisions": False, "provenance": {key: value for key, value in provenance.items() if key != "feature_names"}}, exclusive=not resume)
    log("ALL_FIVE_POLICIES_COMPLETE queries=250 evaluator_population=3418")


def check_numerical_stop(protocol):
    stop = datetime.fromisoformat(protocol["qe"]["numerical_stop_utc"])
    if datetime.now(timezone.utc) >= stop:
        raise RuntimeError("Frozen numerical hard stop reached; no further fitting or selection")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, choices=(20261023, 20261024, 20261025, 20261026))
    parser.add_argument("--initial-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args()
    global SEED, MODEL_ROOT, LOG_ROOT, RUN, SPLIT_FILE
    SEED = args.seed
    MODEL_ROOT = ROOT / "artifacts" / "phase4" / "models" / f"seed_{SEED}"
    LOG_ROOT = ROOT / "artifacts" / "phase4" / "model_logs" / f"seed_{SEED}"
    RUN = ROOT / "artifacts" / "phase4" / "replay" / f"seed_{SEED}"
    SPLIT_FILE = ROOT / "artifacts" / "phase2" / "splits" / f"seed_{SEED}.json"
    if args.evaluate_only:
        return evaluate_all()
    for path in (MODEL_ROOT, LOG_ROOT, RUN):
        path.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    check_numerical_stop(protocol)
    if SEED not in protocol["seeds"] or SEED == protocol["fresh_selector_seed"] or protocol["acquisition_implementation_sha256"] != sha256(ROOT / "research_acquisition.py"):
        raise ValueError("Frozen protocol seed/acquisition source mismatch")
    if protocol["ensemble"]["estimator_kwargs"]["n_jobs"] != 2:
        raise ValueError("Frozen two-thread estimator setting differs")
    split = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))["material_ids"]
    if [len(split[key]) for key in ("train", "calibration", "pool", "unused")] != [2000, 400, 2000, 3418]:
        raise ValueError("Frozen split population differs")
    joined = [mid for values in split.values() for mid in values]
    if len(joined) != len(set(joined)):
        raise ValueError("Split IDs overlap")
    feature_manifest = json.loads(FEATURE_MANIFEST.read_text(encoding="utf-8"))
    if sha256(FEATURE_FILE) != feature_manifest["outputs"]["features.npz"]["sha256"]:
        raise ValueError("Frozen feature archive checksum mismatch")
    if sha256(ROOT / "research_features.py") != feature_manifest["implementation"]["module_sha256"]:
        raise ValueError("Shared descriptor source differs from the frozen feature archive")
    with np.load(FEATURE_FILE, allow_pickle=False) as values:
        all_X = values["X"]
        material_ids = values["material_ids"].tolist()
        feature_names = values["feature_names"].tolist()
    ids_to_position = {mid: index for index, mid in enumerate(material_ids)}
    if set(joined) != set(material_ids) or not np.isfinite(all_X).all():
        raise ValueError("Feature/split population mismatch or nonfinite values")
    fresh_path = ROOT / "artifacts" / "phase3" / "models" / "fresh_selector_seed_20261022.joblib"
    fresh_manifest = json.loads(fresh_path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    if sha256(fresh_path) != fresh_manifest["sha256"]:
        raise ValueError("Original fresh selector was changed")
    provenance = {
        "original_fresh_selector_sha256": fresh_manifest["sha256"],
        "original_fresh_selector_used_for_fresh_generation": True,
        "this_seed_initial_model_used_for_fresh_generation": False,
        "protocol_sha256": sha256(PROTOCOL), "feature_archive_sha256": sha256(FEATURE_FILE),
        "feature_manifest_sha256": sha256(FEATURE_MANIFEST), "split_sha256": sha256(SPLIT_FILE),
        "feature_source_sha256": feature_manifest["implementation"]["module_sha256"],
        "oracle_file_sha256": sha256(ORACLE),
        "acquisition_source_sha256": sha256(ROOT / "research_acquisition.py"),
        "models_source_sha256": sha256(ROOT / "research_models.py"),
        "replay_source_sha256": sha256(Path(__file__)), "feature_names": feature_names,
    }
    start = time.perf_counter()
    initial, manifest = initial_snapshot(protocol, split, all_X, ids_to_position, provenance, args.resume)
    if args.initial_only:
        log(f"initial-only complete seconds={time.perf_counter()-start:.3f}")
        return 0
    run_replay(protocol, split, initial, all_X, ids_to_position, provenance, args.resume)
    if sha256(ROOT / manifest["path"]) != manifest["sha256"]:
        raise ValueError("Fresh selector changed during replay")
    if sha256(fresh_path) != fresh_manifest["sha256"]:
        raise ValueError("Original fresh selector changed during replay")
    write_json(RUN / "execution_cost.json", {
        "paired_seed": SEED, "completed_at_utc": now(),
        "wall_seconds_in_this_invocation": time.perf_counter()-start,
        "replay_source_sha256": sha256(Path(__file__)),
        "original_fresh_selector_sha256": fresh_manifest["sha256"],
        "original_fresh_selector_unchanged": True,
        "estimator_threads": 2,
        "numerical_stop_utc": protocol["qe"]["numerical_stop_utc"],
    }, exclusive=True)
    log(f"full run complete elapsed_seconds={time.perf_counter()-start:.3f}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exception:
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        append(LOG_ROOT / "errors.jsonl", {"utc": now(), "exception": type(exception).__name__, "message": str(exception), "traceback": traceback.format_exc()})
        log(f"FAILED {type(exception).__name__}: {exception}")
        raise
