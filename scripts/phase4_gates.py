"""Record the original conditional composition-stretch gates after core work."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def main():
    path = ROOT / "artifacts/phase4/gates/composition_stretch.json"
    if path.exists():
        raise RuntimeError("Stretch decision already committed; do not revisit after outcomes")
    primary = load("artifacts/phase4/generation/summary.json")
    replay = load("artifacts/phase4/replay/aggregate_summary.json")
    qe = load("artifacts/phase4/qe/summary.json")
    budget = load("artifacts/budget_ledger.json")
    now = datetime.now(timezone.utc)
    nominal_end = datetime.fromisoformat(budget["project_started_utc"]) + timedelta(hours=10)
    margin = (nominal_end-now).total_seconds()
    gates = {
        "all_core_replay_seeds_complete": replay["status"] == "completed" and replay["n_paired_seeds"] == 5,
        "all_primary_arms_have_a_valid_unique_structure": all(r["valid_unique_count"] >= 1 for r in primary["controls"]),
        "all_six_default_formulas_have_primary_eligible_structure": primary["new_formulas_with_exact_valid_structure"] == 6,
        "DFT_reference_work_on_schedule": qe["status"] == "passed" and qe["all_jobs_finished"],
        "sixteen_generation_slots_remain": budget["generation"]["remaining_attempts"] >= 16,
        "at_least_30min_original_Phase4_margin_remains": margin >= 1800,
    }
    enabled = all(gates.values())
    if enabled:
        raise RuntimeError("All optional gates passed; an explicit bounded stretch execution plan would be required before dispatch")
    reason = ("MgO P1 has zero valid unique primary outputs and none of the six default formulas has an exact-cell eligible structure. "
              "The core adequacy gates therefore fail; remaining generation capacity alone does not enable additional formulas.")
    record = {"decided_utc": now.isoformat(), "decision": "disabled", "enabled": False,
              "gates": gates, "reason": reason, "original_nominal_Phase4_end_utc": nominal_end.isoformat(),
              "measured_margin_seconds": margin, "generation_slots_remaining": budget["generation"]["remaining_attempts"],
              "additional_formulas_generated": 0, "new_structure_draws_in_gate_check": 0,
              "primary_failures_retained": True, "symmetry_supplement_does_not_replace_primary_gate": True,
              "unchanged_global_generation_ceiling": 128}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"composition_stretch": "disabled", "reason": reason, "remaining_slots": record["generation_slots_remaining"]}))


if __name__ == "__main__":
    main()
