"""Independent artifact audit; no oracle file access, fitting or new queries."""
import os
for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[name] = "2"
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import joblib
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import research_acquisition as acquisition
import research_models

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--seed", type=int, required=True, choices=range(20261022, 20261027))
SEED = parser.parse_args().seed
PHASE = 3 if SEED == 20261022 else 4
RUN = ROOT / f"artifacts/phase{PHASE}/replay/seed_{SEED}"
MODELS = ROOT / "artifacts/phase3/models" if PHASE == 3 else ROOT / f"artifacts/phase4/models/seed_{SEED}"
LOGS = ROOT / "artifacts/phase3/model_logs" if PHASE == 3 else ROOT / f"artifacts/phase4/model_logs/seed_{SEED}"
AUDITS = ROOT / "artifacts/phase4/replay/audits"
AUDITS.mkdir(parents=True, exist_ok=True)

def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def utc(value):
    return datetime.fromisoformat(value)

def assert_calibration_equal(expected, actual):
    assert expected.keys() == actual.keys()
    for key in expected:
        if isinstance(expected[key], float):
            assert np.isclose(expected[key], actual[key], rtol=1e-12, atol=1e-12), (key, expected[key], actual[key])
        else:
            assert expected[key] == actual[key], (key, expected[key], actual[key])

split = read(ROOT / f"artifacts/phase2/splits/seed_{SEED}.json")["material_ids"]
features = np.load(ROOT / "artifacts/phase2/features/features.npz", allow_pickle=False)
X = features["X"]
index = {mid: i for i, mid in enumerate(features["material_ids"].tolist())}
initial_path = MODELS / ("fresh_selector_seed_20261022.joblib" if PHASE == 3 else f"initial_paired_seed_{SEED}.joblib")
initial_manifest = read(initial_path.with_suffix(".manifest.json"))
assert sha(initial_path) == initial_manifest["sha256"]
protocol = read(ROOT / "config/phase2_protocol.json")
assert initial_manifest["provenance"]["protocol_sha256"] == sha(ROOT / "config/phase2_protocol.json")
assert initial_manifest["provenance"]["split_sha256"] == sha(ROOT / f"artifacts/phase2/splits/seed_{SEED}.json")
assert protocol["acquisition_implementation_sha256"] == sha(ROOT / "research_acquisition.py")
assert initial_manifest["provenance"]["models_source_sha256"] == sha(ROOT / "research_models.py")
assert initial_manifest["pool_queries_revealed_before_snapshot"] == 0
assert initial_manifest["evaluation_labels_read_before_snapshot"] == 0
initial = joblib.load(initial_path)
assert initial["paired_seed"] == SEED
assert initial["train_ids"] == split["train"]
assert initial["calibration_ids"] == split["calibration"]
if PHASE == 4:
    assert not initial["immutable_fresh_selector"]
    assert initial["immutable_paired_initial_snapshot"]
calibration_X = X[[index[mid] for mid in split["calibration"]]]
recomputed_initial_cal = research_models.calibrate_members(initial["members"], calibration_X, initial["calibration_labels"])
assert_calibration_equal(recomputed_initial_cal, initial["calibration"])
initial_evaluation = np.load(RUN / "initial_eval_predictions.npz", allow_pickle=False)
assert initial_evaluation["material_ids"].tolist() == split["unused"]
assert sha(RUN / "initial_eval_predictions.npz") == read(RUN / "initial_eval_predictions.commit.json")["sha256"]
bootstrap_count = 0
normalization = initial["normalization"]
normalization_check = acquisition.fit_diversity_normalization(X[[index[mid] for mid in split["train"]]])
assert all(np.array_equal(normalization[k], normalization_check[k]) for k in normalization)
access = [json.loads(line) for line in (RUN / "label_access.jsonl").read_text().splitlines()]
pool_access = {row["role"]: row for row in access if row["role"].endswith("_query")}
assert len(access) == 27 and len(pool_access) == 25
assert sum(row["count"] for row in pool_access.values()) == 250
assert all(row["unrequested_numeric_values_decoded"] == 0 for row in access)
assert min(utc(row["utc_started"]) for row in pool_access.values()) > utc(initial_manifest["completed_at_utc"])
journal = []
initial_fit = read(LOGS / "initial_fit_audit.json")
fit_seconds = initial_fit["fit_calibration_seconds"]
verified_models = 1
decision_replays = 0
for member in initial_fit["members"]:
    state = np.random.SeedSequence([SEED, 0, member["member_index"], 11]).generate_state(2, dtype=np.uint32)
    assert [int(x) for x in state] == [member["bootstrap_seed"], member["estimator_seed"]]
    planned = np.random.default_rng(int(state[0])).integers(0, 2000, size=2000)
    assert np.array_equal(planned, member["bootstrap_indices"])
    bootstrap_count += 1
for policy in acquisition.POLICIES:
    queried = []
    for round_index in range(1, 6):
        directory = RUN / policy / f"round_{round_index:02d}"
        complete = read(directory / "complete.json")
        for filename, key in (("decision.json", "decision_sha256"), ("reveals.json", "reveal_sha256"), ("fit_audit.json", "fit_audit_sha256"), ("adapted_model.joblib", "model_sha256")):
            assert sha(directory / filename) == complete[key], (policy, round_index, filename)
        decision, reveal, fit = [read(directory / name) for name in ("decision.json", "reveals.json", "fit_audit.json")]
        pool_commit = read(directory / "pool_predictions_before_reveal.commit.json")
        assert sha(directory / "pool_predictions_before_reveal.npz") == pool_commit["sha256"] == decision["pool_prediction_sha256"]
        expected_remaining = [mid for mid in split["pool"] if mid not in set(queried)]
        before = np.load(directory / "pool_predictions_before_reveal.npz", allow_pickle=False)
        assert before["material_ids"].tolist() == expected_remaining
        remaining_D = acquisition.transform_diversity(X[[index[mid] for mid in expected_remaining]], normalization)
        known_D = acquisition.transform_diversity(X[[index[mid] for mid in split["train"] + queried]], normalization)
        with threadpool_limits(limits=2):
            distances = acquisition.distances_to_labeled(remaining_D, known_D)
        selected, recomputed = acquisition.select_batch(
            policy, expected_remaining, before["mean"], before["radius"], remaining_D,
            distances, np.random.default_rng(np.random.SeedSequence([SEED, round_index, 101])),
        )
        assert [expected_remaining[int(i)] for i in selected] == decision["material_ids"]
        assert [row["material_id"] for row in recomputed] == [row["material_id"] for row in decision["decisions"]]
        for expected, saved in zip(recomputed, decision["decisions"], strict=True):
            assert expected.keys() == saved.keys()
            for key in expected:
                if isinstance(expected[key], float):
                    assert np.isclose(expected[key], saved[key], rtol=1e-12, atol=1e-12), (policy, round_index, key)
                else:
                    assert expected[key] == saved[key], (policy, round_index, key)
        decision_replays += 1
        assert decision["material_ids"] == reveal["material_ids"]
        assert len(set(reveal["material_ids"])) == 10
        assert not set(queried) & set(reveal["material_ids"])
        assert utc(pool_commit["created_at_utc"]) <= utc(decision["committed_at_utc"])
        entry = pool_access[f"{policy}_round_{round_index}_query"]
        assert entry["material_ids"] == reveal["material_ids"]
        assert utc(decision["committed_at_utc"]) <= utc(entry["utc_started"]) <= utc(entry["utc_complete"]) <= utc(reveal["revealed_at_utc"])
        assert entry["prior_commit_sha256"] == sha(directory / "decision.json") == reveal["prior_decision_sha256"]
        for position, (mid, label, info) in enumerate(zip(reveal["material_ids"], reveal["labels_eV_atom"], decision["decisions"], strict=True)):
            journal.append({
                "seed": SEED, "policy": policy, "round": round_index,
                "query_number": len(queried) + position + 1, "material_id": mid,
                "label_eV_atom": label, "role": info["role"], "score": info["score"],
                "predicted_mean_eV_atom": info["predicted_mean_eV_atom"],
                "calibrated_radius_eV_atom": info["calibrated_radius_eV_atom"],
                "diversity_at_selection": info["diversity_distance_at_selection"],
                "decision_utc": decision["committed_at_utc"], "reveal_utc": reveal["revealed_at_utc"],
                "decision_sha256": sha(directory / "decision.json"), "reveal_sha256": sha(directory / "reveals.json"),
            })
        queried.extend(reveal["material_ids"])
        assert fit["training_ids"] == split["train"] + queried
        assert utc(reveal["revealed_at_utc"]) <= utc(fit["started_at_utc"]) <= utc(fit["completed_at_utc"])
        assert fit["estimator_kwargs"] == protocol["ensemble"]["estimator_kwargs"]
        assert decision["oracle_labels_supplied_to_acquisition"] == 0
        assert fit["calibration_ids"] == split["calibration"]
        assert not set(fit["training_ids"]) & (set(split["calibration"]) | set(split["unused"]) | set(split["fresh_reserved"]))
        for member in fit["members"]:
            state = np.random.SeedSequence([SEED, round_index, member["member_index"], 11]).generate_state(2, dtype=np.uint32)
            assert [int(x) for x in state] == [member["bootstrap_seed"], member["estimator_seed"]]
            expected_bootstrap = np.random.default_rng(int(state[0])).integers(0, len(fit["training_ids"]), size=len(fit["training_ids"]))
            assert np.array_equal(expected_bootstrap, member["bootstrap_indices"] )
            bootstrap_count += 1
        model = joblib.load(directory / "adapted_model.joblib")
        assert model["train_ids"] == fit["training_ids"]
        assert model["calibration_ids"] == split["calibration"]
        assert all(np.array_equal(model["normalization"][key], normalization[key]) for key in normalization)
        assert all(len(member.estimators_) == 128 and member.n_jobs == 2 and member.n_features_in_ == 408 and member.min_samples_leaf == 2 for member in model["members"])
        assert len(model["members"]) == 5
        assert_calibration_equal(research_models.calibrate_members(model["members"], calibration_X, initial["calibration_labels"]), model["calibration"])
        assert model["calibration"] == fit["calibration"]
        verified_models += 1
        evaluation_commit = read(directory / "evaluation_predictions.commit.json")
        assert sha(directory / "evaluation_predictions.npz") == evaluation_commit["sha256"]
        evaluation = np.load(directory / "evaluation_predictions.npz", allow_pickle=False)
        assert evaluation["material_ids"].tolist() == split["unused"]
        assert all(np.isfinite(evaluation[key]).all() for key in ("mean", "std", "radius"))
        fit_seconds += fit["fit_calibration_seconds"]
    assert len(queried) == len(set(queried)) == 50
evaluation_access = [json.loads(line) for line in (RUN / "evaluation_label_access.jsonl").read_text().splitlines()]
assert len(evaluation_access) == 1
assert evaluation_access[0]["material_ids"] == split["unused"]
assert evaluation_access[0]["count"] == 3418
all_complete = read(RUN / "all_policy_queries_complete.json")
assert utc(evaluation_access[0]["utc_started"]) >= utc(all_complete["completed_at_utc"])
evaluation_summary = read(RUN / "evaluation_summary.json")
assert len(evaluation_summary["evaluated_predictions"]) == 26
assert all(item["labels_returned_to_learner"] == 0 for item in evaluation_summary["evaluated_predictions"])
assert sha(initial_path) == initial_manifest["sha256"]
assert len(journal) == 250
if PHASE == 4:
    with (RUN / "query_journal.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(journal[0]))
        writer.writeheader()
        writer.writerows(journal)
else:
    with (RUN / "query_journal.csv").open(encoding="utf-8", newline="") as stream:
        existing_journal = list(csv.DictReader(stream))
    assert len(existing_journal) == 250
    for saved, reproduced in zip(existing_journal, journal, strict=True):
        assert saved["material_id"] == reproduced["material_id"]
        assert saved["decision_sha256"] == reproduced["decision_sha256"]
        assert saved["reveal_sha256"] == reproduced["reveal_sha256"]
summary = read(RUN / "summary.json")
assert summary["total_policy_queries"] == 250
for policy_summary in summary["policies"]:
    rows = [row for row in journal if row["policy"] == policy_summary["policy"]]
    labels = np.asarray([row["label_eV_atom"] for row in rows])
    assert policy_summary["near_stable_hits"] == int(np.sum(labels <= .05))
    assert policy_summary["reference_hull_hits"] == int(np.sum(labels <= 0))
    assert policy_summary["queried_ids"] == [row["material_id"] for row in rows]
    for point in policy_summary["curve"]:
        assert point["near_stable_hits"] == int(np.sum(labels[:point["queries"]] <= .05))
        assert point["reference_hull_hits"] == int(np.sum(labels[:point["queries"]] <= 0))
fresh = ROOT / "artifacts/phase3/models/fresh_selector_seed_20261022.joblib"
fresh_manifest = read(fresh.with_suffix(".manifest.json"))
assert sha(fresh) == fresh_manifest["sha256"]
assert bootstrap_count == 130
report = {
    "status": "passed", "paired_seed": SEED, "phase": PHASE, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    "verified_model_snapshots": verified_models, "decisions_replayed_from_pre_reveal_predictions": decision_replays,
    "policy_queries": len(journal), "policies": 5, "unique_queries_per_policy": 50,
    "recomputed_bootstrap_plans": 125, "recomputed_initial_bootstrap_plans": 5,
    "recomputed_calibrations": 26, "all_replayed_scores_verified": True,
    "floating_reproduction_tolerance_rtol_and_atol": 1e-12,
    "all_training_ids_initial_plus_only_own_policy_queries": True,
    "all_calibration_ids_fixed": True, "all_diversity_normalizers_frozen_initial_only": True,
    "all_decisions_serialized_before_reveals": True,
    "all_evaluator_labels_read_after_all_policy_queries_complete": True,
    "all_models_and_decision_reveal_fit_hashes_valid": True,
    "fixed_evaluation_rows": 3418, "immutable_evaluation_prediction_sets": 26,
    "initial_snapshot_sha256": initial_manifest["sha256"], "initial_snapshot_unchanged": True,
    "original_fresh_snapshot_sha256": fresh_manifest["sha256"], "original_fresh_snapshot_unchanged": True,
    "total_initial_and_adapted_fit_calibration_seconds": fit_seconds,
    "query_journal_sha256": sha(RUN / "query_journal.csv"),
    "audit_source_sha256": sha(__file__), "oracle_file_read_by_auditor": False,
}
(AUDITS / f"seed_{SEED}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if PHASE == 4:
    (RUN / "audit_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(report, sort_keys=True))
