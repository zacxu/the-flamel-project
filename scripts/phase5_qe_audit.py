"""Read completed Phase5 known-MgO perturbation artifacts; never launch or modify QE jobs."""
from __future__ import annotations

import json
import re
from datetime import datetime

import numpy as np
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from phase5_qe import ROOT, ART, LOCK, digest, now, save
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
    check("initial_MgO_perturbation_geometry_unchanged", digest(ROOT / plan["initial_source_geometry"]) == plan["initial_source_geometry_sha256"])
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
                  "executed_runner_archive": digest(ART / "executed_sources/scripts__phase5_qe.py") == stage["runner_source_sha256"],
                  "executed_parser_archive": digest(ART / "executed_sources/scripts__phase3_qe_parser.py") == stage["parser_source_sha256"]}
        for element, filename in stage["pseudo_files"].items():
            hashes["pseudo_" + element] = digest(directory / "pseudo" / filename) == stage["pseudo_hashes"][element]
        if stage["inherited_source_settings"]:
            hashes["inherited_settings"] = digest(ROOT / stage["inherited_source_settings"]) == stage["inherited_source_settings_sha256"]
        for name, passed in hashes.items():
            check(f"{job_id}:{name}_sha256", passed)
        check(f"{job_id}:queue_authorized_before_dispatch", datetime.fromisoformat(plan["authorized_at_utc"]) <= datetime.fromisoformat(record["started_at_utc"]))
        check(f"{job_id}:phase5_stamped", stage["phase"] == record["phase"] == 5)
        check(f"{job_id}:source_lineage", (ROOT / stage["source_geometry"]).parent.name in plan["jobs"][job_id]["allowed_parent_jobs"])
        check(f"{job_id}:force_fullstress_reparse_matches", all(result.get(key) == record["result"].get(key) for key in (
            "job_scf_accepted", "job_stationary_at_this_setting", "max_force_vector_norm_eV_per_angstrom", "max_absolute_residual_stress_component_kbar", "pressure_kbar", "energy_eV_per_atom")))
        initial_geometry = Structure.from_file(directory / "initial_geometry.json")
        check(f"{job_id}:known_MgO_nonmagnetic_only", initial_geometry.composition.reduced_formula == "MgO"
            and len(initial_geometry) == settings["nat"] == 8 and settings["nspin"] == 1 and settings["occupations"] == "fixed"
            and result.get("formula") in {None, "MgO"})
        check(f"{job_id}:no_imposed_symmetry", settings["nosym"] and settings["noinv"])
        specification = plan["jobs"][job_id]
        check(f"{job_id}:frozen_settings_and_watchdog", settings["calculation"] == specification["calculation"]
            and settings["ecutwfc_Ry"] == 50 * specification["cutoff_multiplier"]
            and settings["ecutrho_Ry"] == 400 * specification["cutoff_multiplier"]
            and settings["k_spacing_start_inv_angstrom"] == specification["k_spacing"]
            and settings["press_conv_thr_kbar"] == specification["pressure_threshold"]
            and settings["max_seconds"] == specification["max_seconds"]
            and stage["outer_timeout_seconds"] == specification["outer_timeout"])
        check(f"{job_id}:four_threads_one_MPI", record["threads"]["OMP_NUM_THREADS"] == "4" and result.get("reported_MPI_processes") == 1 and result.get("reported_threads_per_MPI_process") == 4)
        check(f"{job_id}:one_legacy_record", sum(row["job_id"] == job_id for row in all_records) == 1)
        check(f"{job_id}:reserved_before_dispatch", job_id in starts and starts[job_id]["lane"] == "qe" and starts[job_id]["phase"] == 5 and datetime.fromisoformat(starts[job_id]["reserved_utc"]) <= datetime.fromisoformat(record["started_at_utc"]))
        check(f"{job_id}:finish_matches_elapsed", job_id in finishes and abs(finishes[job_id]["wall_seconds"] - record["elapsed_wall_seconds"]) < 1e-8)
        check(f"{job_id}:within_reserved_watchdog", record["elapsed_wall_seconds"] <= starts[job_id]["max_seconds"])
        check(f"{job_id}:within_numerical_stop", datetime.fromisoformat(record["finished_at_utc"]) <= datetime.fromisoformat(plan["numerical_stop_utc"]))
        jobs.append({"job_id": job_id, "path": str(path.relative_to(ROOT)), "result_sha256": digest(path),
            "elapsed_wall_seconds": record["elapsed_wall_seconds"], "started_at_utc": record["started_at_utc"],
            "finished_at_utc": record["finished_at_utc"], "settings": settings,
            "hash_checks": hashes, "result": result,
            "termination_diagnostics": {
                "internal_QE_time_limit_reached": "Maximum CPU time exceeded" in (directory / "pw.out").read_text(errors="replace"),
                "launcher_watchdog_triggered": record["timed_out"],
                "completed_SCF_calls": result["completed_scf_calls"],
                "started_SCF_calls": len(re.findall(r"Self-consistent Calculation", (directory / "pw.out").read_text(errors="replace"))),
                "last_reported_BFGS_steps": max([int(x) for x in re.findall(r"number of bfgs steps\s*=\s*(\d+)", (directory / "pw.out").read_text(errors="replace"))], default=0),
                "terminal_SCF_accepted": result["job_scf_accepted"],
                "terminal_geometry_forces_and_stress_available": "max_force_vector_norm_eV_per_angstrom" in result and "max_absolute_residual_stress_component_kbar" in result}})
    chronological = sorted(jobs, key=lambda row: row["started_at_utc"])
    check("QE_jobs_do_not_overlap", all(left["finished_at_utc"] <= right["started_at_utc"] for left, right in zip(chronological, chronological[1:])))
    phase5_wall = sum(row["elapsed_wall_seconds"] for row in jobs)
    check("phase5_bounded_queue_wall", phase5_wall <= plan["additional_phase5_QE_wall_ceiling_seconds"])
    canonical = read(ROOT / "artifacts/budget_ledger.json")
    legacy_wall = sum(row["elapsed_wall_seconds"] for row in all_records)
    check("canonical_and_legacy_QE_wall_match", abs(legacy_wall - canonical["qe"]["charged_wall_seconds"]) < 1e-6)
    check("global_QE_cap", canonical["qe"]["charged_wall_seconds"] <= 21600)
    check("no_QE_reservations_or_mutex_remain", not canonical["qe"]["active_reservations"] and not LOCK.exists())
    manifest = read(ROOT / plan["perturbation_manifest"])
    check("frozen_perturbation_manifest_hash", digest(ROOT / plan["perturbation_manifest"]) == plan["perturbation_manifest_sha256"])
    check("original_known_control_result_hash", digest(ROOT / plan["original_control_result"]) == plan["original_control_result_sha256"])
    check("prior_phase4_runner_unchanged", digest(ROOT / "scripts/phase4_qe.py") == plan["prior_phase4_runner_sha256"])
    original_record = read(ROOT / plan["original_control_result"])
    original = Structure.from_file(ROOT / manifest["source_geometry"])
    perturbed = Structure.from_file(ROOT / manifest["geometry_path"])
    check("original_known_control_geometry_hash", digest(ROOT / manifest["source_geometry"]) == manifest["source_geometry_sha256"])
    check("perturbed_known_control_geometry_hash", digest(ROOT / manifest["geometry_path"]) == manifest["geometry_sha256"])
    rng = np.random.default_rng(260022)
    displacements = rng.normal(size=(8, 3))
    displacements *= .01 / np.linalg.norm(displacements, axis=1)[:, None]
    raw = rng.normal(size=(3, 3))
    strain = (raw + raw.T) / 2
    strain *= .005 / np.max(np.abs(np.linalg.eigvalsh(strain)))
    expected_lattice = original.lattice.matrix @ (np.eye(3) + strain)
    expected_positions = original.frac_coords @ expected_lattice + displacements
    fractional_difference = (perturbed.cart_coords - expected_positions) @ np.linalg.inv(expected_lattice)
    check("perturbation_seed_unchanged", manifest["seed"] == 260022)
    check("atomic_displacements_exactly_reproduced", np.allclose(displacements, manifest["atom_displacements_angstrom"], atol=1e-15))
    check("atomic_displacement_norms_0p01_A", np.allclose(np.linalg.norm(displacements, axis=1), .01, atol=1e-15))
    check("symmetric_strain_exactly_reproduced", np.allclose(strain, manifest["symmetric_strain"], atol=1e-15))
    check("maximum_absolute_principal_strain_0p005", np.isclose(np.max(np.abs(np.linalg.eigvalsh(strain))), .005, atol=1e-15))
    check("perturbed_lattice_reproduced", np.allclose(perturbed.lattice.matrix, expected_lattice, atol=1e-12))
    check("perturbed_positions_reproduced_modulo_PBC", np.allclose(fractional_difference, np.round(fractional_difference), atol=1e-12))
    check("same_eight_atom_known_composition", len(perturbed) == len(original) == 8 and original.composition == perturbed.composition)
    check("perturbation_breaks_spacegroup225_to_1", SpacegroupAnalyzer(original, symprec=1e-3).get_space_group_number() == 225 and SpacegroupAnalyzer(perturbed, symprec=1e-3).get_space_group_number() == 1)
    check("perturbation_frozen_before_first_dispatch", not jobs or datetime.fromisoformat(manifest["created_at_utc"]) <= datetime.fromisoformat(chronological[0]["started_at_utc"]))
    check("maximum_queue_watchdogs_bounded", sum(s["outer_timeout"] for s in plan["jobs"].values()) == plan["maximum_all_allowed_job_watchdogs_seconds"] == 2520)
    job_map = {row["job_id"]: row for row in jobs}
    first_job = job_map.get("p5_mgo_perturb_90")
    if first_job and not first_job["result"]["job_scf_accepted"]:
        check("terminal_SCF_failure_stops_queue_without_continuation_or_probes", len(jobs) == 1)
        check("terminal_unaccepted_job_remains_failed_in_budget_events", finishes[first_job["job_id"]]["status"] == "failed")
    continuation = job_map.get("p5_mgo_perturb_90_cont1")
    if continuation:
        first = job_map["p5_mgo_perturb_90"]
        decision = read(ART / "continuation_decision.json")
        check("continuation_only_for_accepted_SCF_failed_stationarity", first["result"]["job_scf_accepted"] and not first["result"]["job_stationary_at_this_setting"])
        check("continuation_trigger_bound_to_first_result", decision["base_result_sha256"] == digest(ART / "p5_mgo_perturb_90/result.json"))
        check("continuation_decision_before_dispatch", datetime.fromisoformat(decision["at_utc"]) <= datetime.fromisoformat(continuation["started_at_utc"]))
    sensitivity_path = ART / "sensitivity_decision.json"
    decision = read(sensitivity_path) if sensitivity_path.exists() else None
    base = job_map.get(decision["base_job"]) if decision else None
    probes = []
    if base:
        for label, key in (("cutoff", "cutoff_job"), ("kpoint", "kpoint_job")):
            probe = job_map[decision[key]]
            probe_stage = read(ART / probe["job_id"] / "stage.json")
            shift = abs(base["result"]["energy_eV_per_atom"] - probe["result"]["energy_eV_per_atom"])
            same_geometry = probe_stage["source_geometry_sha256"] == digest(ART / base["job_id"] / "final_geometry.json")
            distinct_mesh = label != "kpoint" or base["settings"]["k_mesh"] != probe["settings"]["k_mesh"]
            probes.append({"kind": label, "job_id": probe["job_id"], "absolute_energy_shift_eV_per_atom": shift,
                "same_final_geometry": same_geometry, "SCF_accepted": probe["result"]["job_scf_accepted"],
                "distinct_k_mesh": distinct_mesh, "within_5_meV_per_atom": shift <= .005})
            check(label + "_probe_bound_to_accepted_final_geometry", same_geometry)
            check(label + "_sensitivity_decision_reproduced", abs(shift - decision[label + "_shift_eV_per_atom"]) < 1e-12)
        check("accepted_geometry_stationarity_independent_of_probe_status", base["result"]["job_stationary_at_this_setting"])
    accepted = bool(base and base["result"]["job_stationary_at_this_setting"] and len(probes) == 2
        and all(p["same_final_geometry"] and p["SCF_accepted"] and p["distinct_k_mesh"] and p["within_5_meV_per_atom"] for p in probes))
    phase3 = read(ROOT / "artifacts/phase3/qe/summary.json")
    original_accepted = phase3["candidate_validation"]["full_numerical_convergence"]
    reference_record_path = ROOT / "artifacts/phase3/qe" / phase3["accepted_reference_job_id"] / "result.json"
    reference_record = read(reference_record_path)
    reference_accepted = phase3["reference_validation"]["full_numerical_convergence"]
    original_stage = original_record["provenance"]
    common_settings = bool(base and all(base["settings"][k] == original_stage["settings"][k]
        for k in ("input_dft", "ecutwfc_Ry", "ecutrho_Ry", "k_spacing_start_inv_angstrom", "nspin", "occupations", "nosym", "noinv")))
    common_pseudos = bool(base and read(ART / base["job_id"] / "stage.json")["pseudo_hashes"] == original_stage["pseudo_hashes"])
    comparison_valid = accepted and original_accepted and common_settings and common_pseudos
    comparison = None
    if base:
        final = Structure.from_file(ART / base["job_id"] / "final_geometry.json")
        comparison_protocol = read(ART / "comparison_protocol.json")
        matcher_settings = comparison_protocol["matcher_settings"]
        check("prior_Phase3_comparison_summary_unchanged", digest(ROOT / comparison_protocol["source_phase3_summary"]) == comparison_protocol["source_phase3_summary_sha256"])
        check("known_control_comparator_frozen_before_outcomes", datetime.fromisoformat(comparison_protocol["frozen_at_utc"]) <= datetime.fromisoformat(base["finished_at_utc"]))
        check("known_control_comparator_matches_prior_Phase3", matcher_settings == phase3["known_MgO_comparison"]["final_structure_match"]["matcher_settings"])
        matcher = StructureMatcher(ltol=matcher_settings["ltol"], stol=matcher_settings["stol"],
            angle_tol=matcher_settings["angle_tol_degrees"], primitive_cell=matcher_settings["primitive_cell"],
            scale=matcher_settings["scale"], attempt_supercell=matcher_settings["attempt_supercell"])
        rms = matcher.get_rms_dist(original, final)
        comparison = {
            "accepted_for_finite_energy_comparison": comparison_valid,
            "original_control_job_id": original_record["job_id"], "perturbed_relaxation_job_id": base["job_id"],
            "same_functional_pseudos_cutoffs_kspacing": common_settings and common_pseudos,
            "matcher_settings": matcher_settings,
            "original_control_energy_eV_per_atom": original_record["result"]["energy_eV_per_atom"],
            "perturbed_final_energy_eV_per_atom": base["result"]["energy_eV_per_atom"] if accepted else None,
            "perturbed_minus_original_eV_per_atom": base["result"]["energy_eV_per_atom"] - original_record["result"]["energy_eV_per_atom"] if comparison_valid else None,
            "known_reference_job_id": reference_record["job_id"],
            "known_reference_energy_eV_per_atom": reference_record["result"]["energy_eV_per_atom"],
            "known_reference_result_sha256": digest(reference_record_path),
            "perturbed_minus_known_reference_eV_per_atom": base["result"]["energy_eV_per_atom"] - reference_record["result"]["energy_eV_per_atom"] if comparison_valid and reference_accepted else None,
            "finite_comparison_tolerance_eV_per_atom": comparison_protocol["finite_energy_interpretation_tolerance_eV_per_atom"],
            "energy_ordering_resolved_at_tolerance": abs(base["result"]["energy_eV_per_atom"] - original_record["result"]["energy_eV_per_atom"]) > comparison_protocol["finite_energy_interpretation_tolerance_eV_per_atom"] if comparison_valid else None,
            "structure_matcher_to_original_control": bool(matcher.fit(original, final)),
            "normalized_RMS_and_max_displacement": list(rms) if rms is not None else None,
            "final_spacegroup_symprec_1e3": SpacegroupAnalyzer(final, symprec=1e-3).get_space_group_number(),
            "final_spacegroup_symprec_1e2": SpacegroupAnalyzer(final, symprec=1e-2).get_space_group_number(),
            "final_volume_per_atom_angstrom3": final.volume / len(final),
            "original_volume_per_atom_angstrom3": original.volume / len(original),
            "max_force_vector_norm_eV_per_angstrom": base["result"]["max_force_vector_norm_eV_per_angstrom"],
            "max_abs_full_stress_component_kbar": base["result"]["max_absolute_residual_stress_component_kbar"],
            "pressure_kbar": base["result"]["pressure_kbar"],
            "SCF_error_Ry": base["result"]["scf_error_Ry"],
            "scope": "Single perturbation recovery of already known MgO. Similar energies within finite convergence tolerance do not establish a minimum, phonon stability or hull stability."}
        save(ART / "known_control_perturbation_comparison.json", comparison)
    summary = {
        "schema_version": 1, "phase": 5, "updated_at_utc": now(),
        "status": "passed" if all(c["passed"] for c in checks) else "failed",
        "checks_passed": sum(c["passed"] for c in checks), "checks_total": len(checks),
        "failed_checks": [c for c in checks if not c["passed"]],
        "phase5_QE_job_count": len(jobs), "phase5_QE_wall_seconds": phase5_wall,
        "all_jobs_finished": not canonical["qe"]["active_reservations"] and not LOCK.exists(),
        "accepted_perturbation_job_id": base["job_id"] if accepted else None,
        "perturbation_check_performed": len(jobs) > 0,
        "perturbation_validation_incomplete": not accepted,
        "termination_summary": [dict(job_id=j["job_id"], **j["termination_diagnostics"]) for j in jobs],
        "incomplete_reason": ("Internal QE time limit reached without accepted terminal SCF and final force/stress output; no continuation or final-geometry probes authorized" if not accepted and any(j["termination_diagnostics"]["internal_QE_time_limit_reached"] and not j["result"]["job_scf_accepted"] for j in jobs)
            else "Required final stationarity or numerical sensitivity evidence is incomplete" if not accepted else None),
        "phonon_check_performed": False,
        "local_minimum_established": False,
        "perturbation_final_geometry_numerical_checks_pass": accepted,
        "final_geometry_sensitivity_checks": probes,
        "known_control_comparison": comparison,
        "fresh_candidate_jobs_this_phase": 0, "fresh_CaMg2O3_candidate_submitted": False,
        "full_frozen_inventory_hull_established": False, "new_stable_materials": 0,
        "completed_original_source_reference_ids": read(ROOT / "artifacts/phase4/qe/summary.json")["completed_original_source_reference_ids"],
        "reference_inventory_completeness_unchanged_this_phase": True,
        "primary_Ca_Mg_O_reference_coverage": {
            "accepted_original_source_entries": 2,
            "frozen_inventory_entries": len(read(ROOT / "artifacts/phase2/dft/primary_reference_plan.json")["records"]),
            "full_inventory_complete": False},
        "fallback_Mg_O_reference_coverage": {
            "accepted_original_source_entries": 1,
            "frozen_inventory_entries": len(read(ROOT / "artifacts/phase2/dft/fallback_Mg-O_reference_plan.json")["records"]),
            "full_inventory_complete": False},
        "perturbation_definition": {
            "manifest_path": plan["perturbation_manifest"],
            "manifest_sha256": plan["perturbation_manifest_sha256"],
            "seed": manifest["seed"], "atomic_displacement_norm_angstrom": .01,
            "max_absolute_principal_strain": .005,
            "initial_spacegroup": manifest["perturbed_spacegroup_symprec_1e3"],
            "original_spacegroup": manifest["original_spacegroup_symprec_1e3"]},
        "scope": plan["scope"], "canonical_QE_snapshot": canonical["qe"], "jobs": jobs}
    save(ART / "audit.json", {**summary, "checks": checks})
    save(ART / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("status", "checks_passed", "checks_total", "phase5_QE_job_count", "phase5_QE_wall_seconds", "accepted_perturbation_job_id", "perturbation_final_geometry_numerical_checks_pass")}, indent=2))


if __name__ == "__main__":
    main()
