"""Audit completed Phase 3 evidence without fits, samples or numerical jobs."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "artifacts/phase3"
CHECKS = []


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    with (ROOT / path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(value, description):
    CHECKS.append({"passed": bool(value), "check": description})


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    from phase3_qe_parser import parse_job
    from research_budget import snapshot

    prior = load("artifacts/phase2/readiness.json")
    check(prior["status"] == "complete", "Phase 2 prerequisites complete")
    protocol_hash = sha("config/phase2_protocol.json")
    check(protocol_hash == prior["protocol_sha256"], "Frozen Phase 2 protocol unchanged after outcomes")
    protocol_manifest = load("artifacts/phase2/protocol/manifest.json")
    for item in protocol_manifest.values():
        if isinstance(item, dict) and {"path", "sha256"} <= item.keys():
            check(sha(item["path"]) == item["sha256"], "Frozen protocol source: " + item["path"])
    model_path = "artifacts/phase3/models/fresh_selector_seed_20261022.joblib"
    manifest = load("artifacts/phase3/models/fresh_selector_seed_20261022.manifest.json")
    split = load("artifacts/phase2/splits/seed_20261022.json")["material_ids"]
    check(sha(model_path) == manifest["sha256"], "Fresh selector hash matches pre-query commitment")
    check(manifest["status"] == "committed_before_any_pool_query" and
          manifest["pool_queries_revealed_before_snapshot"] == 0 and
          manifest["evaluation_labels_read_before_snapshot"] == 0, "Fresh snapshot precedes query/evaluation access")
    check(set(manifest["train_ids"]) == set(split["train"]) and
          set(manifest["calibration_ids"]) == set(split["calibration"]), "Fresh model uses fixed train/calibration IDs")
    check(manifest["calibration"]["rank_1_based"] == 361 and
          manifest["calibration"]["floor_eV_atom"] == .01, "Calibration rank and floor remain frozen")
    replay_base = "artifacts/phase3/replay/seed_20261022"
    summary = load(replay_base + "/summary.json")
    audit = load(replay_base + "/audit_report.json")
    for key, filename in {"feature_archive_sha256": "artifacts/phase2/features/features.npz",
                          "feature_manifest_sha256": "artifacts/phase2/features/feature_manifest.json",
                          "feature_source_sha256": "research_features.py", "models_source_sha256": "research_models.py",
                          "replay_source_sha256": "scripts/phase3_replay.py",
                          "split_sha256": "artifacts/phase2/splits/seed_20261022.json"}.items():
        check(sha(filename) == summary["provenance"][key], "Executed replay input/source unchanged: " + filename)
    check(audit["status"] == "passed" and all(v for k, v in audit.items() if k.startswith("all_")),
          "Replay decision, bootstrap, calibration and label-boundary audit passed")
    check(audit["decisions_replayed_from_pre_reveal_predictions"] == 25 and
          audit["recomputed_bootstrap_plans"] == 125 and audit["verified_model_snapshots"] == 26,
          "All 25 decisions, 125 bootstrap plans and 26 models audited")
    journal_path = replay_base + "/query_journal.csv"
    check(sha(journal_path) == audit["query_journal_sha256"], "Query journal matches replay audit")
    with (ROOT / journal_path).open(encoding="utf-8", newline="") as stream:
        journal = list(csv.DictReader(stream))
    check(len(journal) == summary["total_policy_queries"] == 250, "Five policies complete 250 retrospective queries")
    completed = load(replay_base + "/all_policy_queries_complete.json")
    evaluated = load(replay_base + "/evaluation_summary.json")
    check(completed["evaluator_labels_read_so_far"] == 0 and
          evaluated["evaluated_at_utc"] > completed["completed_at_utc"] and
          evaluated["policy_decisions_finished_before_label_access"], "Evaluation labels accessed after every policy finished")
    check(set(evaluated["evaluation_ids"]) == set(split["unused"]) and len(split["unused"]) == 3418,
          "Fixed 3418-row evaluation cohort remains untouched by training/querying")
    for item in evaluated["evaluated_predictions"]:
        check(item["n"] == 3418 and item["labels_returned_to_learner"] == 0 and
              sha(item["prediction_path"]) == item["prediction_sha256"], "Immutable evaluation prediction: " + item["prediction_path"])
    for policy in summary["policies"]:
        name = policy["policy"]
        rows = [r for r in journal if r["policy"] == name]
        check(len(rows) == len({r["material_id"] for r in rows}) == policy["queries"] == 50 and
              {r["material_id"] for r in rows} <= set(split["pool"]), "Exactly 50 distinct pool-only queries: " + name)
        check(sum(float(r["label_eV_atom"]) <= .05 for r in rows) == policy["near_stable_hits"] and
              sum(float(r["label_eV_atom"]) <= 0 for r in rows) == policy["reference_hull_hits"], "Hits reproduce from revealed labels: " + name)
        own_ids = []
        for index in range(1, 6):
            directory = f"{replay_base}/{name}/round_{index:02d}"
            decision, reveal = load(directory + "/decision.json"), load(directory + "/reveals.json")
            fit, done = load(directory + "/fit_started.json"), load(directory + "/complete.json")
            own_ids.extend(reveal["material_ids"])
            check(manifest["completed_at_utc"] < decision["committed_at_utc"] <= reveal["revealed_at_utc"] and
                  decision["oracle_labels_supplied_to_acquisition"] == 0, f"Pre-reveal decision: {name}/{index}")
            check(set(fit["training_ids"]) == set(split["train"]) | set(own_ids), f"Own-policy training labels only: {name}/{index}")
            for filename, key in [("decision.json", "decision_sha256"), ("reveals.json", "reveal_sha256"),
                                  ("fit_audit.json", "fit_audit_sha256")]:
                check(sha(directory + "/" + filename) == done[key], f"Round evidence hash: {name}/{index}/{filename}")
            check(sha(done["model_path"]) == done["model_sha256"], f"Adapted model hash: {name}/{index}")

    gen_base = "artifacts/phase3/generation/early_CaMg2O3"
    generation, gen_audit = load(gen_base + "/summary.json"), load(gen_base + "/audit.json")
    check(sha("artifacts/phase2/compositions/generation_protocol.json") == generation["source_protocol_sha256"],
          "Generation protocol remains unchanged after the zero-yield result")
    check(gen_audit["status"] == "passed" and gen_audit["model_draws_in_audit"] == 0 and
          sha(gen_base + "/summary.json") == gen_audit["summary_sha256"], "Generation read-only audit passed")
    check(generation["attempts"] == len(generation["results"]) == 8 and
          generation["valid_count"] == generation["valid_unique_count"] == 0, "Eight original draws retained; zero exact-cell primary survivors")
    check(len(gen_audit["results"]) == len(generation["results"]) == 8, "Generation audit covers all eight retained results")
    check(generation["budget_accounting"]["charged_reservation_attempts"] == 12 and
          generation["budget_accounting"]["actual_model_draws"] == 8 and
          generation["budget_accounting"]["unemitted_engineering_slots_charged"] == 4, "Logging failure/recovery conservatively charged")
    for result, audited in zip(generation["results"], gen_audit["results"]):
        for field, key in [("raw_json", "raw_sha256"), ("structure_json", "structure_sha256"), ("cif", "cif_sha256")]:
            check(sha(result[field]) == audited[key], "Preserved generator output: " + result[field])
    selection = load("artifacts/phase3/selection/early_pool_selection.json")
    fallback = load("artifacts/phase3/selection/fallback_decision.json")
    handoff_path = "artifacts/phase3/selection/DFT_handoff.json"
    handoff = load(handoff_path)
    check(selection["source_summary_sha256"] == sha(gen_base + "/summary.json") and
          selection["initial_selector_sha256"] == sha(model_path) and selection["selected"] == [] and
          not selection["CHGNet_or_QE_energies_used_for_selection"], "Empty primary selection frozen from unchanged initial model")
    check(sha(fallback["source_structure"]) == fallback["source_sha256"] and
          fallback["candidate_id"] == "phase1_mgo_attempt_000" and
          fallback["predetermined_candidate_not_replaced_by_scoring"] and not fallback["DFT_energies_used"], "Predeclared known MgO fallback used without energy-based substitution")
    chg = load("artifacts/phase3/chgnet/phase1_mgo_attempt_000/result.json")
    check(chg["status"] == "completed" and chg["converged"] and chg["DFT_eligible"] and
          sha(chg["final_structure"]) == chg["final_structure_sha256"], "Fallback CHGNet converged and passed workload gates")
    check(handoff["no_reordering_by_CHGNet_energy"] and not handoff["new_DFT_outcomes_used"] and
          len(handoff["DFT_queue_in_frozen_order"]) == 1 and
          handoff["DFT_queue_in_frozen_order"][0]["candidate_id"] == fallback["candidate_id"], "One known-control DFT handoff frozen before QE")
    check(handoff["selection_sha256"] == sha("artifacts/phase3/selection/early_pool_selection.json") and
          fallback["original_selection_sha256"] == handoff["selection_sha256"], "Fallback and DFT handoff bind the same frozen primary selection")

    events = [json.loads(line) for line in (ROOT / "artifacts/runtime_budget_events.jsonl").read_text().splitlines() if line.strip()]
    starts = [r for r in events if r["event"] == "reserved"]
    finishes = [r for r in events if r["event"] == "finished"]
    start_by_id, finish_by_id = ({r["reservation_id"]: r for r in rows} for rows in [starts, finishes])
    check(len(starts) == len(start_by_id) and len(finishes) == len(finish_by_id) and
          set(start_by_id) == set(finish_by_id), "Unique reservations all have terminal records; no unresolved jobs")
    budget = snapshot()
    check(all(not budget[lane]["active_reservations"] for lane in ["generation", "chgnet", "qe"]), "No active numerical jobs at Phase 3 close")
    check(budget["generation"]["charged_attempts"] == 24 and budget["generation"]["remaining_attempts"] == 104 and
          budget["chgnet"]["charged_attempts"] == 9 and budget["chgnet"]["remaining_attempts"] == 31,
          "Shared generation/CHGNet counts reconcile with all failures and pilots")
    check(budget["generation"]["ceiling_attempts"] == 128 and budget["chgnet"]["ceiling_attempts"] == 40 and
          budget["chgnet"]["ceiling_seconds"] == 14400 and budget["qe"]["ceiling_seconds"] == 21600 and
          budget["chgnet"]["remaining_seconds"] >= 0 and budget["qe"]["remaining_seconds"] >= 0, "All original numerical caps unchanged and respected")
    qe_jobs = []
    for path in sorted((OUT / "qe").glob("*/result.json")):
        record = json.loads(path.read_text())
        provenance, settings = record["provenance"], record["provenance"]["settings"]
        directory = path.parent
        check(sha(directory / "pw.in") == record["input_sha256"] == provenance["input_sha256"] and
              sha(directory / "pw.out") == record["output_sha256"] and
              sha(directory / "settings.json") == provenance["settings_sha256"], "QE input/output/settings hashes: " + record["job_id"])
        check(sha(provenance["source_geometry"]) == provenance["source_geometry_sha256"] and
              sha(provenance["executable"]) == provenance["executable_sha256"], "QE source/executable hashes: " + record["job_id"])
        for element, path_string in provenance["pseudo_files"].items():
            check(sha(directory / "pseudo" / path_string) == provenance["pseudo_hashes"][element], "QE pseudopotential hash: " + record["job_id"] + "/" + element)
        parsed = parse_job(directory, settings, return_code=record["return_code"], timed_out=record["timed_out"], write_geometry=False)
        check(all(parsed.get(key) == record["result"].get(key) for key in ["job_scf_accepted", "job_stationary_at_this_setting",
              "energy_eV_per_atom", "max_force_vector_norm_eV_per_angstrom", "max_absolute_residual_stress_component_kbar"]),
              "QE SCF/force/full-stress result independently reparsed: " + record["job_id"])
        reservation = start_by_id[record["job_id"]]
        check(reservation["reserved_utc"] <= record["started_at_utc"] and
              abs(finish_by_id[record["job_id"]]["wall_seconds"] - record["elapsed_wall_seconds"]) < 1e-6 and
              record["threads"]["OMP_NUM_THREADS"] == "4", "QE pre-dispatch reservation and full walltime charging: " + record["job_id"])
        if record["category"] == "candidate":
            check(provenance["selection_manifest_sha256"] == sha(handoff_path) and
                  handoff["frozen_utc"] < record["started_at_utc"], "Candidate bound to pre-QE frozen handoff")
        qe_jobs.append(record)
    check(any(r["category"] == "candidate" for r in qe_jobs) and any(r["category"] == "reference" for r in qe_jobs),
          "Real candidate and reference QE jobs executed with preserved outcomes")
    chronological = sorted(qe_jobs, key=lambda r: r["started_at_utc"])
    check(all(a["finished_at_utc"] <= b["started_at_utc"] for a, b in zip(chronological, chronological[1:])), "Only one QE job executes at a time")
    legacy = [json.loads(line) for line in (ROOT / "artifacts/phase1/qe/qe_jobs.jsonl").read_text().splitlines() if line.strip()]
    check(abs(sum(r["elapsed_wall_seconds"] for r in legacy) - budget["qe"]["charged_wall_seconds"]) < 1e-5,
          "Legacy and canonical cumulative QE runtime ledgers reconcile")
    qe_summary = load("artifacts/phase3/qe/summary.json")
    check(sum(job["elapsed_wall_seconds"] for job in qe_jobs) <= 2700,
          "Phase 3 QE work respects its additional 45-minute local allocation")
    check(qe_summary["all_jobs_finished"] and not qe_summary["active_QE_reservations"] and
          qe_summary["phase3_job_count"] == len(qe_jobs), "QE lane summary is final and covers every completed Phase 3 job")
    check({item["job_id"] for item in qe_summary["jobs"]} == {item["job_id"] for item in qe_jobs} and
          all(sha(item["path"]) == item["result_sha256"] for item in qe_summary["jobs"]), "QE summary inventory matches current result hashes")
    check(abs(qe_summary["canonical_QE_snapshot"]["charged_wall_seconds"] - budget["qe"]["charged_wall_seconds"]) < 1e-5,
          "QE summary budget is current at audit close")
    qe_by_id = {job["job_id"]: job for job in qe_jobs}
    for label in ["reference_validation", "candidate_validation"]:
        validation = qe_summary[label]
        geometry_job = qe_by_id[validation["accepted_geometry_job_id"]]
        geometry_path = Path(geometry_job["result"]["final_geometry_json"])
        probe_passes = []
        for probe in validation["final_geometry_sensitivity_checks"]:
            check(probe["job_id"] in qe_by_id, "Final-geometry sensitivity attempt retained: " + probe["job_id"])
            if probe["job_id"] not in qe_by_id:
                probe_passes.append(False)
                continue
            job = qe_by_id[probe["job_id"]]
            same_geometry = job["provenance"]["source_geometry_sha256"] == sha(geometry_path)
            scf_pass = job["result"]["job_scf_accepted"]
            shift = abs(job["result"]["energy_eV_per_atom"] - geometry_job["result"]["energy_eV_per_atom"])
            check(same_geometry == probe["same_final_geometry"] and scf_pass == probe["scf_accepted"] and
                  abs(shift - probe["absolute_energy_shift_eV_per_atom"]) < 1e-12 and
                  (shift <= .005) == probe["within_5_meV_per_atom"], "Sensitivity result independently recomputed: " + probe["job_id"])
            probe_passes.append(same_geometry and scf_pass and shift <= .005)
        actual_convergence = geometry_job["result"]["job_stationary_at_this_setting"] and all(probe_passes)
        check(actual_convergence == validation["full_numerical_convergence"], "Final-setting stationarity and numerical checks agree: " + label)
    comparison = qe_summary["known_MgO_comparison"]
    reference = qe_by_id[qe_summary["accepted_reference_job_id"]]
    candidate = qe_by_id[qe_summary["accepted_candidate_job_id"]]
    difference = candidate["result"]["energy_eV_per_atom"] - reference["result"]["energy_eV_per_atom"]
    check(abs(difference - comparison["raw_candidate_minus_reference_eV_per_atom"]) < 1e-12 and
          candidate["provenance"]["pseudo_hashes"] == reference["provenance"]["pseudo_hashes"], "Compatible per-atom known-MgO energy difference independently reproduced")
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.core import Structure
    matcher = StructureMatcher(ltol=.01, stol=.01, angle_tol=.5, primitive_cell=True, scale=False, attempt_supercell=True)
    match = matcher.fit(Structure.from_file(candidate["result"]["final_geometry_json"]),
                        Structure.from_file(reference["result"]["final_geometry_json"]))
    check(match and comparison["final_structure_match"]["primitive_supercell_aware_match"], "Generated control independently matches known MgO prototype without rescaling")
    check(load("artifacts/phase3/qe/audit.json")["all_job_hash_checks_pass"], "QE lane final provenance audit passed")
    scope_checks = load("artifacts/phase3/qe/scope_guard_checks.json")
    check(scope_checks["all_rejected_before_job_creation"] and
          all(case["rejected"] and not case["job_directory_created"] for case in scope_checks["cases"]),
          "Unsupported metal/O2 checks rejected before job creation or charging")
    check(load("artifacts/phase3/tests/budget_guards/result.json")["status"] == "passed", "Atomic reservation, cap, failure and competing-process guards passed")
    for filename in ["research_models.py", "research_budget.py", "scripts/phase3_replay.py", "scripts/phase3_generate.py",
                     "scripts/phase3_candidates.py", "scripts/phase3_qe.py", "scripts/phase3_qe_parser.py", "reports/phase3_report.md",
                     "artifacts/phase3/figures/first_seed_acquisition.png"]:
        check((ROOT / filename).is_file(), "Reviewable deliverable exists: " + filename)
    check("PLACEHOLDER" not in (ROOT / "reports/phase3_report.md").read_text(encoding="utf-8"), "Execution report contains final results without pending placeholders")
    passed = all(item["passed"] for item in CHECKS)
    created = datetime.now(timezone.utc).isoformat()
    save(OUT / "audit.json", {"phase": 3, "audited_utc": created, "status": "passed" if passed else "failed",
         "check_count": len(CHECKS), "checks": CHECKS, "new_fits_samples_relaxations_or_QE_jobs_in_audit": 0,
         "audit_source_sha256": sha(Path(__file__).relative_to(ROOT)), "qe_jobs_verified": len(qe_jobs)})
    important = ["config/phase2_protocol.json", model_path, journal_path, gen_base + "/summary.json", handoff_path,
                 "artifacts/runtime_budget_events.jsonl", "artifacts/budget_ledger.json", "artifacts/phase3/qe/summary.json",
                 "reports/phase3_report.md", "research_models.py", "research_budget.py", "scripts/phase3_replay.py",
                 "scripts/phase3_generate.py", "scripts/phase3_candidates.py", "scripts/phase3_qe.py", "scripts/phase3_qe_parser.py",
                 "scripts/phase3_finalize.py"]
    save(OUT / "manifest.json", {"created_utc": created, "files": [{"path": p, "sha256": sha(p)} for p in important]})
    save(OUT / "readiness.json", {"phase": 3, "status": "complete" if passed else "audit_failed", "completed_utc": created,
         "ready_for_phase4": passed, "protocol_sha256": protocol_hash, "completed_paired_seeds": [20261022],
         "remaining_paired_seeds": [20261023, 20261024, 20261025, 20261026], "retrospective_queries": 250,
         "primary_exact_cell_generated_survivors": 0, "actual_new_CrystalFormer_draws": 8,
         "phase3_charged_generation_attempts": 12, "phase3_engineering_overhead_attempts": 4,
         "fresh_DFT_candidate_scope": "Predeclared known MgO control; no primary CaMg2O3 survivor",
         "qe_summary": "artifacts/phase3/qe/summary.json", "qe_result_scope": qe_summary["known_MgO_comparison"]["scope"],
         "remaining_generation_attempts": budget["generation"]["remaining_attempts"],
         "remaining_chgnet_launches": budget["chgnet"]["remaining_attempts"],
         "remaining_QE_seconds": budget["qe"]["remaining_seconds"], "all_caps_unchanged": True,
         "new_stable_material_established": False, "symmetry_benefit_established": False,
         "phase4_requirements": ["Complete other four frozen paired replay seeds without retuning",
             "Complete matched nontrivial-group versus P1 sampling on both reserved controls",
             "Generate the other five default new-composition cohorts using their frozen seeds",
             "Retain zero/partial yields and use frozen initial selector for later fresh shortlist",
             "Continue bounded DFT/reference work; require complete compatible competition before any hull claim"]})
    print(json.dumps({"status": "passed" if passed else "failed", "checks": len(CHECKS),
                      "failures": [item["check"] for item in CHECKS if not item["passed"]]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
