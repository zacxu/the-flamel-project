"""Account for four prepared prototype candidates once under the shared cap."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase2/budgets"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    canonical = ROOT / "artifacts/budget_ledger.json"
    baseline_path = OUT / "phase1_baseline.json"
    event_path = OUT / "prototype_attempts.jsonl"
    current = load(canonical)
    if not baseline_path.exists():
        if current["generation"]["charged_attempts"] != 8 or current.get("phase") != 1:
            raise RuntimeError("Cannot establish a clean Phase1 baseline from changed cumulative state")
        baseline_path.write_bytes(canonical.read_bytes())
    baseline = load(baseline_path)
    plan_path = ROOT / "artifacts/phase2/compositions/prototype_plan.json"
    plan = load(plan_path)
    expected = []
    timestamp = datetime.now(timezone.utc).isoformat()
    for row in plan["plans"]:
        if not row["eligible_for_attempt"]:
            continue
        selected = row["selected"]
        candidate = ROOT / selected["prototype_candidate_cif"]
        expected.append({"attempt_id": f"prototype_{row['target_formula']}", "phase": 2,
                         "lane": "generation", "method": "deterministic_prototype_substitution",
                         "attempts_charged": 1, "status": "prepared_valid_candidate",
                         "formula": row["target_formula"], "exact_counts": row["target_exact_counts"],
                         "parent_material_id": selected["material_id"], "mapping": selected["element_mapping"],
                         "candidate_path": candidate.relative_to(ROOT).as_posix(), "candidate_sha256": sha(candidate),
                         "note": "Count original substitution once; JSON/CIF copies, audits and reuse do not create extra attempts."})
    if len(expected) != 4:
        raise RuntimeError("Expected the four predeclared eligible prototype candidates")
    if event_path.exists():
        observed = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
        clean = [{k: v for k, v in event.items() if k not in {"ledgered_utc", "accounting_timing"}} for event in observed]
        if clean != expected:
            raise RuntimeError("Recorded prototype candidates changed; do not silently recharge or replace them")
    else:
        if (ROOT / "artifacts/phase3").exists():
            raise RuntimeError("Cannot introduce a retrospective Phase2 accounting amendment once Phase3 exists")
        with event_path.open("x", encoding="utf-8") as stream:
            for event in expected:
                event.update(ledgered_utc=timestamp,
                             accounting_timing="Prepared during Phase2; explicitly ledgered before any predictor fit or candidate validation outcome")
                stream.write(json.dumps(event)+"\n")
    amendment = {"reason": "Broad128structureceiling includes four deterministic prototype-substitution candidates, not only CrystalFormer samples",
                 "phase1_baseline_sha256": sha(baseline_path), "prototype_ledger_sha256": sha(event_path),
                 "CrystalFormer_attempts": 8, "prototype_attempts": 4, "total_charged_generation_attempts": 12,
                 "remaining_generation_attempts": 116, "default_CF_attempts": 80,
                 "default_total_including_baselines": 84, "default_headroom": 44,
                 "stretch_CF_attempts": 96, "stretch_total_including_baselines": 100, "stretch_headroom": 28,
                 "symmetry_primary_denominators_unchanged": True, "CHGNet_QE_charges_unchanged": True,
                 "prototype_preparation_runtime": "Not separately measured; no generation walltime cap is defined"}
    (OUT / "accounting_amendment.json").write_text(json.dumps(amendment, indent=2)+"\n", encoding="utf-8")
    # Never overwrite later runtime accounting when inspecting this historical phase.
    later_work = (current.get("phase", 1) > 2
                  or current["generation"]["charged_attempts"] > 12
                  or current["chgnet"]["charged_attempts"] > baseline["chgnet"]["charged_attempts"]
                  or current["chgnet"]["charged_wall_seconds"] > baseline["chgnet"]["charged_wall_seconds"]
                  or current["qe"]["charged_wall_seconds"] > baseline["qe"]["charged_wall_seconds"]
                  or current["qe"]["completed_jobs"] > baseline["qe"]["completed_jobs"])
    if later_work:
        print(json.dumps({"status": "historical_prototype_ledger_verified", "current_cumulative_budget_preserved": True}))
        return
    cumulative = json.loads(json.dumps(baseline))
    cumulative.update(phase=2, as_of_utc=timestamp)
    cumulative["generation"].update(charged_attempts=12, remaining_attempts=116,
                                    CrystalFormer_sample_attempts=8, deterministic_prototype_attempts=4,
                                    source_ledgers=["artifacts/phase1/generator/ledger.jsonl", event_path.relative_to(ROOT).as_posix()])
    cumulative["note"] = "Phase2 adds four deterministic prototype candidates under the broad128structure ceiling. All later sampling/baseline attempts require explicit registered ledgers. Historical finalizers must not reset cumulative accounting."
    canonical.write_text(json.dumps(cumulative, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"generation_charged": 12, "remaining": 116, "new_CrystalFormer_samples": 0,
                      "prototype_candidates_charged_once": 4, "CHGNet_remaining": 32, "new_QE_jobs": 0}))


if __name__ == "__main__":
    main()
