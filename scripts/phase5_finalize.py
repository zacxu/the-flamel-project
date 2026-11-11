"""Consolidate completed Phase 5 evidence without dispatching numerical work.

This command reads saved model-relaxation trajectories and QE XML. It only
writes artifacts/phase5/{audit,readiness,manifest}.json and refuses to rewrite
the historical close after another numerical phase or ledger change.
"""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import re
import sys
from urllib.parse import unquote

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "artifacts/phase5"
PROTOCOL_SHA = "b71724ad4e9a940de090d4163bc6a23a10ed9bfb957fb656b50222b884d36c94"
ACQUISITION_SHA = "68374dd88f03cf6f3652c79a46774993bdc3bb936459da214870ddfec07e1f7c"
FRESH_SHA = "b7cbae9c54cdc486bac5d9de743f3e75e2322bf7bf01a3f03f7b92acfa3e8359"
CHECKPOINT_SHA = "d14ab7c0f093efe64b60a7bcd540bca10e74fb7f46c86108a079af60524659d1"
CHECKS = []
INVENTORY = {}


def path(value):
    value = Path(value)
    result = value if value.is_absolute() else ROOT / value
    if not result.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Audit input outside the workspace")
    return result


def sha(value):
    source = path(value)
    key = source.relative_to(ROOT).as_posix()
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    INVENTORY[key] = {"path": key, "sha256": digest, "bytes": source.stat().st_size}
    return digest


def read(value):
    source = path(value)
    sha(source)
    return json.loads(source.read_text(encoding="utf-8"))


def lines(value):
    source = path(value)
    sha(source)
    return [json.loads(row) for row in source.read_text(encoding="utf-8").splitlines() if row.strip()]


def save(name, value):
    if name not in {"audit.json", "readiness.json", "manifest.json"}:
        raise ValueError("The finalizer may only write its three closure artifacts")
    temporary = OUT / (name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, OUT / name)


def check(condition, description, **detail):
    CHECKS.append({"check": description, "passed": bool(condition), **detail})


def close(a, b, tolerance=1e-7):
    return abs(float(a) - float(b)) <= tolerance


def audit_chgnet(starts, finishes):
    import numpy as np
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.filters import FrechetCellFilter
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.core import Structure
    from pymatgen.io.ase import AseAtomsAdaptor

    plan = read("artifacts/phase5/chgnet/plan.json")
    summary = read("artifacts/phase5/chgnet/summary.json")
    audit = read("artifacts/phase5/chgnet/audit.json")
    check(audit["status"] == "passed" and not audit["failures"] and audit["new_model_inferences"] == audit["new_relaxations"] == 0,
          "CHGNet lane saved-trajectory audit passed without new inference")
    check(plan["protocol_sha256"] == PROTOCOL_SHA and summary["plan_sha256"] == sha("artifacts/phase5/chgnet/plan.json"),
          "CHGNet plan and summary bind the frozen scientific protocol")
    check(plan["selections"] == summary["selections"] == 11 and plan["new_jobs"] == summary["new_CHGNet_launches"] == 10
          and plan["cached_reuses"] == summary["cached_reuses"] == 1, "Eleven experimental selections, ten new launches and one cache reuse")
    check(Counter(row["category"] for row in plan["jobs"]) == Counter(symmetry=4, prototype=4, same_composition_reference=3),
          "Selected cohort is four symmetry, four prototype and three reference structures")
    symmetry_plan = read("artifacts/phase4/selection/symmetry_relaxation_plan.json")
    frozen_symmetry = {chosen["candidate_id"]: chosen for control in symmetry_plan["controls"]
                       for arm in control["arms"] for chosen in arm["selected"]}
    check({row["candidate_id"] for row in plan["jobs"] if row["category"] == "symmetry"} == set(frozen_symmetry),
          "The symmetry experiment uses exactly the earlier random within-arm selections")
    prototype_charges = {row["attempt_id"]: row for row in lines("artifacts/phase2/budgets/prototype_attempts.jsonl")}
    check({row["candidate_id"] for row in plan["jobs"] if row["category"] == "prototype"} == set(prototype_charges),
          "The four prototype baselines are exactly the originals charged once in Phase2")
    settings = plan["settings"]
    expected = {"package": "0.4.2", "model_version": "0.3.0", "checkpoint_sha256": CHECKPOINT_SHA,
                "device": "cuda", "torch_threads": 2, "torch_interop_threads": 1, "torch_seed": 20261022,
                "optimizer": "FIRE", "steps_max": 200, "fmax_eV_A": .05, "relax_cell": True,
                "ase_filter": "FrechetCellFilter", "imposed_symmetry": False, "on_isolated_atoms": "error"}
    check(all(settings.get(key) == value for key, value in expected.items()), "All cached and new CHGNet numerical settings match the frozen worker")
    check(sha(".envs/analysis/Lib/site-packages/chgnet/pretrained/0.3.0/chgnet_0.3.0_e29f68s314m37.pth.tar") == CHECKPOINT_SHA,
          "The checkpoint bytes used by cached and new CHGNet jobs remain identical")
    for record in plan["inputs"] + plan["source_manifest"]:
        check(sha(record["path"]) == record["sha256"], "CHGNet frozen source/input hash: " + record["path"])
        if record.get("archive"):
            check(sha(record["archive"]) == record["sha256"], "CHGNet archived executed source: " + record["archive"])
    worker_source = path(settings["worker_source"])
    worker_ast = next(node for node in ast.parse(worker_source.read_text(encoding="utf-8")).body
                      if isinstance(node, ast.FunctionDef) and node.name == "worker")
    check(hashlib.sha256(ast.dump(worker_ast).encode()).hexdigest() == settings["worker_function_AST_sha256"],
          "The reused Phase3 numerical worker function is unchanged")
    phase5 = [row for row in starts.values() if row["phase"] == 5 and row["lane"] == "chgnet"]
    check(len(phase5) == 10 and Counter(row["category"] for row in phase5) == Counter(symmetry=3, prototype=4, same_composition_reference=3),
          "Exactly the ten predeclared new CHGNet attempts were charged to their original categories")
    check({row["reservation_id"] for row in phase5} == {row["job_id"] for row in plan["jobs"] if not row["cached"]},
          "No CHGNet replacement, retry or invisible shortlist launch occurred")
    results = {}
    check(len(summary["results"]) == 11 and {row["selection"]["candidate_id"] for row in summary["results"]} ==
          {row["candidate_id"] for row in plan["jobs"]}, "Every predeclared CHGNet selection has exactly one recorded outcome")
    for entry in summary["results"]:
        selected, result = entry["selection"], entry["result"]
        name = selected["candidate_id"]
        results[name] = entry
        check(selected in plan["jobs"], "Recorded CHGNet selection belongs to frozen plan: " + name)
        if selected["category"] == "symmetry":
            check(selected["source_structure_sha256"] == frozen_symmetry[name]["source_structure_sha256"],
                  "The earlier selected symmetry source is unchanged: " + name)
        if selected["category"] == "prototype":
            check(selected["original_source_sha256"] == prototype_charges[name]["candidate_sha256"] and
                  selected["structure_budget_already_charged_phase2"], "The original prototype generation charge is reused: " + name)
        for source, expected_hash in [(selected["source_structure"], selected["source_structure_sha256"]),
                                      (selected["original_source"], selected["original_source_sha256"]),
                                      (entry["result_path"], entry["result_sha256"])]:
            check(sha(source) == expected_hash, "CHGNet source/result checksum: " + source)
        parent = read(path(entry["result_path"]).parent / "parent_result.json")
        if not result:
            check(parent["status"] in {"failed", "timeout", "aborted"}, "Missing numerical result is retained as failed outcome: " + name)
            continue
        check(result["source_structure_sha256"] == selected["source_structure_sha256"] and
              result["checkpoint_sha256"] == CHECKPOINT_SHA and result["model_version"] == "0.3.0" and result["device"] == "cuda",
              "Executed CHGNet source/checkpoint/device lineage: " + name)
        initial = Structure.from_dict(read(selected["source_structure"]))
        final = Structure.from_dict(read(result["final_structure"]))
        check(sha(result["final_structure"]) == result["final_structure_sha256"] and initial.composition == final.composition
              and len(initial) == len(final) == result["atoms"], "CHGNet preserves actual cell counts and composition: " + name)
        trajectory_path = path(entry["result_path"]).parent / "trajectory.pkl"
        sha(trajectory_path)
        with trajectory_path.open("rb") as stream:
            trajectory = pickle.load(stream)
        total = float(trajectory["energy"][-1])
        check(close(total, result["energy_total_eV"], 1e-9) and close(total / len(final), result["energy_eV_per_atom"], 1e-10),
              "Saved total energy is divided by actual atom count: " + name)
        atomic_force = float(np.linalg.norm(trajectory["forces"][-1], axis=1).max())
        stress = float(np.abs(trajectory["stresses"][-1]).max() * 160.21766208)
        check(close(atomic_force, result["final_atomic_force_norm_max_eV_A"], 1e-8)
              and close(stress, result["final_stress_max_abs_GPa"], 1e-8), "Saved CHGNet force/stress units agree: " + name)
        atoms = AseAtomsAdaptor.get_atoms(initial)
        cell_filter = FrechetCellFilter(atoms)
        atoms.set_cell(trajectory["cell"][-1], scale_atoms=False)
        atoms.set_positions(trajectory["atom_positions"][-1])
        atoms.calc = SinglePointCalculator(atoms, energy=total, forces=np.asarray(trajectory["forces"][-1]), stress=np.asarray(trajectory["stresses"][-1]))
        filter_force = float(np.linalg.norm(cell_filter.get_forces(), axis=1).max())
        check(close(filter_force, result["final_filter_fmax_eV_A"], 2e-5) and bool(result["converged"]) == (filter_force <= .05)
              and result["optimizer_steps"] <= 200, "Cell-filter convergence independently reconstructed: " + name)
        if selected["cached"]:
            check(name == "phase1_mgo_attempt_000" and not any(row["metadata"].get("candidate_id") == name for row in phase5)
                  and entry["charged_wall_seconds_this_phase"] == 0 and selected["prior_reservation_id"] in starts,
                  "Identical known MgO cached computation has no second charge")
        else:
            reservation = starts[selected["job_id"]]
            terminal = finishes[selected["job_id"]]
            worker = read(path(entry["result_path"]).parent / "worker_started.json")
            check(plan["frozen_utc"] <= reservation["reserved_utc"] <= worker["started_utc"] <= terminal["finished_utc"],
                  "CHGNet selection and charge precede worker dispatch: " + name)
            check(close(terminal["wall_seconds"], parent["charged_wall_seconds"]) and close(terminal["wall_seconds"], entry["charged_wall_seconds_this_phase"]),
                  "Whole new CHGNet subprocess time charged once: " + name)
    matcher = StructureMatcher(ltol=.05, stol=.1, angle_tol=5, primitive_cell=True, scale=True, attempt_supercell=False)
    check(sum(bool(row["result"].get("converged", False)) for row in summary["results"]) == summary["converged_selections"],
          "Reported CHGNet convergence count preserves all successful and unsuccessful selections")
    for pair in summary["symmetry_pairs"]:
        left, right = results[pair["nontrivial_id"]], results[pair["p1_id"]]
        same = left["selection"]["control"] == right["selection"]["control"]
        converged = left["result"].get("converged", False) and right["result"].get("converged", False)
        check(same and pair["quota_each_arm"] == 1 and pair["both_converged"] == converged, "Balanced within-composition symmetry comparison: " + pair["control"])
        if converged:
            check(close(pair["p1_minus_nontrivial_eV_atom"], right["result"]["energy_eV_per_atom"] - left["result"]["energy_eV_per_atom"], 1e-12),
                  "Within-composition CHGNet energy difference reproduced: " + pair["control"])
            matching = matcher.fit(Structure.from_dict(read(left["result"]["final_structure"])), Structure.from_dict(read(right["result"]["final_structure"])))
            check(pair["relaxed_structures_match"] == bool(matching), "Relaxed symmetry-pair structure matching reproduced: " + pair["control"])
    check(summary["fresh_transformer_shortlist_relaxations"] == summary["new_generation_draws"] == 0 and
          len(plan["excluded_references"]) == 1 and plan["excluded_references"][0]["phase"] == "brookite",
          "Empty transformer shortlist and oversize brookite exclusion remain unchanged")
    check(not summary["new_stable_material_established"], "CHGNet results carry no DFT stability claim")
    return plan, summary


def audit_qe(starts, finishes):
    import numpy as np
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.core import Structure
    from phase3_qe_parser import parse_job

    plan = read("artifacts/phase5/qe/queue_plan.json")
    summary = read("artifacts/phase5/qe/summary.json")
    audit = read("artifacts/phase5/qe/audit.json")
    check(summary["status"] == audit["status"] == "passed" and not audit["failed_checks"], "QE lane numerical/provenance audit passed")
    check(plan["frozen_phase2_protocol_sha256"] == PROTOCOL_SHA and sha("artifacts/phase2/dft/numerical_protocol.json") == plan["numerical_protocol_sha256"],
          "QE perturbation preserves frozen numerical/scientific protocols")
    check(sum(row["outer_timeout"] for row in plan["jobs"].values()) == plan["maximum_all_allowed_job_watchdogs_seconds"] == 2520
          and plan["additional_phase5_QE_wall_ceiling_seconds"] == 3600, "All four permitted QE watchdogs fit the Phase5 wall cap")
    perturb = read(plan["perturbation_manifest"])
    check(sha(plan["perturbation_manifest"]) == plan["perturbation_manifest_sha256"] and perturb["seed"] == 260022,
          "One deterministic known-control perturbation is frozen")
    original = Structure.from_dict(read(perturb["source_geometry"]))
    proposed = Structure.from_dict(read(perturb["geometry_path"]))
    check(sha(perturb["source_geometry"]) == perturb["source_geometry_sha256"] and
          sha(perturb["geometry_path"]) == perturb["geometry_sha256"] and len(original) == len(proposed) == 8
          and original.composition == proposed.composition and proposed.composition.reduced_formula == "MgO",
          "Perturbation retains the frozen eight-atom MgO control cell and source lineage")
    rng = np.random.default_rng(260022)
    displacements = rng.normal(size=(8, 3)); displacements *= .01 / np.linalg.norm(displacements, axis=1)[:, None]
    raw = rng.normal(size=(3, 3)); strain = (raw + raw.T) / 2
    strain *= .005 / np.max(np.abs(np.linalg.eigvalsh(strain)))
    lattice = original.lattice.matrix @ (np.eye(3) + strain)
    expected_positions = original.frac_coords @ lattice + displacements
    delta = (proposed.cart_coords - expected_positions) @ np.linalg.inv(lattice)
    check(np.allclose(displacements, perturb["atom_displacements_angstrom"], atol=1e-15)
          and np.allclose(np.linalg.norm(displacements, axis=1), .01, atol=1e-15)
          and np.allclose(strain, perturb["symmetric_strain"], atol=1e-15)
          and close(np.max(np.abs(np.linalg.eigvalsh(strain))), .005, 1e-15)
          and np.allclose(proposed.lattice.matrix, lattice, atol=1e-12)
          and np.allclose(delta, np.round(delta), atol=1e-12), "Frozen seed reproduces every .01A displacement and .5-percent principal strain modulo PBC")
    new = [row for row in starts.values() if row["phase"] == 5 and row["lane"] == "qe"]
    check(len(new) == summary["phase5_QE_job_count"] and {row["reservation_id"] for row in new} <= set(plan["allowed_job_ids"]),
          "Only jobs in the bounded known-MgO perturbation queue were launched")
    records = {}
    legacy = lines("artifacts/phase1/qe/qe_jobs.jsonl")
    for reservation in new:
        name = reservation["reservation_id"]; directory = OUT / "qe" / name
        record = read(directory / "result.json"); records[name] = record
        provenance, saved = record["provenance"], record["result"]
        settings = read(directory / "settings.json")
        parsed = parse_job(directory, settings, return_code=record["return_code"], timed_out=record["timed_out"], write_geometry=False)
        for key in ["job_scf_accepted", "job_stationary_at_this_setting", "scf_converged", "force_norm_pass", "full_stress_pass", "pressure_pass"]:
            check(parsed[key] == saved[key], "Independently parsed QE acceptance " + name + ":" + key)
        if "energy_eV_per_atom" in parsed:
            check(close(parsed["energy_eV_per_atom"], saved["energy_eV_per_atom"], 1e-10)
                  and parsed["n_atoms"] == 8, "QE XML energy is normalized by actual eight atoms: " + name)
        check(settings["nosym"] and settings["noinv"] and settings["nspin"] == 1 and settings["occupations"] == "fixed"
              and settings["ecutwfc_Ry"] in {75., 90.} and settings["ecutrho_Ry"] == 8 * settings["ecutwfc_Ry"], "Supported unconstrained nonmagnetic oxide settings: " + name)
        check(record["threads"]["OMP_NUM_THREADS"] == record["threads"]["MKL_NUM_THREADS"] == "4" and
              record["threads"]["OPENBLAS_NUM_THREADS"] == "1", "QE single process has frozen four-thread settings: " + name)
        if saved.get("reported_MPI_processes") is not None:
            check(saved["reported_MPI_processes"] == 1 and saved["reported_threads_per_MPI_process"] == 4, "QE output confirms one MPI process and four threads: " + name)
        for source, expected in [(directory / "pw.in", provenance["input_sha256"]),
                                 (directory / "settings.json", provenance["settings_sha256"]),
                                 (directory / "pw.out", record["output_sha256"]),
                                 (provenance["source_geometry"], provenance["source_geometry_sha256"]),
                                 (provenance["executable"], provenance["executable_sha256"])]:
            if expected is None:
                check(not path(source).exists(), "Failed QE attempt explicitly retains an absent output: " + str(source))
            else:
                check(sha(source) == expected, "QE staged/executed file checksum: " + str(source))
        xml = path(parsed["xml_path"])
        if xml.exists(): sha(xml)
        for element, filename in provenance["pseudo_files"].items():
            check(sha(directory / "pseudo" / filename) == provenance["pseudo_hashes"][element], "QE common pseudopotential checksum: " + name + ":" + element)
        for source, key in [("scripts/phase5_qe.py", "runner_source_sha256"),
                            ("scripts/phase3_qe_parser.py", "parser_source_sha256"),
                            ("scripts/phase2_dft_inputs.py", "input_factory_sha256")]:
            check(sha(source) == provenance[key] and
                  sha(OUT / "qe/executed_sources" / source.replace("/", "__")) == provenance[key],
                  "QE executed source and archived bytes agree: " + name + ":" + source)
        check(provenance["queue_plan_sha256"] == sha("artifacts/phase5/qe/queue_plan.json")
              and reservation["metadata"]["queue_plan_sha256"] == provenance["queue_plan_sha256"], "QE queue hash precedes dispatch: " + name)
        check(plan["authorized_at_utc"] <= reservation["reserved_utc"] <= record["started_at_utc"] <= record["finished_at_utc"] <= finishes[name]["finished_utc"],
              "QE freeze and reservation precede execution: " + name)
        check(close(record["elapsed_wall_seconds"], finishes[name]["wall_seconds"])
              and sum(row["job_id"] == name for row in legacy) == 1, "QE real elapsed walltime appears once in both ledgers: " + name)
    chronological = sorted(records.values(), key=lambda row: row["started_at_utc"])
    check(all(a["finished_at_utc"] <= b["started_at_utc"] for a, b in zip(chronological, chronological[1:])), "All Phase5 QE attempts are serial")
    if "p5_mgo_perturb_90_cont1" in records:
        first = records["p5_mgo_perturb_90"]["result"]
        check(first["job_scf_accepted"] and not first["job_stationary_at_this_setting"], "The sole QE continuation was triggered by stationarity, not energy preference")
    sensitivity = path("artifacts/phase5/qe/sensitivity_decision.json")
    expected_numerical_acceptance = False
    accepted_job_id = None
    if sensitivity.exists():
        decision = read(sensitivity); base = records[decision["base_job"]]
        check(base["result"]["job_stationary_at_this_setting"], "Finite numerical probes use an independently stationary final geometry")
        for label, key in [("cutoff", "cutoff_job"), ("kpoint", "kpoint_job")]:
            probe = records[decision[key]]
            shift = abs(base["result"]["energy_eV_per_atom"] - probe["result"]["energy_eV_per_atom"])
            check(close(shift, decision[label + "_shift_eV_per_atom"], 1e-12)
                  and probe["provenance"]["source_geometry_sha256"] == sha(OUT / "qe" / base["job_id"] / "final_geometry.json"),
                  "Same-final-geometry finite energy shift reproduced: " + label)
        distinct_mesh = base["provenance"]["settings"]["k_mesh"] != records[decision["kpoint_job"]]["provenance"]["settings"]["k_mesh"]
        check(decision["actual_k_mesh_changed"] == distinct_mesh, "K-point sensitivity records whether the actual executed mesh changes")
        expected_numerical_acceptance = bool(base["result"]["job_stationary_at_this_setting"] and distinct_mesh and
            all(records[decision[key]]["result"]["job_scf_accepted"] and
                abs(base["result"]["energy_eV_per_atom"] - records[decision[key]]["result"]["energy_eV_per_atom"]) <= .005
                for key in ["cutoff_job", "kpoint_job"]))
        accepted_job_id = base["job_id"] if expected_numerical_acceptance else None
    check(summary["perturbation_final_geometry_numerical_checks_pass"] == expected_numerical_acceptance and
          summary["accepted_perturbation_job_id"] == accepted_job_id,
          "Scientific numerical acceptance is separate from successful completion of the bounded audit")
    comparison = summary.get("known_control_comparison")
    if comparison:
        comparison_plan = read("artifacts/phase5/qe/comparison_protocol.json")
        original_record = read(plan["original_control_result"])
        current = records[comparison["perturbed_relaxation_job_id"]]
        check(comparison_plan["frozen_at_utc"] <= current["finished_at_utc"] and
              comparison["matcher_settings"] == comparison_plan["matcher_settings"], "The known-control comparator is fixed before the new outcome")
        if comparison["accepted_for_finite_energy_comparison"]:
            check(summary["perturbation_final_geometry_numerical_checks_pass"] and
                  close(comparison["perturbed_minus_original_eV_per_atom"], current["result"]["energy_eV_per_atom"] - original_record["result"]["energy_eV_per_atom"], 1e-12),
                  "A finite known-control energy difference is reported only after final numerical acceptance")
            reference = read("artifacts/phase3/qe/" + comparison["known_reference_job_id"] + "/result.json")
            check(close(comparison["perturbed_minus_known_reference_eV_per_atom"], current["result"]["energy_eV_per_atom"] - reference["result"]["energy_eV_per_atom"], 1e-12),
                  "The perturbed-control energy is compared only with the compatible known MgO reference")
        else:
            check(comparison["perturbed_minus_original_eV_per_atom"] is None, "Incomplete perturbation validation has no accepted energy ordering")
        match_settings = comparison_plan["matcher_settings"]
        matcher = StructureMatcher(ltol=match_settings["ltol"], stol=match_settings["stol"], angle_tol=match_settings["angle_tol_degrees"],
                                   primitive_cell=match_settings["primitive_cell"], scale=match_settings["scale"], attempt_supercell=match_settings["attempt_supercell"])
        final = Structure.from_dict(read(OUT / "qe" / current["job_id"] / "final_geometry.json"))
        check(bool(matcher.fit(original, final)) == comparison["structure_matcher_to_original_control"],
              "Known-control structure matching is independently reproduced with the frozen strict tolerances")
    check(summary["fresh_candidate_jobs_this_phase"] == 0 and not summary["fresh_CaMg2O3_candidate_submitted"]
          and summary["new_stable_materials"] == 0 and not summary["full_frozen_inventory_hull_established"], "Known-control QE checks do not promote a new candidate or claim a full hull")
    return plan, summary, legacy


def main():
    event_hash = sha("artifacts/runtime_budget_events.jsonl")
    events = lines("artifacts/runtime_budget_events.jsonl")
    if any(row.get("phase", 0) > 5 for row in events):
        raise RuntimeError("A later numerical phase exists; refusing to overwrite historical Phase5 closure")
    prior_manifest = read(OUT / "manifest.json") if (OUT / "manifest.json").exists() else None
    if prior_manifest and prior_manifest["phase5_end_budget"]["runtime_events_sha256"] != event_hash:
        raise RuntimeError("Numerical ledger changed after Phase5 closure; refusing historical overwrite")
    reserved = [row for row in events if row["event"] == "reserved"]
    terminal = [row for row in events if row["event"] == "finished"]
    starts = {row["reservation_id"]: row for row in reserved}
    finishes = {row["reservation_id"]: row for row in terminal}
    check(len(starts) == len(reserved) and len(finishes) == len(terminal) and set(starts) == set(finishes), "Every unique reservation has exactly one terminal record; no active numerical jobs")
    if set(starts) != set(finishes):
        raise RuntimeError("Numerical attempts remain unfinished; wait for their existing owners")
    budget = read("artifacts/budget_ledger.json")
    check(budget["phase"] == 5, "Canonical budget records Phase5 as the latest executed numerical phase")
    previous = read("artifacts/phase5/preflight/budget_ledger.json")
    phase4_manifest = read("artifacts/phase4/manifest.json")
    check(sha("artifacts/phase4/manifest.json") == sha("artifacts/phase5/preflight/manifest.json") and
          sha("artifacts/phase4/readiness.json") == sha("artifacts/phase5/preflight/readiness.json"), "Phase4 historical manifest and readiness remain byte-for-byte preserved")
    check(previous["generation"]["charged_attempts"] == 96 and previous["chgnet"]["charged_attempts"] == 9
          and close(previous["qe"]["charged_wall_seconds"], 1658.4818778000044), "Phase5 starts from frozen 96 generation, nine CHGNet and 1658.482 QE-second totals")
    check(sha("config/phase2_protocol.json") == PROTOCOL_SHA and sha("research_acquisition.py") == ACQUISITION_SHA
          and sha("artifacts/phase3/models/fresh_selector_seed_20261022.joblib") == FRESH_SHA, "Scientific protocol, acquisition implementation and original fresh selector remain frozen")
    for value in read("artifacts/phase2/protocol/manifest.json").values():
        if isinstance(value, dict) and {"path", "sha256"} <= value.keys():
            check(sha(value["path"]) == value["sha256"], "Phase2 frozen input: " + value["path"])
    for row in phase4_manifest["files"]:
        name = row["path"]
        if name.startswith("artifacts/phase4/selection/") or name.endswith("query_journal.csv") or name == "artifacts/phase4/replay/aggregate_summary.json":
            check(sha(name) == row["sha256"], "Frozen Phase4 selection/replay evidence: " + name)
    shortlist = read("artifacts/phase4/selection/fresh_shortlist.json")
    check(shortlist["selected_count"] == 0 and not shortlist["selected_in_formula_and_pair_order"] and not shortlist["default_CaMg_DFT_queue_changed"],
          "Zero eligible transformer candidates remain excluded; the original DFT queue is unchanged")
    new = [row for row in reserved if row["phase"] == 5]
    check(not any(row["lane"] == "generation" for row in new), "Phase5 has no new generator draws or prototype-generation charges")
    chg_plan, chg = audit_chgnet(starts, finishes)
    qe_plan, qe, legacy = audit_qe(starts, finishes)
    baseline = read("artifacts/phase3/budget_baseline.json")["budget"]
    for lane in ["generation", "chgnet", "qe"]:
        lane_reservations = [row for row in reserved if row["lane"] == lane]
        check(not budget[lane]["active_reservations"], "No active canonical reservation in lane: " + lane)
        if lane != "qe":
            charges = baseline[lane]["charged_attempts"] + sum(row["attempts"] for row in lane_reservations)
            check(charges == budget[lane]["charged_attempts"] and budget[lane]["remaining_attempts"] == budget[lane]["ceiling_attempts"] - charges,
                  "Attempt counts independently reconstructed from reservations: " + lane)
        if lane != "generation":
            wall = baseline[lane]["charged_wall_seconds"] + sum(finishes[row["reservation_id"]]["wall_seconds"] for row in lane_reservations)
            check(close(wall, budget[lane]["charged_wall_seconds"]) and close(budget[lane]["remaining_seconds"], budget[lane]["ceiling_seconds"] - wall),
                  "Whole-process walltime independently reconstructed: " + lane)
    check(budget["generation"]["charged_attempts"] == 96 and budget["generation"]["remaining_attempts"] == 32
          and budget["chgnet"]["charged_attempts"] == 19 and budget["chgnet"]["remaining_attempts"] == 21, "Phase5 closes with 96/128 structure charges and 19/40 CHGNet launch charges")
    check(budget["generation"]["ceiling_attempts"] == 128 and budget["chgnet"]["ceiling_attempts"] == 40
          and budget["chgnet"]["ceiling_seconds"] == 14400 and budget["qe"]["ceiling_seconds"] == 21600
          and budget["chgnet"]["remaining_seconds"] >= 0 and budget["qe"]["remaining_seconds"] >= 0,
          "All original attempt and cumulative walltime caps remain unchanged and respected")
    check(close(sum(row["elapsed_wall_seconds"] for row in legacy), budget["qe"]["charged_wall_seconds"]), "All historical QE attempts agree between legacy and central ledgers")
    check(close(sum(row["wall_seconds"] for row in terminal if row["phase"] == 5 and row["lane"] == "chgnet"), chg["charged_new_job_wall_seconds"])
          and close(sum(row["wall_seconds"] for row in terminal if row["phase"] == 5 and row["lane"] == "qe"), qe["phase5_QE_wall_seconds"]),
          "Both lane summaries include every Phase5 walltime charge")
    cutoff = datetime.fromisoformat(budget["numerical_stop_utc"])
    check(budget["numerical_stop_utc"] == "2026-10-22T10:24:44+00:00" and all(datetime.fromisoformat(row["finished_utc"]) <= cutoff for row in terminal),
          "Every numerical job stopped by 22 October 18:24:44 Singapore time")
    qe_reservations = sorted([row for row in reserved if row["lane"] == "qe"], key=lambda row: row["reserved_utc"])
    check(all(finishes[a["reservation_id"]]["finished_utc"] <= b["reserved_utc"] for a, b in zip(qe_reservations, qe_reservations[1:])),
          "All post-baseline QE reservations across phases are serialized")
    inventory = read("artifacts/phase2/dft/primary_reference_plan.json")
    check(len(inventory["records"]) == 161, "All 161 original Ca-Mg-O reference entries remain in the inventory")
    phase3_qe = read("artifacts/phase3/qe/summary.json")
    check(phase3_qe["candidate_validation"]["full_numerical_convergence"] and phase3_qe["reference_validation"]["full_numerical_convergence"],
          "Prior known MgO control and source reference have accepted compatible numerical checks")
    # Accepted references are the two oxide anchors. The CHGNet references are a separate lane.
    phase4_qe = read("artifacts/phase4/qe/summary.json")
    check(phase4_qe["CaO_final_geometry_numerical_checks_pass"] and phase4_qe["CaO_and_MgO_shared_90_720_Ry_spacing_0p35_anchor_settings"]
          and set(phase4_qe["completed_original_source_reference_ids"]) == {"mp-2605", "mp-1265"}
          and len(phase4_qe["uncompleted_frozen_primary_reference_ids"]) == 159,
          "Only two of 161 frozen source references have accepted compatible fresh QE calculations; 159 remain incomplete")
    report = path("reports/phase5_report.md"); sha(report)
    text = report.read_text(encoding="utf-8")
    check(not re.search(r"\b(?:PLACEHOLDER|TBD|TODO)\b", text), "Phase5 report contains completed outcomes without placeholders")
    planned_outputs = {(OUT / name).resolve() for name in ["audit.json", "readiness.json", "manifest.json"]}
    deferred = []
    for document in [report, path("README.md"), path("one_day_research_proposal.md")]:
        sha(document)
        for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            target = unquote(link.strip().strip("<>").split("#", 1)[0])
            if not target or re.match(r"(?:https?://|mailto:)", target):
                continue
            resolved = (document.parent / target).resolve()
            if resolved in planned_outputs and not resolved.exists(): deferred.append(resolved)
            check(resolved.exists() or resolved in planned_outputs, "Document local link resolves: " + document.name + ":" + target)
    for script in sorted((ROOT / "scripts").glob("phase5*.py")): sha(script)
    for source in ["research_budget.py", "research_features.py", "scripts/phase3_candidates.py", "scripts/phase3_qe_parser.py", "scripts/phase2_dft_inputs.py"]: sha(source)
    for source in sorted(OUT.rglob("*")):
        if source.is_file() and source.name not in {"audit.json", "readiness.json", "manifest.json"} and ".partial" not in source.name:
            sha(source)
    check(sha("artifacts/runtime_budget_events.jsonl") == event_hash and not path("artifacts/runtime_budget.lock").exists()
          and not path("artifacts/phase1/qe/qe_active.lock").exists(), "Final audit dispatched no work and numerical ledger stayed unchanged")
    passed = all(row["passed"] for row in CHECKS)
    completed = datetime.now(timezone.utc).isoformat()
    save("audit.json", {"phase": 5, "audited_utc": completed, "status": "passed" if passed else "failed",
        "check_count": len(CHECKS), "checks": CHECKS, "failed_checks": [row for row in CHECKS if not row["passed"]],
        "audit_source_sha256": sha(Path(__file__)), "oracle_label_file_accesses": 0,
        "new_fits_draws_relaxations_or_QE_jobs": 0, "canonical_budget_writes": 0,
        "CHGNet_experimental_selections": 11, "new_CHGNet_launches": 10, "cached_CHGNet_reuses": 1,
        "phase5_QE_jobs": qe["phase5_QE_job_count"], "original_fresh_transformer_shortlist_count": 0,
        "compatible_accepted_fresh_QE_reference_entries": 2, "frozen_primary_reference_entries": 161,
        "not_completed_primary_reference_entries": 159, "new_stable_materials": 0})
    readiness = {"phase": 5, "status": "complete" if passed else "audit_failed", "completed_utc": completed,
        "ready_for_phase6": passed, "protocol_sha256": PROTOCOL_SHA, "original_fresh_selector_sha256": FRESH_SHA,
        "CHGNet_experimental_selections": 11, "new_CHGNet_launches": 10, "cached_CHGNet_reuses": 1,
        "converged_CHGNet_selections": chg["converged_selections"], "symmetry_pairs": chg["symmetry_pairs"],
        "symmetry_energy_evidence_scope": "One structure per arm; supplemented MgO and primary TiO2 are descriptive separate comparisons, not architecture-causal evidence",
        "prototype_baselines_validated": 4, "eligible_CHGNet_same_composition_references_validated": 3,
        "brookite_reference_status": "Predeclared 24-atom conventional cell remains excluded without replacement",
        "fresh_transformer_shortlist_count": 0, "fresh_CaMg2O3_DFT_candidate_submitted": False,
        "phase5_QE_jobs": qe["phase5_QE_job_count"],
        "known_control_perturbation_numerical_checks_pass": qe["perturbation_final_geometry_numerical_checks_pass"],
        "compatible_accepted_fresh_QE_reference_entries": 2, "frozen_primary_reference_entries": 161,
        "not_completed_primary_reference_entries": 159, "full_compatible_competition_hull_established": False,
        "new_stable_material_established": False, "phonon_stability_established": False,
        "remaining_generation_slots": budget["generation"]["remaining_attempts"],
        "remaining_CHGNet_launches": budget["chgnet"]["remaining_attempts"],
        "remaining_CHGNet_seconds": budget["chgnet"]["remaining_seconds"], "remaining_QE_seconds": budget["qe"]["remaining_seconds"],
        "numerical_stop_utc": budget["numerical_stop_utc"], "report": "reports/phase5_report.md",
        "phase6_tasks": ["Finish only permitted useful sensitivity/reference work within the unchanged caps and numerical stop; incomplete phases remain explicit",
            "Analyze fixed five-seed acquisition outcomes and descriptive symmetry/MLIP results without retuning",
            "Audit reference completeness, numerical sensitivity, catalog scope and failed/excluded candidates",
            "Retain zero eligible transformer candidates; a later cell-gate or candidate-method change must be separately labelled supplementary research",
            "Prepare scoped scientific conclusions and reporting inputs for Phases7-8"],
        "review_command": ".envs/analysis/Scripts/python.exe scripts/phase5_finalize.py",
        "review_command_scope": "Read saved artifacts and write only the three Phase5 closure files; no numerical experiments or canonical budget writes"}
    save("readiness.json", readiness)
    frozen_budget = prior_manifest["phase5_end_budget"] if prior_manifest else {
        "frozen_utc": completed, "budget_ledger": budget, "budget_ledger_sha256": sha("artifacts/budget_ledger.json"),
        "runtime_events_sha256": event_hash, "runtime_event_count": len(events),
        "scope": "Historical Phase5 close. Later phases may advance the ledger; this close must remain unchanged."}
    sha(OUT / "audit.json"); sha(OUT / "readiness.json")
    save("manifest.json", {"phase": 5, "created_utc": completed, "status": "complete" if passed else "audit_failed",
        "phase5_end_budget": frozen_budget, "files": [INVENTORY[key] for key in sorted(INVENTORY) if key != "artifacts/phase5/manifest.json"],
        "scope": "Frozen protocols, sources, selected initial geometries, saved CHGNet trajectories/results, QE XML/input/output/pseudopotentials, lane audits, report/docs and the final budget. No oracle labels were opened."})
    if not all(source.is_file() for source in deferred):
        raise RuntimeError("An explicitly deferred finalizer-output link did not materialize")
    print(json.dumps({"phase": 5, "status": "passed" if passed else "failed", "checks": len(CHECKS),
        "failed": sum(not row["passed"] for row in CHECKS), "ready_for_phase6": passed,
        "remaining_generation_slots": budget["generation"]["remaining_attempts"],
        "remaining_CHGNet_launches": budget["chgnet"]["remaining_attempts"], "remaining_QE_seconds": budget["qe"]["remaining_seconds"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
