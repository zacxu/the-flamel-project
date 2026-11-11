"""Reconcile frozen DFT evidence and budgets without launching numerical work.

Reads completed QE XML/stdout and immutable ledgers. Writes only Phase 6
evidence artifacts; no predictor, oracle, generator or simulation is called.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher

from phase3_qe_parser import parse_job, BOHR_ANGSTROM, HARTREE_EV

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase6/evidence"
FROZEN_PROTOCOL = "b71724ad4e9a940de090d4163bc6a23a10ed9bfb957fb656b50222b884d36c94"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def jsonl(path):
    return [json.loads(x) for x in (ROOT / path).read_text(encoding="utf-8").splitlines() if x]


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def csv_save(name, rows):
    with (OUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks, sources = [], {}

    def source(path):
        path = Path(path)
        if not path.is_absolute():
            path = ROOT / path
        path = path.resolve()
        path.relative_to(ROOT)
        sources[path.relative_to(ROOT).as_posix()] = {"sha256": sha(path), "bytes": path.stat().st_size}
        return path

    def check(name, passed, details=None):
        checks.append({"name": name, "passed": bool(passed), "details": details})

    def close(a, b, tol=1e-7):
        return a is not None and b is not None and abs(a - b) <= tol

    common = ["config/phase2_protocol.json", "artifacts/phase2/dft/numerical_protocol.json",
              "artifacts/phase2/dft/reference_plan.json", "artifacts/phase2/budgets/phase1_baseline.json",
              "artifacts/phase2/budgets/accounting_amendment.json", "artifacts/phase2/budgets/prototype_attempts.jsonl",
              "artifacts/budget_ledger.json", "artifacts/runtime_budget_events.jsonl", "artifacts/phase5/manifest.json",
              "artifacts/phase3/qe/summary.json", "artifacts/phase4/qe/summary.json", "artifacts/phase5/qe/summary.json",
              "artifacts/phase5/qe/queue_plan.json", "artifacts/phase3/qe/scope_guard_checks.json",
              "artifacts/phase4/generation/summary.json", "artifacts/phase4/generation/supplementary_mgo/summary.json",
              "artifacts/phase5/chgnet/summary.json", "artifacts/phase5/chgnet/plan.json",
              "hackathon_instructions.md", "artifacts/phase6/current_submission_requirements.md",
              "scripts/phase3_qe_parser.py", "research_budget.py", "scripts/phase6_evidence.py"]
    for path in common:
        source(path)
    protocol = read("config/phase2_protocol.json")
    budget = read("artifacts/budget_ledger.json")
    baseline = read("artifacts/phase2/budgets/phase1_baseline.json")
    phase5 = read("artifacts/phase5/manifest.json")["phase5_end_budget"]
    events = jsonl("artifacts/runtime_budget_events.jsonl")
    starts = {x["reservation_id"]: x for x in events if x["event"] == "reserved"}
    finishes = {x["reservation_id"]: x for x in events if x["event"] == "finished"}
    check("protocol_sha256_unchanged", sha(ROOT / "config/phase2_protocol.json") == FROZEN_PROTOCOL)
    check("phase5_end_budget_unchanged", sha(ROOT / "artifacts/budget_ledger.json") == phase5["budget_ledger_sha256"])
    check("phase5_end_runtime_events_unchanged", sha(ROOT / "artifacts/runtime_budget_events.jsonl") == phase5["runtime_events_sha256"])
    check("runtime_event_count_unchanged", len(events) == phase5["runtime_event_count"] == 82)
    check("every_runtime_reservation_finished_once", len(starts) == len(finishes) == len(events) // 2 and starts.keys() == finishes.keys())
    stop = datetime.fromisoformat(budget["numerical_stop_utc"])
    check("original_hour18_stop_preserved", stop.isoformat() == "2026-10-22T10:24:44+00:00")
    for reservation_id, start in starts.items():
        finish = finishes[reservation_id]
        check(reservation_id + ":reservation_precedes_finish", datetime.fromisoformat(start["reserved_utc"]) <= datetime.fromisoformat(finish["finished_utc"]))
        check(reservation_id + ":finished_before_original_stop", datetime.fromisoformat(finish["finished_utc"]) <= stop)
        check(reservation_id + ":runtime_fits_reserved_watchdog", finish["wall_seconds"] <= start["max_seconds"])
        check(reservation_id + ":phase_lane_attempts_reconcile", all(start[k] == finish[k] for k in ("phase", "lane", "attempts")))

    # Reconstruct all attempt charges from raw baseline ledgers and append-only reservations.
    generator = jsonl("artifacts/phase1/generator/ledger.jsonl")
    prototypes = jsonl("artifacts/phase2/budgets/prototype_attempts.jsonl")
    chg1 = jsonl("artifacts/phase1/chgnet/ledger.jsonl")
    chg2 = jsonl("artifacts/phase1/chgnet_relaxation/ledger.jsonl")
    for path in ["artifacts/phase1/generator/ledger.jsonl", "artifacts/phase1/chgnet/ledger.jsonl",
                 "artifacts/phase1/chgnet_relaxation/ledger.jsonl", "artifacts/phase1/qe/qe_jobs.jsonl"]:
        source(path)
    phase1_draws = next(x["attempts"] for x in generator if x["event"] == "run_completed")
    gen_new = sum(x["attempts"] for x in starts.values() if x["lane"] == "generation")
    prototype_count = sum(x["attempts_charged"] for x in prototypes)
    charged_generation = phase1_draws + prototype_count + gen_new
    generation_summary = read("artifacts/phase4/generation/summary.json")
    supplementary = read("artifacts/phase4/generation/supplementary_mgo/summary.json")
    actual_draws = generation_summary["all_primary_actual_draws"] + supplementary["new_actual_draws"]
    check("generation_charges_reconstructed", charged_generation == budget["generation"]["charged_attempts"] == 96)
    check("generation_actual_vs_charged", actual_draws == 88 and charged_generation - actual_draws - prototype_count == 4)
    check("generation_remaining_and_cap", budget["generation"]["remaining_attempts"] == 128 - charged_generation == 32)
    check("prototype_preparations_charged_once", prototype_count == 4 and len({x["attempt_id"] for x in prototypes}) == 4)
    for row in prototypes:
        check(row["attempt_id"] + ":original_prepared_candidate_hash", sha(source(row["candidate_path"])) == row["candidate_sha256"])
    phase1_chg = [x for x in chg1 + chg2 if x["event"] == "finish"]
    new_chg = [x for x in starts.values() if x["lane"] == "chgnet"]
    total_chg = len(phase1_chg) + sum(x["attempts"] for x in new_chg)
    chg_wall = sum(x["budget_charged_seconds"] for x in phase1_chg) + sum(finishes[x["reservation_id"]]["wall_seconds"] for x in new_chg)
    check("CHGNet_conservative_launch_charges", total_chg == budget["chgnet"]["charged_attempts"] == 19)
    check("CHGNet_failed_launcher_charges_retained", sum(x["status"] == "failed" for x in phase1_chg) == budget["chgnet"]["pre_model_launcher_rejections"] == 4)
    check("CHGNet_actual_model_relaxations", sum(x["status"] == "completed" for x in phase1_chg) + len(new_chg) == budget["chgnet"]["actual_relaxations"] == 15)
    check("CHGNet_entire_subprocess_wall_reconciled", close(chg_wall, budget["chgnet"]["charged_wall_seconds"]))
    check("CHGNet_attempt_and_wall_caps", total_chg <= 40 and chg_wall <= 14400 and budget["chgnet"]["remaining_attempts"] == 40 - total_chg)
    categories = Counter()
    for row in new_chg:
        categories[row["category"]] += row["attempts"]
    category_caps = {"symmetry": 10, "new_composition_shortlist": 12, "prototype": 4, "same_composition_reference": 4, "contingency": 2}
    category_rows = []
    for category, ceiling in category_caps.items():
        charged = categories[category]
        check("CHGNet_category_" + category, charged <= ceiling and charged == budget["chgnet"]["phase3_and_later_category_charged_attempts"][category])
        category_rows.append({"category": category, "ceiling": ceiling, "charged": charged, "unused": ceiling - charged})
    chg = read("artifacts/phase5/chgnet/summary.json")
    check("cached_MgO_reused_without_double_charge", chg["cached_reuses"] == 1 and chg["new_CHGNet_launches"] == 10 and len(new_chg) == 11)
    check("fresh_transformer_shortlist_remains_empty", chg["fresh_transformer_shortlist_relaxations"] == 0)
    for lane in ("generation", "chgnet", "qe"):
        check(lane + ":no_active_reservations", not budget[lane]["active_reservations"])
    check("QE_mutex_absent", not (ROOT / "artifacts/phase1/qe/qe_active.lock").exists())

    summaries = {phase: read(f"artifacts/phase{phase}/qe/summary.json") for phase in (3, 4, 5)}
    records = jsonl("artifacts/phase1/qe/qe_jobs.jsonl")
    check("all_19_QE_attempts_retained", len(records) == len({x["job_id"] for x in records}) == budget["qe"]["completed_jobs"] == 19)
    check("QE_entire_job_wall_reconciled", close(sum(x["elapsed_wall_seconds"] for x in records), budget["qe"]["charged_wall_seconds"]))
    check("QE_time_cap_and_remaining", budget["qe"]["charged_wall_seconds"] <= 21600 and close(21600 - budget["qe"]["charged_wall_seconds"], budget["qe"]["remaining_seconds"]))
    chronological = sorted(records, key=lambda x: x["started_at_utc"])
    check("single_QE_job_at_a_time", all(datetime.fromisoformat(a["finished_at_utc"]) <= datetime.fromisoformat(b["started_at_utc"]) for a, b in zip(chronological, chronological[1:])))
    accepted_ids = {"p3_ref_mgo_90_k035_cont1", "p3_candidate_mgo_fallback_90", "p4_ref_cao_90_k035"}
    parsed, job_records, table = {}, {}, []
    pilot = records[0]
    pilot_dir = ROOT / "artifacts/phase1/qe/mgo_scf_pilot"
    pilot_xml = source(pilot_dir / "scratch/mgo_phase1.save/data-file-schema.xml")
    output = ET.parse(pilot_xml).getroot().find("output")
    pilot_energy = float(output.findtext("total_energy/etot")) * HARTREE_EV / 2
    pilot_scf = output.findtext("convergence_info/scf_conv/convergence_achieved").strip().lower() == "true"
    check("pilot_stdout_hash", sha(source(pilot_dir / "mgo.scf.out")) == pilot["output_sha256"])
    check("pilot_input_hash", sha(source(pilot_dir / "mgo.scf.in")) == pilot["input_sha256"])
    check("pilot_XML_energy_and_SCF_reproduced", pilot_scf and close(pilot_energy, pilot["energy_eV_per_atom"], 1e-6))
    table.append({"job_id": pilot["job_id"], "phase": 1, "role": "known_MgO_engine_pilot", "formula": "MgO", "n_atoms": 2,
        "calculation": "scf", "exit_code": pilot["return_code"], "JOB_DONE": pilot["qe_job_done"], "terminal_SCF_accepted": pilot_scf,
        "stationary_at_this_setting": False, "accepted_with_final_geometry_sensitivity": False, "energy_eV_per_atom": pilot_energy,
        "max_force_eV_A": "", "max_full_stress_kbar": "", "cutoff_Ry": 50, "density_cutoff_Ry": 400, "k_mesh": "4x4x4",
        "elapsed_wall_seconds": pilot["elapsed_wall_seconds"], "evidence_level": "fixed_geometry_engine_readiness_only", "source_result": "artifacts/phase1/qe/mgo_scf_pilot_result.json"})
    for phase, summary in summaries.items():
        for row in summary["jobs"]:
            path = source(row["path"] if "path" in row else f"artifacts/phase{phase}/qe/{row['job_id']}/result.json")
            record = json.loads(path.read_text(encoding="utf-8"))
            directory = path.parent
            settings = record["provenance"]["settings"]
            result = parse_job(directory, settings, return_code=record["return_code"], timed_out=record["timed_out"], write_geometry=False)
            job_id = row["job_id"]
            parsed[job_id], job_records[job_id] = result, record
            source(result["xml_path"])
            check(job_id + ":stdout_hash", sha(source(directory / "pw.out")) == record["output_sha256"])
            check(job_id + ":input_hash", sha(source(directory / "pw.in")) == record["provenance"]["input_sha256"])
            check(job_id + ":settings_hash", sha(source(directory / "settings.json")) == record["provenance"]["settings_sha256"])
            check(job_id + ":source_geometry_hash", sha(source(record["provenance"]["source_geometry"])) == record["provenance"]["source_geometry_sha256"])
            for element, filename in record["provenance"]["pseudo_files"].items():
                check(job_id + ":pseudo_" + element, sha(source(directory / "pseudo" / filename)) == record["provenance"]["pseudo_hashes"][element])
            for key in ("job_scf_accepted", "job_stationary_at_this_setting", "energy_eV_per_atom", "max_force_vector_norm_eV_per_angstrom", "max_absolute_residual_stress_component_kbar"):
                check(job_id + ":reparse_" + key, result.get(key) == record["result"].get(key))
            check(job_id + ":reservation_and_actual_elapsed_match", job_id in starts and close(record["elapsed_wall_seconds"], finishes[job_id]["wall_seconds"]))
            check(job_id + ":one_legacy_entry", sum(x["job_id"] == job_id for x in records) == 1)
            check(job_id + ":four_threads_one_MPI", result["reported_threads_per_MPI_process"] == 4 and result["reported_MPI_processes"] == 1)
            evidence = "accepted_relaxed_geometry_with_finite_sensitivity" if job_id in accepted_ids else (
                "incomplete_terminal_SCF_no_accepted_final_energy" if not result["job_scf_accepted"] else (
                    "fixed_geometry_SCF_sensitivity_only" if settings["calculation"] == "scf" else (
                        "preliminary_stationary_setting_only" if result["job_stationary_at_this_setting"] else "SCF_passed_independent_stationarity_failed")))
            table.append({"job_id": job_id, "phase": phase, "role": record["provenance"]["role"], "formula": result.get("formula", "MgO" if phase == 5 else ""),
                "n_atoms": settings["nat"], "calculation": settings["calculation"], "exit_code": record["return_code"], "JOB_DONE": result["job_done"],
                "terminal_SCF_accepted": result["job_scf_accepted"], "stationary_at_this_setting": result["job_stationary_at_this_setting"],
                "accepted_with_final_geometry_sensitivity": job_id in accepted_ids, "energy_eV_per_atom": result.get("energy_eV_per_atom", ""),
                "max_force_eV_A": result.get("max_force_vector_norm_eV_per_angstrom", ""), "max_full_stress_kbar": result.get("max_absolute_residual_stress_component_kbar", ""),
                "cutoff_Ry": settings["ecutwfc_Ry"], "density_cutoff_Ry": settings["ecutrho_Ry"], "k_mesh": "x".join(map(str, settings["k_mesh"])),
                "elapsed_wall_seconds": record["elapsed_wall_seconds"], "evidence_level": evidence, "source_result": path.relative_to(ROOT).as_posix()})
    check("DFT_evidence_table_contains_every_job_once", len(table) == 19 and {x["job_id"] for x in table} == {x["job_id"] for x in records})
    sensitivity_sets = [
        ("p3_ref_mgo_90_k035_cont1", "p3_mgo_final_final_cut75", "p3_mgo_final_final_k045"),
        ("p3_candidate_mgo_fallback_90", "p3_fallback_final_final_cut75", "p3_fallback_final_final_k045"),
        ("p4_ref_cao_90_k035", "p4_cao_final_cut75", "p4_cao_final_k045")]
    sensitivity = []
    accepted_pseudos = {}
    for base_id, cut_id, k_id in sensitivity_sets:
        base, stage = parsed[base_id], job_records[base_id]["provenance"]
        check(base_id + ":independent_final_setting_stationarity", base["job_stationary_at_this_setting"])
        check(base_id + ":90_720_Ry_spacing035", stage["settings"]["ecutwfc_Ry"] == 90 and stage["settings"]["ecutrho_Ry"] == 720 and stage["settings"]["k_spacing_start_inv_angstrom"] == .35)
        check(base_id + ":PBE_and_frozen_electronic_threshold", stage["settings"]["input_dft"] == "PBE" and stage["settings"]["conv_thr_Ry"] == 1e-8)
        check(base_id + ":unconstrained_nonmagnetic_oxide", stage["settings"]["nosym"] and stage["settings"]["noinv"] and stage["settings"]["nspin"] == 1 and stage["settings"]["occupations"] == "fixed")
        for element, digest in stage["pseudo_hashes"].items():
            check(base_id + ":compatible_accepted_pseudo_" + element, element not in accepted_pseudos or accepted_pseudos[element] == digest)
            accepted_pseudos[element] = digest
        shifts = {}
        for kind, probe_id in (("cutoff", cut_id), ("kpoint", k_id)):
            probe, probe_stage = parsed[probe_id], job_records[probe_id]["provenance"]
            geom = ROOT / f"artifacts/phase{job_records[base_id]['phase']}/qe/{base_id}/final_geometry.json"
            delta = abs(base["energy_eV_per_atom"] - probe["energy_eV_per_atom"])
            check(probe_id + ":same_accepted_final_geometry", probe_stage["source_geometry_sha256"] == sha(source(geom)))
            check(probe_id + ":SCF_accepted_and_shift_under5meV", probe["job_scf_accepted"] and delta <= .005)
            check(probe_id + ":same_functional_and_pseudos", probe_stage["settings"]["input_dft"] == stage["settings"]["input_dft"] and probe_stage["pseudo_hashes"] == stage["pseudo_hashes"])
            if kind == "kpoint":
                check(probe_id + ":distinct_actual_mesh", stage["settings"]["k_mesh"] != probe_stage["settings"]["k_mesh"])
                check(probe_id + ":only_k_spacing_probe", probe_stage["settings"]["ecutwfc_Ry"] == 90 and probe_stage["settings"]["ecutrho_Ry"] == 720 and probe_stage["settings"]["k_spacing_start_inv_angstrom"] == .45)
            else:
                check(probe_id + ":only_cutoff_probe", probe_stage["settings"]["ecutwfc_Ry"] == 75 and probe_stage["settings"]["ecutrho_Ry"] == 600 and probe_stage["settings"]["k_mesh"] == stage["settings"]["k_mesh"])
            shifts[kind + "_shift_eV_atom"] = delta
        sensitivity.append({"accepted_job_id": base_id, "energy_eV_atom": base["energy_eV_per_atom"],
            "force_eV_A": base["max_force_vector_norm_eV_per_angstrom"], "full_stress_kbar": base["max_absolute_residual_stress_component_kbar"], **shifts})
    known_delta = parsed["p3_candidate_mgo_fallback_90"]["energy_eV_per_atom"] - parsed["p3_ref_mgo_90_k035_cont1"]["energy_eV_per_atom"]
    comparison = summaries[3]["known_MgO_comparison"]
    check("MgO_tiny_difference_reproduced", close(known_delta, comparison["raw_candidate_minus_reference_eV_per_atom"]))
    check("MgO_energy_ordering_not_resolved", abs(known_delta) < .01 and not comparison["energy_ordering_resolved_at_10_meV_tolerance"])
    matcher = StructureMatcher(ltol=.01, stol=.01, angle_tol=.5, primitive_cell=True, scale=False, attempt_supercell=True)
    reference = Structure.from_file(ROOT / parsed["p3_ref_mgo_90_k035_cont1"]["final_geometry_json"])
    candidate = Structure.from_file(ROOT / parsed["p3_candidate_mgo_fallback_90"]["final_geometry_json"])
    check("MgO_final_known_phase_recovery_reproduced", matcher.fit(reference, candidate))
    check("invalid_intermediate_MgO_relaxation_not_accepted", not parsed["p3_ref_mgo_90_k035"]["job_stationary_at_this_setting"] and "p3_ref_mgo_90_k035" not in accepted_ids)
    failed = parsed["p5_mgo_perturb_90"]
    check("JOB_DONE_is_not_convergence", failed["return_code"] == 0 and failed["job_done"] and not failed["job_scf_accepted"])
    check("failed_terminal_perturbation_energy_is_not_used", "energy_eV_per_atom" not in failed and summaries[5]["known_control_comparison"] is None)
    check("SCF_failure_halts_frozen_perturbation_queue", summaries[5]["phase5_QE_job_count"] == 1 and not summaries[5]["final_geometry_sensitivity_checks"] and summaries[5]["accepted_perturbation_job_id"] is None)
    check("failed_perturbation_still_charged", finishes["p5_mgo_perturb_90"]["status"] == "failed" and finishes["p5_mgo_perturb_90"]["wall_seconds"] > 900)

    # Retain the complete inventory, including costly and spin-ambiguous entries.
    inventory_rows, coverage = [], {}
    completed_reference_ids = {"mp-1265": "p3_ref_mgo_90_k035_cont1", "mp-2605": "p4_ref_cao_90_k035"}
    for system, filename in (("Ca-Mg-O", "primary_reference_plan.json"), ("Mg-O", "fallback_Mg-O_reference_plan.json")):
        plan_path = source("artifacts/phase2/dft/" + filename)
        entries = json.loads(plan_path.read_text(encoding="utf-8"))["records"]
        completed = 0
        for entry in entries:
            material_id = entry["material_id"]
            accepted = material_id in completed_reference_ids
            completed += accepted
            check(system + ":" + material_id + ":original_source_geometry_retained", sha(source(entry["execution_geometry_path"])) == entry["execution_geometry_sha256"])
            if accepted:
                first_job = "p3_ref_mgo_base" if material_id == "mp-1265" else "p3_ref_cao_base"
                check(system + ":" + material_id + ":source_reference_lineage", job_records[first_job]["provenance"]["source_geometry_sha256"] == entry["execution_geometry_sha256"])
            inventory_rows.append({"inventory_system": system, "material_id": material_id, "formula": entry["reduced_formula"], "chemical_system": entry["chemical_system"],
                "execution_n_sites": entry["execution_n_sites"], "spin_review_required": entry["spin_review_required"], "expensive_reference_flag": entry["expensive_reference_flag"],
                "elemental_endpoint_entry": len(entry["elements"]) == 1, "accepted_fresh_compatible_QE": accepted,
                "accepted_job_id": completed_reference_ids.get(material_id, ""), "status": "accepted_relaxed_and_finite_checked" if accepted else "uncomputed_fresh_compatible_QE",
                "blocks_full_inventory_hull": not accepted, "original_source_geometry": entry["execution_geometry_path"]})
        coverage[system] = {"frozen_entries": len(entries), "accepted_fresh_compatible_QE": completed, "missing": len(entries) - completed,
            "full_inventory_complete": completed == len(entries), "missing_spin_review_entries": sum(x["spin_review_required"] and not x["accepted_fresh_compatible_QE"] for x in inventory_rows if x["inventory_system"] == system),
            "missing_elemental_entries": sum(x["elemental_endpoint_entry"] and not x["accepted_fresh_compatible_QE"] for x in inventory_rows if x["inventory_system"] == system)}
    check("primary_coverage_two_of161", coverage["Ca-Mg-O"]["accepted_fresh_compatible_QE"] == 2 and coverage["Ca-Mg-O"]["missing"] == 159)
    check("fallback_coverage_one_of57", coverage["Mg-O"]["accepted_fresh_compatible_QE"] == 1 and coverage["Mg-O"]["missing"] == 56)
    check("all_incomplete_entries_explicitly_listed", len(inventory_rows) == 218 and sum(x["blocks_full_inventory_hull"] for x in inventory_rows) == 215)
    guards = read("artifacts/phase3/qe/scope_guard_checks.json")
    check("O2_and_metals_require_separate_authorization", guards["all_rejected_before_job_creation"] and {x["case"] for x in guards["cases"]} == {"pure_O2", "metal_explicit"})
    check("no_original_queue_candidate_left_pending", chg["fresh_transformer_shortlist_relaxations"] == 0
          and "no primary-composition DFT candidate was submitted" in summaries[3]["primary_CaMg2O3_status"]
          and all(row["formula"] != "CaMg2O3" for row in table))
    check("no_full_hull_or_new_stable_material_claim", not summaries[3]["full_hull_established"] and not summaries[5]["full_frozen_inventory_hull_established"] and summaries[5]["new_stable_materials"] == 0)

    claims = [
        {"claim": "Retrospective acquisition comparison", "status": "supported_in_historical_replay", "scope": "Fixed WBM labels and equal per-policy query budgets; distinct from freshly run DFT", "limitation": "No fresh discovery efficiency or arbitrary OOD guarantee"},
        {"claim": "Symmetry sampling policy comparison", "status": "supported_descriptive", "scope": "Frozen controls and first-eight primary denominators; supplementary MgO kept separate", "limitation": "No training-architecture causal ablation"},
        {"claim": "Symmetry-pair CHGNet energy difference", "status": "supported_one_pair_each", "scope": "Within-composition model energies, one relaxed selection per arm", "limitation": "No energy-distribution estimate or DFT validation of symmetry pairs"},
        {"claim": "Fresh known MgO phase recovery", "status": "supported", "scope": "Relaxed generated eight-atom control matches relaxed original-source two-atom MgO", "limitation": "Tiny energy difference is numerically unresolved; known phase"},
        {"claim": "Compatible CaO and MgO oxide anchors", "status": "supported", "scope": "90/720 Ry PBE, final-setting stationarity plus finite cutoff/k checks", "limitation": "No CaMg2O3 QE energy, therefore no candidate reaction energy"},
        {"claim": "New composition absent from checked catalogs", "status": "scoped_catalog_evidence_only", "scope": "Named WBM and MP releases, frozen formulas", "limitation": "Absence is not global novelty, generator-training absence or stable discovery"},
        {"claim": "New DFT-confirmed stable material", "status": "not_established", "scope": "Zero qualifying fresh CrystalFormer new-formula candidates", "limitation": "No new-composition QE relaxation or complete reference competition"},
        {"claim": "Full frozen-inventory DFT hull", "status": "not_established", "scope": "Primary 2/161 and fallback 1/57 accepted source entries", "limitation": "Elemental metals, oxygen, spin/occupation and other phases remain missing"},
        {"claim": "Perturbation recovery or local minimum", "status": "incomplete", "scope": "One known MgO perturbation stopped at frozen 900-second limit", "limitation": "No accepted terminal SCF/forces/stress; no continuation allowed; no phonons"},
        {"claim": "Experimental or finite-temperature stability", "status": "not_tested", "scope": "Static approximate PBE evidence only", "limitation": "No synthesis, finite-temperature free energies or phonon calculations"},
    ]
    stop_decision = {
        "decision": "Close numerical evidence now and preserve unused allocations",
        "required_allowed_unfinished_job_count": 0,
        "new_numerical_jobs_dispatched_phase6": 0,
        "reason": "Accepted oxide/control geometries already have all required final-setting checks. No valid frozen new-formula candidate exists. The terminal SCF failure closes the bounded perturbation queue; no continuation or probe is allowed. Broader reference inventory is incomplete, with metal/O2/spin branches outside authorized oxide runners. Unused budgets do not authorize revised candidates, gates, retries or chemistry.",
        "optional_inventory_work": "The frozen catalog lists preparatory metal/O2/reference work, but no complete-hull outcome was promised and no qualifying primary candidate remains. These entries remain explicitly missing; no extra queue or protocol is invented to spend unused time.",
        "numerical_stop_utc_unchanged": budget["numerical_stop_utc"],
        "early_closure_does_not_relax_failed_checks": True,
    }
    rows = [{"lane": "generation", "cap": 128, "charged": charged_generation, "remaining": 128 - charged_generation, "unit": "conservative_structure_slots", "interpretation": "88 actual CrystalFormer draws + 4 prototypes + 4 unemitted engineering charges"},
            {"lane": "chgnet_attempts", "cap": 40, "charged": total_chg, "remaining": 40 - total_chg, "unit": "conservative_launch_slots", "interpretation": "15 actual model relaxations + 4 pre-model failures; cached selections not recharged"},
            {"lane": "chgnet_wall", "cap": 14400, "charged": chg_wall, "remaining": 14400 - chg_wall, "unit": "seconds", "interpretation": "Entire subprocess walltime including imports, model load and failures"},
            {"lane": "QE_wall", "cap": 21600, "charged": budget["qe"]["charged_wall_seconds"], "remaining": budget["qe"]["remaining_seconds"], "unit": "seconds", "interpretation": "All 19 actual jobs including pilot, sensitivities and incomplete perturbation"}]
    csv_save("fresh_DFT_evidence_table.csv", table)
    csv_save("reference_inventory_completeness.csv", inventory_rows)
    csv_save("missing_reference_inventory.csv", [x for x in inventory_rows if not x["accepted_fresh_compatible_QE"]])
    csv_save("claim_matrix.csv", claims)
    csv_save("budget_reconciliation.csv", rows)
    csv_save("CHGNet_category_caps.csv", category_rows)
    save("numerical_stop_decision.json", stop_decision)
    save("source_hashes.json", {"scope": "Frozen inputs consumed by this read-only analysis; no simulation/model dispatch", "files": [{"path": p, **v} for p, v in sorted(sources.items())]})
    failed_checks = [x for x in checks if not x["passed"]]
    summary = {"phase": 6, "lane": "DFT_budget_and_claim_evidence", "status": "passed" if not failed_checks else "failed", "created_utc": datetime.now(timezone.utc).isoformat(),
        "checks_total": len(checks), "checks_passed": len(checks) - len(failed_checks), "failed_checks": failed_checks,
        "all_QE_jobs": len(table), "fresh_QE_relaxed_geometries_with_final_finite_checks": sensitivity,
        "known_MgO_candidate_minus_reference_eV_atom": known_delta, "known_MgO_energy_ordering_resolved": False,
        "known_MgO_final_reference_structure_match": bool(matcher.fit(reference, candidate)),
        "finite_check_scope": "Measured adjacent cutoff/k changes and final-setting stationarity, not a rigorous total DFT error bound",
        "primary_reaction": {"equation": "CaMg2O3 -> CaO + 2 MgO", "anchor_weighted_energy_eV_atom": (parsed["p4_ref_cao_90_k035"]["energy_eV_per_atom"] + 2 * parsed["p3_ref_mgo_90_k035_cont1"]["energy_eV_per_atom"]) / 3, "candidate_energy_available": False, "reaction_energy_available": False},
        "reference_coverage": coverage, "isolated_O2_and_metal_checks_complete": False, "ground_spin_review_complete_for_inventory": False,
        "perturbation_validation_complete": False, "phonon_calculation_performed": False, "full_hull_established": False, "new_stable_material_established": False,
        "budget_rows": rows, "CHGNet_category_rows": category_rows, "numerical_decision": stop_decision,
        "submission_requirements_source": "artifacts/phase6/current_submission_requirements.md",
        "requirements_scope": "Root checked current official agenda/submission page; public/account/submission actions remain for later user-authorized work",
        "source_hashes": "artifacts/phase6/evidence/source_hashes.json", "source_file_count": len(sources),
        "no_numerical_or_oracle_jobs": True, "frozen_phase5_end_state_unchanged": True}
    save("summary.json", summary)
    save("audit.json", {**{k: summary[k] for k in ("phase", "lane", "status", "created_utc", "checks_total", "checks_passed", "failed_checks")}, "checks": checks})
    print(json.dumps({k: summary[k] for k in ("status", "checks_total", "checks_passed", "failed_checks", "all_QE_jobs", "source_file_count")}))
    return 0 if not failed_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
