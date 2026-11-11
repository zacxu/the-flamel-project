"""Read completed Phase4 CaO artifacts; never launch or modify QE jobs."""
from __future__ import annotations

import json
from datetime import datetime

from phase4_qe import ROOT, ART, LOCK, digest, now, save
from phase3_qe_parser import parse_job


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    checks = []

    def check(name, passed, details=None):
        checks.append({"name": name, "passed": bool(passed), "details": details})

    plan = read(ART / "queue_plan.json")
    frozen = digest(ART / "queue_plan.json")
    check("phase2_protocol_unchanged", digest(ROOT / "config/phase2_protocol.json") == plan["frozen_phase2_protocol_sha256"])
    check("phase2_numerical_protocol_unchanged", digest(ROOT / "artifacts/phase2/dft/numerical_protocol.json") == plan["numerical_protocol_sha256"])
    check("prior_phase3_runner_unchanged", digest(ROOT / "scripts/phase3_qe.py") == plan["prior_phase3_runner_sha256"])
    check("initial_CaO_source_geometry_unchanged", digest(ROOT / plan["initial_source_geometry"]) == plan["initial_source_geometry_sha256"])
    jobs = []
    all_records = [json.loads(line) for line in (ROOT / "artifacts/phase1/qe/qe_jobs.jsonl").read_text().splitlines()]
    runtime = [json.loads(line) for line in (ROOT / "artifacts/runtime_budget_events.jsonl").read_text().splitlines()]
    starts = {row["reservation_id"]: row for row in runtime if row["event"] == "reserved"}
    finishes = {row["reservation_id"]: row for row in runtime if row["event"] == "finished"}
    for path in sorted(ART.glob("*/result.json")):
        record = read(path)
        stage = record["provenance"]
        job_id = record["job_id"]
        settings = stage["settings"]
        directory = path.parent
        result = parse_job(directory, settings, return_code=record["return_code"], timed_out=record["timed_out"], write_geometry=False)
        hashes = {"input": digest(directory / "pw.in") == stage["input_sha256"],
                  "source_geometry": digest(ROOT / stage["source_geometry"]) == stage["source_geometry_sha256"],
                  "executable": digest(ROOT / stage["executable"]) == stage["executable_sha256"],
                  "output": digest(directory / "pw.out") == record["output_sha256"],
                  "settings": digest(directory / "settings.json") == stage["settings_sha256"],
                  "queue": frozen == stage["queue_plan_sha256"],
                  "input_factory": digest(ROOT / "scripts/phase2_dft_inputs.py") == stage["input_factory_sha256"],
                  "executed_runner_archive": digest(ART / "executed_sources/scripts__phase4_qe.py") == stage["runner_source_sha256"],
                  "executed_parser_archive": digest(ART / "executed_sources/scripts__phase3_qe_parser.py") == stage["parser_source_sha256"]}
        for element, filename in stage["pseudo_files"].items():
            hashes["pseudo_" + element] = digest(directory / "pseudo" / filename) == stage["pseudo_hashes"][element]
        if stage["inherited_source_settings"]:
            hashes["inherited_settings"] = digest(ROOT / stage["inherited_source_settings"]) == stage["inherited_source_settings_sha256"]
        for name, passed in hashes.items():
            check(f"{job_id}:{name}_sha256", passed)
        check(f"{job_id}:queue_authorized_before_dispatch", datetime.fromisoformat(plan["authorized_at_utc"]) <= datetime.fromisoformat(record["started_at_utc"]))
        check(f"{job_id}:phase4_stamped", stage["phase"] == record["phase"] == 4)
        check(f"{job_id}:source_lineage", (ROOT / stage["source_geometry"]).parent.name in plan["jobs"][job_id]["allowed_parent_jobs"])
        check(f"{job_id}:force_fullstress_reparse_matches", all(result.get(key) == record["result"].get(key) for key in (
            "job_scf_accepted", "job_stationary_at_this_setting", "max_force_vector_norm_eV_per_angstrom", "max_absolute_residual_stress_component_kbar", "pressure_kbar", "energy_eV_per_atom")))
        check(f"{job_id}:CaO_nonmagnetic_only", result.get("formula") == "CaO" and settings["nat"] == 2 and settings["nspin"] == 1 and settings["occupations"] == "fixed")
        check(f"{job_id}:no_imposed_symmetry", settings["nosym"] and settings["noinv"])
        check(f"{job_id}:four_threads_one_MPI", record["threads"]["OMP_NUM_THREADS"] == "4" and result.get("reported_MPI_processes") == 1 and result.get("reported_threads_per_MPI_process") == 4)
        check(f"{job_id}:one_legacy_record", sum(row["job_id"] == job_id for row in all_records) == 1)
        check(f"{job_id}:reserved_before_dispatch", job_id in starts and starts[job_id]["lane"] == "qe" and starts[job_id]["phase"] == 4 and datetime.fromisoformat(starts[job_id]["reserved_utc"]) <= datetime.fromisoformat(record["started_at_utc"]))
        check(f"{job_id}:finish_matches_elapsed", job_id in finishes and abs(finishes[job_id]["wall_seconds"] - record["elapsed_wall_seconds"]) < 1e-8)
        check(f"{job_id}:within_reserved_watchdog", record["elapsed_wall_seconds"] <= starts[job_id]["max_seconds"])
        check(f"{job_id}:within_numerical_stop", datetime.fromisoformat(record["finished_at_utc"]) <= datetime.fromisoformat(plan["numerical_stop_utc"]))
        jobs.append({"job_id": job_id, "path": str(path.relative_to(ROOT)), "result_sha256": digest(path),
            "elapsed_wall_seconds": record["elapsed_wall_seconds"], "started_at_utc": record["started_at_utc"],
            "finished_at_utc": record["finished_at_utc"], "settings": settings,
            "hash_checks": hashes, "result": result})
    chronological = sorted(jobs, key=lambda row: row["started_at_utc"])
    check("QE_jobs_do_not_overlap", all(left["finished_at_utc"] <= right["started_at_utc"] for left, right in zip(chronological, chronological[1:])))
    phase4_wall = sum(row["elapsed_wall_seconds"] for row in jobs)
    check("phase4_bounded_queue_wall", phase4_wall <= plan["additional_phase4_QE_wall_ceiling_seconds"])
    canonical = read(ROOT / "artifacts/budget_ledger.json")
    legacy_wall = sum(row["elapsed_wall_seconds"] for row in all_records)
    check("canonical_and_legacy_QE_wall_match", abs(legacy_wall - canonical["qe"]["charged_wall_seconds"]) < 1e-6)
    check("global_QE_cap", canonical["qe"]["charged_wall_seconds"] <= 21600)
    check("no_QE_reservations_or_mutex_remain", not canonical["qe"]["active_reservations"] and not LOCK.exists())
    decision_path = ART / ("refined_sensitivity_decision.json" if (ART / "refined_sensitivity_decision.json").exists() else "initial_sensitivity_decision.json")
    decision = read(decision_path) if decision_path.exists() else None
    job_map = {row["job_id"]: row for row in jobs}
    base = job_map.get(decision["base_job"]) if decision else None
    rechecked_probes = []
    if base:
        for label, key in (("cutoff", "cutoff_job"), ("kpoint", "kpoint_job")):
            probe = job_map[decision[key]]
            probe_stage = read(ART / probe["job_id"] / "stage.json")
            shift = abs(base["result"]["energy_eV_per_atom"] - probe["result"]["energy_eV_per_atom"])
            final_geometry_bound = probe_stage["source_geometry_sha256"] == digest(ART / base["job_id"] / "final_geometry.json")
            rechecked_probes.append({"kind": label, "job_id": probe["job_id"], "absolute_energy_shift_eV_per_atom": shift,
                "same_final_geometry": final_geometry_bound, "SCF_accepted": probe["result"]["job_scf_accepted"],
                "distinct_k_mesh": label != "kpoint" or base["settings"]["k_mesh"] != probe["settings"]["k_mesh"],
                "within_5_meV_per_atom": shift <= .005})
            check(label + "_probe_bound_to_accepted_final_geometry", final_geometry_bound)
    numerically_accepted = bool(base and base["result"]["job_stationary_at_this_setting"] and len(rechecked_probes) == 2
        and all(row["same_final_geometry"] and row["SCF_accepted"] and row["distinct_k_mesh"] and row["within_5_meV_per_atom"] for row in rechecked_probes))
    phase3 = read(ROOT / "artifacts/phase3/qe/summary.json")
    mgo_validation = phase3["reference_validation"]["full_numerical_convergence"]
    mgo_id = phase3["accepted_reference_job_id"]
    mgo_record_path = ROOT / "artifacts/phase3/qe" / mgo_id / "result.json"
    mgo_record = read(mgo_record_path)
    common_pseudos = bool(base and read(ART / base["job_id"] / "stage.json")["pseudo_hashes"]["O"] == mgo_record["provenance"]["pseudo_hashes"]["O"])
    common = bool(numerically_accepted and base["settings"]["ecutwfc_Ry"] == 90 and base["settings"]["ecutrho_Ry"] == 720 and base["settings"]["k_spacing_start_inv_angstrom"] == .35 and mgo_validation and common_pseudos
        and base["settings"]["input_dft"] == mgo_record["provenance"]["settings"]["input_dft"] == "PBE")
    incomplete = read(ROOT / "artifacts/phase2/dft/primary_reference_plan.json")["records"]
    completed_ids = {"mp-1265"} if mgo_validation else set()
    if numerically_accepted:
        completed_ids.add("mp-2605")
    summary = {"schema_version": 1, "phase": 4, "updated_at_utc": now(),
        "status": "passed" if all(row["passed"] for row in checks) else "failed",
        "checks_passed": sum(row["passed"] for row in checks), "checks_total": len(checks),
        "failed_checks": [row for row in checks if not row["passed"]],
        "phase4_QE_job_count": len(jobs), "phase4_QE_wall_seconds": phase4_wall,
        "all_jobs_finished": not canonical["qe"]["active_reservations"] and not LOCK.exists(),
        "accepted_CaO_job_id": base["job_id"] if numerically_accepted else None,
        "CaO_final_geometry_numerical_checks_pass": numerically_accepted,
        "final_geometry_sensitivity_checks": rechecked_probes,
        "CaO_and_MgO_shared_90_720_Ry_spacing_0p35_anchor_settings": common,
        "CaO_energy_eV_per_atom": base["result"]["energy_eV_per_atom"] if numerically_accepted else None,
        "known_MgO_reference_energy_eV_per_atom": mgo_record["result"]["energy_eV_per_atom"],
        "fresh_candidate_jobs_this_phase": 0, "fresh_CaMg2O3_candidate_submitted": False,
        "full_frozen_inventory_hull_established": False, "new_stable_materials": 0,
        "completed_original_source_reference_ids": sorted(completed_ids),
        "uncompleted_frozen_primary_reference_ids": [row["material_id"] for row in incomplete if row["material_id"] not in completed_ids],
        "scope": "Only CaO reference refinement; compatible oxide anchors alone do not establish a decomposition hull, discovery, dynamics, or experimental stability. Metal/O2/spin-ambiguous references remain uncomputed.",
        "canonical_QE_snapshot": canonical["qe"], "jobs": jobs}
    if common:
        anchor = {"created_at_utc": now(), "scope": "Compatible CaO+2MgO reaction anchors only; target candidate has not been calculated; no decomposition hull established",
            "target_formula": "CaMg2O3", "balanced_products": {"CaO": 1, "MgO": 2},
            "per_atom_weights": {"CaO": 1/3, "MgO": 2/3},
            "weighted_product_energy_eV_per_atom": (summary["CaO_energy_eV_per_atom"] + 2 * summary["known_MgO_reference_energy_eV_per_atom"]) / 3,
            "CaO_result_path": str((ART / base["job_id"] / "result.json").relative_to(ROOT)),
            "CaO_result_sha256": digest(ART / base["job_id"] / "result.json"),
            "MgO_result_path": str(mgo_record_path.relative_to(ROOT)), "MgO_result_sha256": digest(mgo_record_path),
            "same_functional_common_O_pseudopotential_cutoffs_and_kspacing": True,
            "candidate_energy_present": False, "reaction_energy_present": False,
            "interpretation": "A future positive resolved candidate-minus-products difference establishes instability against this reaction. A negative difference only beats these anchors and is insufficient for full-inventory stability."}
        save(ART / "oxide_reaction_anchors.json", anchor)
    save(ART / "audit.json", {**summary, "checks": checks})
    save(ART / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("status", "checks_passed", "checks_total", "phase4_QE_job_count", "phase4_QE_wall_seconds", "accepted_CaO_job_id", "CaO_final_geometry_numerical_checks_pass", "CaO_and_MgO_shared_90_720_Ry_spacing_0p35_anchor_settings")}, indent=2))


if __name__ == "__main__":
    main()
