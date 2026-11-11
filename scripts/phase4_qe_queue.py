"""Execute the already frozen bounded CaO queue, retaining every attempt."""
from __future__ import annotations

import json
from types import SimpleNamespace

from phase4_qe import ROOT, ART, digest, execute, now, prepare, save


def run(job_id, source_job, cutoff=90, spacing=.35):
    prior_phase = "phase3" if source_job.startswith("p3_") else "phase4"
    geometry = ROOT / "artifacts" / prior_phase / "qe" / source_job / "final_geometry.json"
    plan = json.loads((ART / "queue_plan.json").read_text())
    spec = plan["jobs"][job_id]
    args = SimpleNamespace(job_id=job_id, reference_id=None,
        geometry=str(geometry.relative_to(ROOT)), expected_geometry_sha256=digest(geometry),
        selection_manifest=None, role=spec["role"], calculation=spec["calculation"],
        cutoff_multiplier=cutoff / 50, k_spacing=spacing, pressure_threshold=.1,
        max_seconds=spec["max_seconds"], outer_timeout=spec["outer_timeout"])
    save(ART / (job_id + "_dispatch.json"), {"created_at_utc": now(),
        "args": vars(args), "queue_plan_sha256": digest(ART / "queue_plan.json")})
    directory, stage = prepare(args)
    execute(directory, stage)
    return json.loads((directory / "result.json").read_text())


def energy(record):
    return record["result"]["energy_eV_per_atom"]


def probes(base, label, lower_cutoff, coarse_spacing):
    base_id = base["job_id"]
    if label == "initial":
        cutoff_id, k_id = "p4_cao_final_cut75", "p4_cao_final_k045"
    else:
        cutoff_id, k_id = "p4_cao_refined_final_cut", "p4_cao_refined_final_k"
    settings = base["provenance"]["settings"]
    high_cutoff = settings["ecutwfc_Ry"]
    fine_spacing = settings["k_spacing_start_inv_angstrom"]
    cutoff = run(cutoff_id, base_id, lower_cutoff, fine_spacing)
    if not cutoff["result"]["job_scf_accepted"]:
        return None
    kpoint = run(k_id, base_id, high_cutoff, coarse_spacing)
    if not kpoint["result"]["job_scf_accepted"]:
        return None
    changed_mesh = settings["k_mesh"] != kpoint["provenance"]["settings"]["k_mesh"]
    changes = {"base_job": base_id, "cutoff_job": cutoff_id, "kpoint_job": k_id,
        "cutoff_shift_eV_per_atom": abs(energy(base) - energy(cutoff)),
        "kpoint_shift_eV_per_atom": abs(energy(base) - energy(kpoint)),
        "actual_k_mesh_changed": changed_mesh, "at_utc": now()}
    changes["cutoff_pass"] = changes["cutoff_shift_eV_per_atom"] <= .005
    changes["kpoint_pass"] = changes["kpoint_shift_eV_per_atom"] <= .005 and changed_mesh
    save(ART / (label + "_sensitivity_decision.json"), changes)
    return changes


def main():
    if list(ART.glob("*/result.json")):
        raise RuntimeError("Queue already has outcomes: do not silently replay it")
    archive = ART / "executed_sources"
    archive.mkdir()
    for relative in ("scripts/phase4_qe.py", "scripts/phase4_qe_queue.py",
                     "scripts/phase3_qe_parser.py", "scripts/phase2_dft_inputs.py", "research_budget.py"):
        (archive / relative.replace("/", "__")).write_bytes((ROOT / relative).read_bytes())
    base = run("p4_ref_cao_90_k035", "p3_ref_cao_base")
    if not base["result"]["job_scf_accepted"]:
        return
    if not base["result"]["job_stationary_at_this_setting"]:
        save(ART / "continuation_decision.json", {"at_utc": now(),
            "trigger": "Independent force/full-stress stationarity failed at final settings",
            "base_job": base["job_id"], "base_result_sha256": digest(ART / base["job_id"] / "result.json")})
        base = run("p4_ref_cao_90_k035_cont1", base["job_id"])
        if not base["result"]["job_stationary_at_this_setting"]:
            return
    changes = probes(base, "initial", 75, .45)
    if changes is None or changes["cutoff_pass"] and changes["kpoint_pass"]:
        return
    refined_cutoff = 90 if changes["cutoff_pass"] else 105
    refined_spacing = .35 if changes["kpoint_pass"] else .30
    save(ART / "refinement_decision.json", {"at_utc": now(),
        "trigger": "Predeclared adjacent-cutoff or k-mesh energy shift exceeded tolerance",
        "parent_sensitivity": changes, "refined_cutoff_Ry": refined_cutoff,
        "refined_spacing_inv_A": refined_spacing,
        "CaO_plus_MgO_common_setting_comparison_incomplete_if_changed": True})
    refined = run("p4_ref_cao_refined", base["job_id"], refined_cutoff, refined_spacing)
    if refined["result"]["job_stationary_at_this_setting"]:
        probes(refined, "refined", 90 if refined_cutoff == 105 else 75,
               .35 if refined_spacing == .30 else .45)


if __name__ == "__main__":
    main()
