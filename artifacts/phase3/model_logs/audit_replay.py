"""Independent artifact audit; no oracle file access, fitting or new queries."""
import os
for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[name] = "2"
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import joblib
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import research_acquisition as acquisition

RUN = ROOT / "artifacts/phase3/replay/seed_20261022"
MODELS = ROOT / "artifacts/phase3/models"
SEED = 20261022

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

split = read(ROOT / "artifacts/phase2/splits/seed_20261022.json")["material_ids"]
features = np.load(ROOT / "artifacts/phase2/features/features.npz", allow_pickle=False)
X = features["X"]
index = {mid: i for i, mid in enumerate(features["material_ids"].tolist())}
initial_path = MODELS / "fresh_selector_seed_20261022.joblib"
initial_manifest = read(initial_path.with_suffix(".manifest.json"))
assert sha(initial_path) == initial_manifest["sha256"]
initial = joblib.load(initial_path)
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
fit_seconds = read(ROOT / "artifacts/phase3/model_logs/initial_fit_audit.json")["fit_calibration_seconds"]
verified_models = 1
decision_replays = 0
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
        assert fit["calibration_ids"] == split["calibration"]
        assert not set(fit["training_ids"]) & (set(split["calibration"]) | set(split["unused"]) | set(split["fresh_reserved"]))
        for member in fit["members"]:
            state = np.random.SeedSequence([SEED, round_index, member["member_index"], 11]).generate_state(2, dtype=np.uint32)
            assert [int(x) for x in state] == [member["bootstrap_seed"], member["estimator_seed"]]
            expected_bootstrap = np.random.default_rng(int(state[0])).integers(0, len(fit["training_ids"]), size=len(fit["training_ids"]))
            assert np.array_equal(expected_bootstrap, member["bootstrap_indices"])
        model = joblib.load(directory / "adapted_model.joblib")
        assert model["train_ids"] == fit["training_ids"]
        assert model["calibration_ids"] == split["calibration"]
        assert all(np.array_equal(model["normalization"][key], normalization[key]) for key in normalization)
        assert all(len(member.estimators_) == 128 and member.n_jobs == 2 and member.n_features_in_ == 408 and member.min_samples_leaf == 2 for member in model["members"])
        assert len(model["members"]) == 5
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
with (RUN / "query_journal.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(journal[0]))
    writer.writeheader()
    writer.writerows(journal)
report = {
    "status": "passed", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    "verified_model_snapshots": verified_models, "decisions_replayed_from_pre_reveal_predictions": decision_replays,
    "policy_queries": len(journal), "policies": 5, "unique_queries_per_policy": 50,
    "recomputed_bootstrap_plans": 125,
    "all_training_ids_initial_plus_only_own_policy_queries": True,
    "all_calibration_ids_fixed": True, "all_diversity_normalizers_frozen_initial_only": True,
    "all_decisions_serialized_before_reveals": True,
    "all_evaluator_labels_read_after_all_policy_queries_complete": True,
    "all_models_and_decision_reveal_fit_hashes_valid": True,
    "fixed_evaluation_rows": 3418, "immutable_evaluation_prediction_sets": 26,
    "fresh_snapshot_sha256": initial_manifest["sha256"], "fresh_snapshot_unchanged": True,
    "total_initial_and_adapted_fit_calibration_seconds": fit_seconds,
    "query_journal_sha256": sha(RUN / "query_journal.csv"),
    "audit_source_sha256": sha(__file__), "oracle_file_read_by_auditor": False,
}
(RUN / "audit_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(report, sort_keys=True))
