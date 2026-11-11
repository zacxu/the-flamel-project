"""Commit balanced random symmetry selections without launching relaxations."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase4/selection"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    destination = OUT / "symmetry_relaxation_plan.json"
    if destination.exists():
        raise RuntimeError("Random selections already committed; do not redraw after seeing energies")
    primary_path = "artifacts/phase4/generation/summary.json"
    supplementary_path = "artifacts/phase4/generation/supplementary_mgo/summary.json"
    primary, supplementary = load(primary_path), load(supplementary_path)
    protocol = load("artifacts/phase2/controls/matched_protocol.json")
    records, selected_count = [], 0
    for control_index, control in enumerate(protocol["controls"]):
        name = control["label"]
        pools = {}
        if name == "mgo_rocksalt":
            source = supplementary["arms"]
            pools = {r["arm"]: r["combined_valid_unique_representatives"] for r in source}
            scope, cap = "supplementary_primary_plus_topup_pool", 1
        else:
            source = [r for r in primary["controls"] if r["control"] == name]
            pools = {r["arm"]: r["valid_unique_representatives"] for r in source}
            scope, cap = "primary_first8_per_arm", 4
        quota = min(cap, len(pools["nontrivial"]), len(pools["p1"]))
        arms = []
        for arm_index, arm in enumerate(["nontrivial", "p1"]):
            candidates = sorted(pools[arm], key=lambda row: row["candidate_id"])
            seed_sequence = [protocol["seed"], control_index, arm_index, 404]
            rng = np.random.default_rng(np.random.SeedSequence(seed_sequence))
            indices = rng.choice(len(candidates), size=quota, replace=False).tolist() if quota else []
            selected = []
            for index in indices:
                row = candidates[int(index)]
                digest = sha(row["structure_json"])
                if digest != row["structure_sha256"]:
                    raise RuntimeError("Candidate changed after generation audit")
                selected.append({"candidate_id": row["candidate_id"], "source_structure": row["structure_json"],
                                 "source_structure_sha256": digest, "selection_index": int(index)})
            arms.append({"arm": arm, "pool_size": len(candidates), "pool_ids": [r["candidate_id"] for r in candidates],
                         "seed_sequence": seed_sequence, "selected": selected})
            selected_count += len(selected)
        records.append({"control": name, "evaluated_formula": control["evaluated_formula"],
                        "comparison_scope": scope, "quota_per_arm": quota, "arms": arms,
                        "minimum_two_unique_per_arm_achieved": all(len(pool) >= 2 for pool in pools.values()),
                        "energy_comparison_limit": "At most one paired structure in this run; descriptive, without an estimated within-arm energy distribution"})
    cached_path = "artifacts/phase3/chgnet/phase1_mgo_attempt_000/result.json"
    cached = load(cached_path)
    cached_source_matches = cached["source_structure_sha256"] == records[0]["arms"][0]["selected"][0]["source_structure_sha256"]
    record = {"frozen_utc": datetime.now(timezone.utc).isoformat(), "status": "committed_before_any_new_symmetry_relaxation",
              "selection_rule": "Seeded uniform random choice without replacement from sorted valid unique IDs; no predicted or observed energy input",
              "source_control_protocol_sha256": sha("artifacts/phase2/controls/matched_protocol.json"),
              "source_primary_summary_sha256": sha(primary_path), "source_supplementary_summary_sha256": sha(supplementary_path),
              "controls": records, "selected_structures": selected_count, "CHGNet_or_DFT_energies_used_to_select": False,
              "relaxation_jobs_executed_by_this_script": 0,
              "cache_candidate": {"candidate_id": "phase1_mgo_attempt_000", "result_path": cached_path,
                                  "result_sha256": sha(cached_path), "initial_source_matches": cached_source_matches,
                                  "converged": cached["converged"], "model_version": cached["model_version"],
                                  "reuse_condition": "Phase5 verifies identical initial source, checkpoint and the frozen unconstrained FIRE200/fmax0.05 settings; record cached compute once and keep this experimental selection",
                                  "prior_charge_category": "contingency", "new_charge_if_identical_reused": 0},
              "planned_new_symmetry_launches_if_exact_cache_reused": selected_count - int(cached_source_matches),
              "scope": "MgO comparison uses supplemented pools; TiO2 comparison uses primary pools. Generation denominators remain eight per primary arm."}
    OUT.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "committed", "quota_per_arm": {r["control"]: r["quota_per_arm"] for r in records}, "selected": selected_count}))


if __name__ == "__main__":
    main()
