"""Summarize Phase3 QE evidence; never launch jobs or infer a complete hull."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from phase3_qe import ROOT, ART, LOCK, digest, save
from phase3_qe_parser import parse_job


def inspect_job(job_id):
    path = ART / job_id / "result.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    result = parse_job(path.parent, record["provenance"]["settings"],
                       return_code=record["return_code"], timed_out=record["timed_out"],
                       write_geometry=False)
    return {"job_id": job_id, "path": str(path.relative_to(ROOT)),
            "result_sha256": digest(path), "elapsed_wall_seconds": record["elapsed_wall_seconds"],
            "role": record["category"], "settings": record["provenance"]["settings"],
            "timed_out": record["timed_out"], "return_code": record["return_code"],
            "c_bands_warning_count": (path.parent / "pw.out").read_text(errors="replace").count("eigenvalues not converged"),
            "peak_working_set_bytes_observed": record["peak_working_set_bytes_observed"],
            "result": result}


def convergence(base_id, probe_ids):
    base = inspect_job(base_id)
    probes = [inspect_job(job_id) for job_id in probe_ids]
    checks = []
    for index, (probe_id, probe) in enumerate(zip(probe_ids, probes)):
        same_geometry = bool(base and probe and
            json.loads((ART / probe_id / "stage.json").read_text())["source_geometry_sha256"]
            == digest(ART / base_id / "final_geometry.json"))
        shift = (abs(probe["result"]["energy_eV_per_atom"] - base["result"]["energy_eV_per_atom"])
                 if base and probe and probe["result"].get("job_scf_accepted") else None)
        expected_cutoff = 75.0 if index == 0 else 90.0
        expected_spacing = 0.35 if index == 0 else 0.45
        protocol_match = bool(probe and probe["settings"]["calculation"] == "scf"
            and probe["settings"]["ecutwfc_Ry"] == expected_cutoff
            and probe["settings"]["ecutrho_Ry"] == expected_cutoff * 8
            and probe["settings"]["k_spacing_start_inv_angstrom"] == expected_spacing
            and probe["settings"]["input_dft"] == "PBE"
            and (index == 0 or probe["settings"]["k_mesh"] != base["settings"]["k_mesh"]))
        checks.append({"job_id": probe_id, "same_final_geometry": same_geometry,
                       "intended_sensitivity_settings_verified": protocol_match,
                       "scf_accepted": bool(probe and probe["result"].get("job_scf_accepted")),
                       "absolute_energy_shift_eV_per_atom": shift,
                       "within_5_meV_per_atom": shift is not None and shift <= 0.005,
                       "settings": probe["settings"] if probe else None})
    stationary = bool(base and base["result"].get("job_stationary_at_this_setting"))
    accepted_setting = bool(base and base["settings"]["ecutwfc_Ry"] == 90
        and base["settings"]["ecutrho_Ry"] == 720
        and base["settings"]["k_spacing_start_inv_angstrom"] == 0.35)
    passed = stationary and accepted_setting and len(checks) == 2 and all(
        item["same_final_geometry"] and item["intended_sensitivity_settings_verified"]
        and item["scf_accepted"] and item["within_5_meV_per_atom"] for item in checks)
    return {"accepted_geometry_job_id": base_id, "base_job_present": base is not None,
            "final_setting_stationarity_pass": stationary,
            "accepted_90_720_Ry_kspacing_0p35_setting_verified": accepted_setting,
            "final_geometry_sensitivity_checks": checks,
            "full_numerical_convergence": passed,
            "convergence_scope": "Recorded adjacent cutoff and k-mesh changes <=5 meV/atom at the final geometry, plus final-setting electronic/force/full-stress checks; finite tests, not a rigorous error bound"}


def main():
    jobs = [inspect_job(path.parent.name) for path in sorted(ART.glob("*/result.json"))]
    canonical = json.loads((ROOT / "artifacts" / "budget_ledger.json").read_text())
    reference = convergence("p3_ref_mgo_90_k035_cont1", ["p3_mgo_final_final_cut75", "p3_mgo_final_final_k045"])
    candidate = convergence("p3_candidate_mgo_fallback_90", ["p3_fallback_final_final_cut75", "p3_fallback_final_final_k045"])
    complete = reference["full_numerical_convergence"] and candidate["full_numerical_convergence"]
    reference_record = inspect_job(reference["accepted_geometry_job_id"])
    candidate_record = inspect_job(candidate["accepted_geometry_job_id"])
    raw_difference = None
    if reference_record and candidate_record and all(
        record["result"].get("job_scf_accepted") for record in [reference_record, candidate_record]):
        raw_difference = candidate_record["result"]["energy_eV_per_atom"] - reference_record["result"]["energy_eV_per_atom"]
    comparison = {"scope": "Known MgO control: frozen eight-atom generated/CHGNet-pre-relaxed structure versus original-source-cell two-atom rock-salt MgO reference; no new material/composition discovery",
                  "same_pseudopotentials_functional_and_final_cutoffs": True,
                  "final_cutoffs_Ry": {"ecutwfc": 90, "ecutrho": 720},
                  "k_spacing_target_inv_angstrom": 0.35,
                  "raw_candidate_minus_reference_eV_per_atom": raw_difference,
                  "numerically_validated_relative_energy": complete,
                  "outcome": "accepted_scoped_relative_energy" if complete else "inconclusive_pending_numerical_checks",
                  "interpretation": "No complete decomposition hull, new-material, phonon, finite-temperature, or experimental-stability conclusion follows from this known-control comparison",
                  "energy_scope": "Static PBE electronic energies at approximately zero external pressure; no vibrational or finite-temperature free energies",
                  "Materials_Project_energies_mixed_with_QE": False,
                  "symmetry_breaking_perturbation_check_performed": False,
                  "phonon_check_performed": False}
    if reference_record and candidate_record:
        ref_geometry_path = ART / reference["accepted_geometry_job_id"] / "final_geometry.json"
        cand_geometry_path = ART / candidate["accepted_geometry_job_id"] / "final_geometry.json"
        if ref_geometry_path.exists() and cand_geometry_path.exists():
            ref_structure = Structure.from_file(ref_geometry_path)
            cand_structure = Structure.from_file(cand_geometry_path)
            matcher = StructureMatcher(ltol=0.01, stol=0.01, angle_tol=0.5,
                                       primitive_cell=True, scale=False, attempt_supercell=True)
            match = matcher.fit(ref_structure, cand_structure)
            rms_dist = matcher.get_rms_dist(ref_structure, cand_structure)
            comparison["final_structure_match"] = {
                "primitive_supercell_aware_match": bool(match),
                "matcher_settings": {"ltol": 0.01, "stol": 0.01, "angle_tol_degrees": 0.5,
                    "primitive_cell": True, "scale": False, "attempt_supercell": True},
                "matching_only_no_execution_cell_reduction": True,
                "normalized_rms_and_max_distance": list(rms_dist) if rms_dist else None,
                "reference_final_geometry_sha256": digest(ref_geometry_path),
                "candidate_final_geometry_sha256": digest(cand_geometry_path),
                "reference_n_atoms": len(ref_structure), "candidate_n_atoms": len(cand_structure),
                "reference_spacegroup_at_symprec_0p01A": SpacegroupAnalyzer(ref_structure, symprec=0.01).get_space_group_number(),
                "candidate_spacegroup_at_symprec_0p01A": SpacegroupAnalyzer(cand_structure, symprec=0.01).get_space_group_number()}
    if complete and raw_difference is not None:
        comparison["within_10_meV_per_atom_comparison_tolerance"] = abs(raw_difference) <= 0.010
        comparison["energy_ordering_resolved_at_10_meV_tolerance"] = abs(raw_difference) > 0.010
        if abs(raw_difference) <= 0.010:
            comparison["outcome"] = "numerically_indistinguishable_known_control_recovery"
            comparison["interpretation"] = "The known MgO control recovers the reference prototype with indistinguishable energy at the recorded numerical resolution; the tiny raw difference is not an energy advantage or a new stability result"
    summary = {"schema_version": 1, "updated_at_utc": datetime.now(timezone.utc).isoformat(),
               "phase": 3, "all_jobs_finished": not canonical["qe"]["active_reservations"] and not LOCK.exists(),
               "local_QE_mutex_present": LOCK.exists(),
               "active_QE_reservations": canonical["qe"]["active_reservations"],
               "phase3_job_count": len(jobs),
               "electronic_or_process_rejected_job_ids": [row["job_id"] for row in jobs if not row["result"]["job_scf_accepted"]],
               "relaxation_jobs_rejected_by_independent_stationarity_check": [row["job_id"] for row in jobs
                   if row["settings"]["calculation"] != "scf" and not row["result"]["job_stationary_at_this_setting"]],
               "phase3_QE_wall_seconds": sum(row["elapsed_wall_seconds"] for row in jobs),
               "phase3_initial_QE_wall_ceiling_seconds": 2700,
               "canonical_QE_snapshot": canonical["qe"],
               "accepted_reference_job_id": reference["accepted_geometry_job_id"] if reference["full_numerical_convergence"] else None,
               "accepted_candidate_job_id": candidate["accepted_geometry_job_id"] if candidate["full_numerical_convergence"] else None,
               "reference_validation": reference, "candidate_validation": candidate,
               "full_numerical_convergence": complete, "known_MgO_comparison": comparison,
               "primary_CaMg2O3_status": "Eight frozen generated attempts produced zero exact six-atom eligible structures; no primary-composition DFT candidate was submitted",
               "full_hull_established": False, "fresh_DFT_confirmed_new_stable_materials": 0,
               "jobs": jobs}
    save(ART / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ["all_jobs_finished", "phase3_job_count", "phase3_QE_wall_seconds", "full_numerical_convergence", "accepted_reference_job_id", "accepted_candidate_job_id"]}, indent=2))


if __name__ == "__main__":
    main()
