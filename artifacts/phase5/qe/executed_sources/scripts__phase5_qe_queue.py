"""Freeze and execute the bounded, predeclared known-MgO perturbation check.

The deterministic perturbation is a validation geometry, not a proposed new
material or a replacement for the empty fresh-composition DFT shortlist.
"""
from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

import numpy as np
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from phase5_qe import ROOT, ART, digest, execute, now, prepare, save


def freeze():
    if (ART / "queue_plan.json").exists():
        raise RuntimeError("Queue already frozen; do not redraw the perturbation")
    original = ROOT / "artifacts/phase3/qe/p3_candidate_mgo_fallback_90"
    record = json.loads((original / "result.json").read_text())
    if not record["result"]["job_stationary_at_this_setting"]:
        raise RuntimeError("Original known control is not independently stationary")
    structure = Structure.from_file(original / "final_geometry.json")
    if len(structure) != 8 or structure.composition.as_dict() != {"Mg": 4, "O": 4}:
        raise RuntimeError("Unexpected original known-control cell")
    rng = np.random.default_rng(260022)
    displacement = rng.normal(size=(8, 3))
    displacement *= .01 / np.linalg.norm(displacement, axis=1)[:, None]
    raw = rng.normal(size=(3, 3))
    strain = (raw + raw.T) / 2
    strain *= .005 / np.max(np.abs(np.linalg.eigvalsh(strain)))
    deformed = Structure(structure.lattice.matrix @ (np.eye(3) + strain),
                         structure.species, structure.frac_coords)
    for atom_index, offset in enumerate(displacement):
        deformed.translate_sites([atom_index], offset, frac_coords=False, to_unit_cell=True)
    perturb = ART / "perturbation"
    perturb.mkdir(parents=True)
    save(perturb / "final_geometry.json", deformed.as_dict())
    deformed.to(filename=str(perturb / "initial_geometry.cif"))
    inherited = json.loads((original / "settings.json").read_text())
    inherited["source_geometry_sha256"] = digest(original / "final_geometry.json")
    inherited["perturbation_validation_geometry_only"] = True
    save(perturb / "settings.json", inherited)
    perturbation_manifest = {
        "created_at_utc": now(), "seed": 260022,
        "source_geometry": str((original / "final_geometry.json").relative_to(ROOT)),
        "source_geometry_sha256": digest(original / "final_geometry.json"),
        "source_result_sha256": digest(original / "result.json"),
        "algorithm": "NumPy default_rng: eight independent normalized Gaussian directions of length0.01A, then Gaussian symmetric strain rescaled to maximum absolute principal strain0.005; strain lattice retaining fractional coordinates, then add Cartesian atomic displacements",
        "atom_displacements_angstrom": displacement.tolist(),
        "atom_displacement_norms_angstrom": np.linalg.norm(displacement, axis=1).tolist(),
        "symmetric_strain": strain.tolist(),
        "principal_strains": np.linalg.eigvalsh(strain).tolist(),
        "geometry_path": str((perturb / "final_geometry.json").relative_to(ROOT)),
        "geometry_sha256": digest(perturb / "final_geometry.json"),
        "original_spacegroup_symprec_1e3": SpacegroupAnalyzer(structure, symprec=1e-3).get_space_group_number(),
        "perturbed_spacegroup_symprec_1e3": SpacegroupAnalyzer(deformed, symprec=1e-3).get_space_group_number(),
        "scope": "Single deterministic local re-relaxation probe of known MgO; not a phonon test, hull test, new candidate or new composition"}
    save(perturb / "manifest.json", perturbation_manifest)
    jobs = {
        "p5_mgo_perturb_90": dict(calculation="vc-relax", role="perturbation", max_seconds=900, outer_timeout=930,
            cutoff_multiplier=1.8, k_spacing=.35, pressure_threshold=.1, allowed_parent_jobs=["perturbation"]),
        "p5_mgo_perturb_90_cont1": dict(calculation="vc-relax", role="perturbation", max_seconds=900, outer_timeout=930,
            cutoff_multiplier=1.8, k_spacing=.35, pressure_threshold=.1, allowed_parent_jobs=["p5_mgo_perturb_90"]),
        "p5_mgo_perturb_final_cut75": dict(calculation="scf", role="sensitivity", max_seconds=300, outer_timeout=330,
            cutoff_multiplier=1.5, k_spacing=.35, pressure_threshold=.1, allowed_parent_jobs=["p5_mgo_perturb_90", "p5_mgo_perturb_90_cont1"]),
        "p5_mgo_perturb_final_k045": dict(calculation="scf", role="sensitivity", max_seconds=300, outer_timeout=330,
            cutoff_multiplier=1.8, k_spacing=.45, pressure_threshold=.1, allowed_parent_jobs=["p5_mgo_perturb_90", "p5_mgo_perturb_90_cont1"])}
    plan = {
        "schema_version": 1, "phase": 5, "status": "authorized_before_dispatch", "authorized_at_utc": now(),
        "authorization": "Root approval of this bounded queue under the user-authorized Phase5 completion",
        "scope": perturbation_manifest["scope"], "additional_phase5_QE_wall_ceiling_seconds": 3600,
        "maximum_all_allowed_job_watchdogs_seconds": sum(s["outer_timeout"] for s in jobs.values()),
        "global_QE_wall_ceiling_seconds": 21600, "numerical_stop_utc": "2026-10-22T10:24:44+00:00",
        "frozen_phase2_protocol_sha256": digest(ROOT / "config/phase2_protocol.json"),
        "numerical_protocol_sha256": digest(ROOT / "artifacts/phase2/dft/numerical_protocol.json"),
        "prior_phase3_runner_sha256": digest(ROOT / "scripts/phase3_qe.py"),
        "prior_phase4_runner_sha256": digest(ROOT / "scripts/phase4_qe.py"),
        "initial_source_job": "perturbation", "initial_source_geometry": perturbation_manifest["geometry_path"],
        "initial_source_geometry_sha256": perturbation_manifest["geometry_sha256"],
        "perturbation_manifest": str((perturb / "manifest.json").relative_to(ROOT)),
        "perturbation_manifest_sha256": digest(perturb / "manifest.json"),
        "original_control_result": str((original / "result.json").relative_to(ROOT)),
        "original_control_result_sha256": digest(original / "result.json"),
        "execution_cell_policy": "Retain eight-atom control cell; perturb coordinates and cell once before outcomes; no primitive reduction",
        "external_acceptance": dict(SCF_Ry=1e-8, max_force_vector_norm_eV_A=.0205688269904,
            abs_pressure_kbar=.5, max_abs_full_stress_kbar=.5, adjacent_energy_shift_eV_per_atom=.005),
        "rules": [
            "Run the deterministic seed260022 perturbation once at90/720Ry, kspacing0.35, nosym/noinv and all cell degrees of freedom released.",
            "Stop on process or SCF failure. If SCF completes but independent final stationarity fails, allow exactly one same-setting continuation.",
            "At accepted final geometry run75/600Ry cutoff and90/720Ry kspacing0.45 probes; require distinct actual meshes and shifts<=5meV/atom.",
            "A failed numerical sensitivity remains incomplete; no unplanned refinement, target switch or fresh candidate replacement.",
            "All jobs charge actual entire subprocess walltime and reserve full watchdog before launch. One QE process and four threads only.",
            "Compare only with the original known MgO control and known MgO reference. No full-hull, new-material, phonon or synthesis claim."],
        "jobs": jobs, "allowed_job_ids": list(jobs)}
    save(ART / "queue_plan.json", plan)


def run(job_id, source_job):
    geometry = ART / source_job / "final_geometry.json"
    plan = json.loads((ART / "queue_plan.json").read_text())
    spec = plan["jobs"][job_id]
    args = SimpleNamespace(job_id=job_id, reference_id=None,
        geometry=str(geometry.relative_to(ROOT)), expected_geometry_sha256=digest(geometry),
        selection_manifest=None, role=spec["role"], calculation=spec["calculation"],
        cutoff_multiplier=spec["cutoff_multiplier"], k_spacing=spec["k_spacing"],
        pressure_threshold=spec["pressure_threshold"], max_seconds=spec["max_seconds"], outer_timeout=spec["outer_timeout"])
    save(ART / (job_id + "_dispatch.json"), {"created_at_utc": now(), "args": vars(args),
        "queue_plan_sha256": digest(ART / "queue_plan.json")})
    directory, stage = prepare(args)
    execute(directory, stage)
    return json.loads((directory / "result.json").read_text())


def dispatch():
    if list(ART.glob("*/result.json")):
        raise RuntimeError("Queue already has outcomes; do not silently replay")
    archive = ART / "executed_sources"
    archive.mkdir()
    for relative in ("scripts/phase5_qe.py", "scripts/phase5_qe_queue.py", "scripts/phase3_qe_parser.py", "scripts/phase2_dft_inputs.py", "research_budget.py"):
        (archive / relative.replace("/", "__")).write_bytes((ROOT / relative).read_bytes())
    base = run("p5_mgo_perturb_90", "perturbation")
    if not base["result"]["job_scf_accepted"]:
        return
    if not base["result"]["job_stationary_at_this_setting"]:
        save(ART / "continuation_decision.json", {"at_utc": now(),
            "trigger": "Independent force/full-stress stationarity failed at final settings", "base_job": base["job_id"],
            "base_result_sha256": digest(ART / base["job_id"] / "result.json")})
        base = run("p5_mgo_perturb_90_cont1", base["job_id"])
        if not base["result"]["job_stationary_at_this_setting"]:
            return
    cutoff = run("p5_mgo_perturb_final_cut75", base["job_id"])
    if not cutoff["result"]["job_scf_accepted"]:
        return
    kpoint = run("p5_mgo_perturb_final_k045", base["job_id"])
    if not kpoint["result"]["job_scf_accepted"]:
        return
    changed_mesh = base["provenance"]["settings"]["k_mesh"] != kpoint["provenance"]["settings"]["k_mesh"]
    cut_shift = abs(base["result"]["energy_eV_per_atom"] - cutoff["result"]["energy_eV_per_atom"])
    k_shift = abs(base["result"]["energy_eV_per_atom"] - kpoint["result"]["energy_eV_per_atom"])
    save(ART / "sensitivity_decision.json", {"at_utc": now(), "base_job": base["job_id"],
        "cutoff_job": cutoff["job_id"], "kpoint_job": kpoint["job_id"],
        "cutoff_shift_eV_per_atom": cut_shift, "kpoint_shift_eV_per_atom": k_shift,
        "actual_k_mesh_changed": changed_mesh, "cutoff_pass": cut_shift <= .005, "kpoint_pass": k_shift <= .005 and changed_mesh})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "dispatch"])
    args = parser.parse_args()
    freeze() if args.action == "freeze" else dispatch()
