"""Commit Phase 4 execution boundaries without changing the research protocol."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase4"


def sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main():
    path = OUT / "execution_plan.json"
    if path.exists():
        raise RuntimeError("Execution plan already committed; inspect it without replacing it")
    prior = json.loads((ROOT / "artifacts/phase3/readiness.json").read_text())
    budget = json.loads((OUT / "preflight/budget_ledger.json").read_text())
    assert prior["status"] == "complete" and prior["ready_for_phase4"]
    assert sha("config/phase2_protocol.json") == prior["protocol_sha256"]
    assert budget["generation"]["charged_attempts"] == 24 and budget["chgnet"]["charged_attempts"] == 9
    assert not any(budget[lane]["active_reservations"] for lane in ["generation", "chgnet", "qe"])
    model = "artifacts/phase3/models/fresh_selector_seed_20261022.joblib"
    manifest = json.loads((ROOT / "artifacts/phase3/models/fresh_selector_seed_20261022.manifest.json").read_text())
    assert sha(model) == manifest["sha256"]
    record = {
        "phase": 4, "committed_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Complete paired replay and fixed primary generation cohorts; continue bounded CaO anchor numerical validation",
        "research_protocol": {"path": "config/phase2_protocol.json", "sha256": prior["protocol_sha256"]},
        "previous_results_are_retained": True, "hypothesis_or_acquisition_retuning": False,
        "remaining_replay_seeds": prior["remaining_paired_seeds"],
        "policies_per_seed": 5, "rounds_per_policy": 5, "labels_per_round": 10,
        "new_replay_query_events": 1000, "total_including_phase3": 1250,
        "untouched_evaluation_rows_per_seed": 3418,
        "new_primary_generation": {"remaining_control_arms": 3, "remaining_formulas": 5,
                                   "attempts_per_cohort": 8, "total_actual_draws_planned": 64},
        "reused_primary_cohorts": ["Phase1 Mg4O4 SG225 first8, including invalid attempt",
                                   "Phase3 CaMg2O3 SG2 first8, zero exact-six-atom survivors"],
        "fresh_selector": {"path": model, "sha256": manifest["sha256"],
                           "other_seed_or_adapted_models_allowed": False},
        "shortlist": "Use unchanged select_fresh_pair independently per formula, up to2 each; initial geometry only. No CHGNet or QE outcomes enter scores.",
        "shortlist_validation_phase": 5,
        "symmetry_relaxation_selection": "After primary and any separately gated topups, use frozen seeded random within-arm selection and balanced quotas in Phase5; not surrogate energy ranking.",
        "optional_topups": "Disabled by default. Consider only balanced supplementary batches under the original16-slot allocation and unchanged primary denominators; record decision before dispatch.",
        "optional_composition_stretch": "Evaluate original gates only after all core cohorts/replays and DFT obligations are secure; preserve failed default cohorts. Do not spend residual slots merely to chase a positive finding.",
        "QE": {"queue": "Original CaO anchor refinement and final-geometry numerical probes; Phase3 MgO evidence reused",
               "new_phase4_seconds_cap": 2700, "new_primary_candidate": False,
               "no_retargeting_from_CaMg2O3_based_on_outcomes": True,
               "no_full_competition_hull_claim": True},
        "global_caps": {"generation_slots": 128, "CHGNet_launches": 40, "CHGNet_seconds": 14400, "QE_seconds": 21600},
        "numerical_stop_utc": budget["numerical_stop_utc"],
        "CPU_threads": {"replay": 2, "generation": 4, "QE": 4},
        "baseline": {"path": "artifacts/phase4/preflight/budget_ledger.json", "sha256": sha("artifacts/phase4/preflight/budget_ledger.json")},
        "runtime_API_update": {"change": "Current phase header tracks maximum event phase; budget arithmetic and caps unchanged",
                               "previous_source": "artifacts/phase4/preflight/research_budget.py",
                               "previous_sha256": sha("artifacts/phase4/preflight/research_budget.py"),
                               "current_sha256": sha("research_budget.py")},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "committed", "path": str(path), "protocol_sha256": prior["protocol_sha256"]}))


if __name__ == "__main__":
    main()
