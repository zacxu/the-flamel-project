"""Frozen Phase 5 CHGNet experiments; no candidate selection from energies.

The numerical worker is the unchanged, manifest-verified Phase 3 worker. This
launcher supplies immutable source geometries and records each new reservation.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "artifacts/phase5/chgnet"
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
for key in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"]:
    os.environ[key] = "2"


def utc():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def append(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def source_manifest():
    paths = [ROOT / "scripts/phase3_candidates.py", ROOT / "scripts/phase5_chgnet.py",
             ROOT / "research_features.py", ROOT / "scripts/phase2_dft_inputs.py",
             ROOT / "research_budget.py",
             ROOT / ".envs/analysis/Lib/site-packages/chgnet/model/dynamics.py",
             ROOT / ".envs/analysis/Lib/site-packages/ase/optimize/fire.py",
             ROOT / ".envs/analysis/Lib/site-packages/ase/filters.py"]
    records = []
    for index, source in enumerate(paths):
        target = OUT / "executed_sources" / f"{index:02d}_{source.name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        records.append({"path": rel(source), "sha256": sha(source), "archive": rel(target)})
    return records


def freeze():
    from pymatgen.core import Structure
    target = OUT / "plan.json"
    if target.exists():
        raise RuntimeError("Phase 5 CHGNet plan already frozen; inspect rather than reselect")
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = ROOT / "config/phase2_protocol.json"
    assert sha(protocol) == "b71724ad4e9a940de090d4163bc6a23a10ed9bfb957fb656b50222b884d36c94"
    readiness = load(ROOT / "artifacts/phase4/readiness.json")
    assert readiness["ready_for_phase5"] and readiness["fresh_shortlist_count"] == 0
    symmetry_path = ROOT / "artifacts/phase4/selection/symmetry_relaxation_plan.json"
    generation_path = ROOT / "artifacts/phase2/compositions/generation_protocol.json"
    reference_path = ROOT / "artifacts/phase2/controls/same_composition_reference_plan.json"
    symmetry = load(symmetry_path)
    generation = load(generation_path)
    references = load(reference_path)
    old_worker = ROOT / "scripts/phase3_candidates.py"
    phase3_manifest = load(ROOT / "artifacts/phase3/manifest.json")
    old_hash = next(row["sha256"] for row in phase3_manifest["files"] if row["path"] == rel(old_worker))
    assert sha(old_worker) == old_hash, "Phase 3 worker changed since its completed manifest"
    checkpoint = ROOT / ".envs/analysis/Lib/site-packages/chgnet/pretrained/0.3.0/chgnet_0.3.0_e29f68s314m37.pth.tar"
    assert importlib.metadata.version("chgnet") == "0.4.2"
    jobs = []
    for control in symmetry["controls"]:
        for arm in control["arms"]:
            assert len(arm["selected"]) == 1
            chosen = arm["selected"][0]
            source = ROOT / chosen["source_structure"]
            assert sha(source) == chosen["source_structure_sha256"]
            jobs.append({"candidate_id": chosen["candidate_id"], "category": "symmetry",
                         "control": control["control"], "arm": arm["arm"],
                         "comparison_scope": control["comparison_scope"],
                         "original_source": rel(source), "original_source_sha256": sha(source),
                         "source_structure": rel(source), "source_structure_sha256": sha(source),
                         "cached": chosen["candidate_id"] == "phase1_mgo_attempt_000"})
    def converted(candidate_id, category, source, metadata):
        structure = Structure.from_file(source)
        assert len(structure) <= 20
        destination = OUT / "initial_structures" / f"{candidate_id}.json"
        dump(destination, structure.as_dict())
        jobs.append({"candidate_id": candidate_id, "category": category,
                     "original_source": rel(source), "original_source_sha256": sha(source),
                     "source_structure": rel(destination), "source_structure_sha256": sha(destination),
                     "cached": False, "atoms": len(structure),
                     "formula": structure.composition.formula, **metadata})
    for row in generation["deterministic_prototype_candidates"]:
        source = ROOT / row["cif"]
        assert sha(source) == row["cif_sha256"]
        converted(row["candidate_id"], "prototype", source,
                  {"target_formula": row["target_formula"], "parent_material_id": row["parent_material_id"],
                   "structure_budget_already_charged_phase2": True})
    excluded = []
    for row in references["references"]:
        if not row["eligible_at_most_20_atoms"]:
            excluded.append({**row, "reason": "Predeclared conventional cell exceeds 20 atoms; no replacement"})
            continue
        converted(f"reference_{row['phase']}", "same_composition_reference", ROOT / row["reference_cif"],
                  {"reference_material_id": row["material_id"], "reference_phase": row["phase"]})
    cached = next(row for row in jobs if row["cached"])
    cached_path = ROOT / symmetry["cache_candidate"]["result_path"]
    cached_result = load(cached_path)
    assert sha(cached_path) == symmetry["cache_candidate"]["result_sha256"]
    assert cached_result["source_structure_sha256"] == cached["source_structure_sha256"]
    assert cached_result["checkpoint_sha256"] == sha(checkpoint)
    assert cached_result["model_version"] == "0.3.0" and cached_result["device"] == "cuda"
    assert cached_result["converged"] and cached_result["final_filter_fmax_eV_A"] <= .05
    assert sha(ROOT / cached_result["final_structure"]) == cached_result["final_structure_sha256"]
    cached.update(result_path=rel(cached_path), result_sha256=sha(cached_path),
                  prior_reservation_id="p3_chgnet_phase1_mgo_attempt_000", new_compute_charge=0,
                  cache_reuse_verified_before_all_new_jobs=True)
    for index, row in enumerate(jobs):
        row["selection_index"] = index
        row["job_id"] = row.get("prior_reservation_id", f"p5_chgnet_{row['candidate_id']}")
        if not row["cached"]:
            row["output_directory"] = rel(OUT / row["candidate_id"])
    worker_ast = next(node for node in ast.parse(old_worker.read_text(encoding="utf-8")).body
                      if isinstance(node, ast.FunctionDef) and node.name == "worker")
    settings = {"package": "0.4.2", "model_version": "0.3.0", "checkpoint_sha256": sha(checkpoint),
                "device": "cuda", "torch_threads": 2, "torch_interop_threads": 1,
                "torch_seed": 20261022, "optimizer": "FIRE", "steps_max": 200,
                "fmax_eV_A": .05, "relax_cell": True, "ase_filter": "FrechetCellFilter",
                "imposed_symmetry": False, "on_isolated_atoms": "error",
                "worker_source": rel(old_worker), "worker_source_sha256": old_hash,
                "worker_function_AST_sha256": hashlib.sha256(ast.dump(worker_ast).encode()).hexdigest(),
                "new_job_watchdog_seconds": 900, "trajectory_energy_unit": "total eV, divide actual atom count",
                "convergence_criterion": "FIRE converged and final max vector norm of FrechetCellFilter forces <=0.05",
                "settings_identity_to_cached_phase3": True}
    plan = {"frozen_utc": utc(), "status": "frozen_before_all_Phase5_CHGNet_dispatch",
            "protocol_sha256": sha(protocol), "settings": settings,
            "package_versions": {package: importlib.metadata.version(package) for package in
                                 ["chgnet", "ase", "torch", "numpy", "pymatgen"]},
            "inputs": [{"path": rel(p), "sha256": sha(p)} for p in [symmetry_path, generation_path, reference_path]],
            "source_manifest": source_manifest(), "jobs": jobs, "selections": len(jobs),
            "new_jobs": sum(not row["cached"] for row in jobs), "cached_reuses": 1,
            "fresh_transformer_shortlist": [], "excluded_references": excluded,
            "energy_dependent_selection": False, "nonconvergence_replacements": False,
            "scope": "Within-composition descriptive symmetry pairs; prototypes separate from transformer; MLIP energies are not DFT stability"}
    assert len(jobs) == 11 and plan["new_jobs"] == 10
    dump(target, plan)
    print(json.dumps({"plan": rel(target), "sha256": sha(target), "selections": 11, "new_jobs": 10,
                      "cache_verified": True}), flush=True)


def verify_sources(plan):
    for row in plan["inputs"] + plan["source_manifest"]:
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"Frozen source changed: {row['path']}")


def worker(spec_path):
    spec = load(spec_path)
    plan = load(OUT / "plan.json")
    if sha(OUT / "plan.json") != spec["plan_sha256"]:
        raise RuntimeError("Frozen plan hash mismatch")
    verify_sources(plan)
    from phase3_candidates import worker as identical_numerical_worker
    identical_numerical_worker(spec_path)


def run():
    from research_budget import reserve_job, finish_job
    plan_path = OUT / "plan.json"
    plan = load(plan_path)
    verify_sources(plan)
    for row in plan["jobs"]:
        if row["cached"]:
            continue
        source = ROOT / row["source_structure"]
        assert sha(source) == row["source_structure_sha256"]
        assert sha(ROOT / row["original_source"]) == row["original_source_sha256"]
        job = ROOT / row["output_directory"]
        if (job / "parent_result.json").exists():
            print(json.dumps({"candidate_id": row["candidate_id"], "status": "existing_result_preserved"}), flush=True)
            continue
        job.mkdir(parents=True, exist_ok=True)
        if (job / "spec.json").exists():
            raise RuntimeError("Unfinished spec exists: reconcile its existing reservation, never silently retry")
        spec = {**row, "worker_token": uuid.uuid4().hex, "plan_sha256": sha(plan_path),
                "selection_sha256": sha(plan_path), "settings": plan["settings"]}
        dump(job / "spec.json", spec)
        command = [sys.executable, "-u", str(Path(__file__).resolve()), "worker", str(job / "spec.json")]
        ticket = reserve_job(lane="chgnet", job_id=row["job_id"], attempts=1, max_seconds=900,
                             phase=5, category=row["category"], metadata={"plan_sha256": sha(plan_path),
                             "candidate_id": row["candidate_id"], "source_structure_sha256": sha(source),
                             "checkpoint_sha256": plan["settings"]["checkpoint_sha256"], "command": command})
        dump(job / "reservation.json", ticket)
        append(OUT / "ledger.jsonl", {"event": "started", "utc": utc(), **row, "plan_sha256": sha(plan_path)})
        status, returncode = "failed", None
        start = time.perf_counter()
        try:
            with (job / "run.log").open("w", encoding="utf-8") as stream:
                try:
                    process = subprocess.run(command, cwd=ROOT, env=dict(os.environ, PHASE3_CHGNET_WORKER_TOKEN=spec["worker_token"]),
                                             stdout=stream, stderr=subprocess.STDOUT, timeout=900)
                    returncode = process.returncode
                    status = "completed" if returncode == 0 else "failed"
                except subprocess.TimeoutExpired:
                    status = "timeout"
        finally:
            elapsed = time.perf_counter() - start
            result_path = job / "result.json"
            result = load(result_path) if result_path.exists() else {}
            finish_job(ticket, wall_seconds=elapsed, status=status,
                       metadata={"candidate_id": row["candidate_id"],
                                 "relaxation_started": (job / "relaxation_started.json").exists(),
                                 "result_path": rel(result_path), "converged": result.get("converged", False)})
            parent = {"job_id": row["job_id"], "candidate_id": row["candidate_id"], "category": row["category"],
                      "status": status, "returncode": returncode, "charged_wall_seconds": elapsed,
                      "finished_utc": utc(), "plan_sha256": sha(plan_path), "result": result}
            dump(job / "parent_result.json", parent)
            append(OUT / "ledger.jsonl", {"event": "finished", **parent})
        print(json.dumps({"candidate_id": row["candidate_id"], "status": status,
                          "converged": result.get("converged"), "energy_eV_per_atom": result.get("energy_eV_per_atom"),
                          "wall_seconds": elapsed}), flush=True)
    summarize()


def summarize():
    import numpy as np
    from pymatgen.core import Structure
    from pymatgen.analysis.structure_matcher import StructureMatcher
    plan = load(OUT / "plan.json")
    records = []
    for selected in plan["jobs"]:
        result_path = ROOT / selected["result_path"] if selected["cached"] else ROOT / selected["output_directory"] / "result.json"
        parent_path = result_path.parent / "parent_result.json"
        parent = load(parent_path)
        result = load(result_path) if result_path.exists() else {}
        records.append({"selection": selected, "result_path": rel(result_path),
                        "result_sha256": sha(result_path) if result_path.exists() else None,
                        "charged_wall_seconds_this_phase": 0 if selected["cached"] else parent["charged_wall_seconds"],
                        "status": parent["status"], "result": result})
    matcher = StructureMatcher(ltol=.05, stol=.1, angle_tol=5, primitive_cell=True, scale=True, attempt_supercell=False)
    pairs = []
    for control in ["mgo_rocksalt", "tio2_rutile"]:
        pair = [r for r in records if r["selection"].get("control") == control]
        assert len(pair) == 2
        byarm = {r["selection"]["arm"]: r for r in pair}
        a, b = byarm["nontrivial"], byarm["p1"]
        successful = all(r["result"].get("converged", False) for r in pair)
        pairs.append({"control": control, "scope": a["selection"]["comparison_scope"], "quota_each_arm": 1,
                      "nontrivial_id": a["selection"]["candidate_id"], "p1_id": b["selection"]["candidate_id"],
                      "both_converged": successful,
                      "p1_minus_nontrivial_eV_atom": b["result"]["energy_eV_per_atom"] - a["result"]["energy_eV_per_atom"] if successful else None,
                      "relaxed_structures_match": bool(matcher.fit(Structure.from_dict(load(ROOT / a["result"]["final_structure"])),
                                                                    Structure.from_dict(load(ROOT / b["result"]["final_structure"])))) if successful else None,
                      "inference_limit": "One selected unique structure per arm; descriptive only, no energy-distribution or architecture-causality inference"})
    references = [r for r in records if r["selection"]["category"] == "same_composition_reference"]
    ti = {r["selection"]["reference_phase"]: r for r in references if r["selection"]["reference_phase"] in {"rutile", "anatase"}}
    difference = None
    if all(ti[key]["result"].get("converged", False) for key in ["rutile", "anatase"]):
        difference = ti["anatase"]["result"]["energy_eV_per_atom"] - ti["rutile"]["result"]["energy_eV_per_atom"]
    summary = {"completed_utc": utc(), "status": "complete", "plan_sha256": sha(OUT / "plan.json"),
               "selections": len(records), "new_CHGNet_launches": 10, "cached_reuses": 1,
               "converged_selections": sum(bool(r["result"].get("converged")) for r in records),
               "new_converged_relaxations": sum(bool(r["result"].get("converged")) for r in records if not r["selection"]["cached"]),
               "charged_new_job_wall_seconds": sum(r["charged_wall_seconds_this_phase"] for r in records),
               "fresh_transformer_shortlist_relaxations": 0, "new_generation_draws": 0,
               "excluded_references": plan["excluded_references"], "results": records, "symmetry_pairs": pairs,
               "reference_anatase_minus_rutile_eV_atom": difference,
               "reference_energy_scope": "Within TiO2 only; CHGNet prediction, not DFT ground-state ordering",
               "new_stable_material_established": False,
               "comparison_rule": "No raw cross-composition energy ranking; no energy-dependent replacements or new candidate selection"}
    dump(OUT / "summary.json", summary)
    print(json.dumps({"summary": rel(OUT / "summary.json"), "converged": summary["converged_selections"],
                      "new_job_wall_seconds": summary["charged_new_job_wall_seconds"]}), flush=True)


def audit():
    """Read-only checks using saved trajectories and atomic/filter forces; no model inference."""
    import numpy as np
    from pymatgen.core import Structure
    from pymatgen.io.ase import AseAtomsAdaptor
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.filters import FrechetCellFilter
    plan = load(OUT / "plan.json")
    summary = load(OUT / "summary.json")
    checks = []
    def check(name, condition, **detail):
        checks.append({"check": name, "passed": bool(condition), **detail})
    check("summary_plan_hash", summary["plan_sha256"] == sha(OUT / "plan.json"))
    verify_sources(plan)
    events = [json.loads(line) for line in (ROOT / "artifacts/runtime_budget_events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    launched = [r for r in events if r["event"] == "reserved" and r["lane"] == "chgnet" and r["phase"] == 5]
    check("exactly_ten_new_reservations", len(launched) == 10)
    check("predeclared_job_set_only", {r["reservation_id"] for r in launched} == {r["job_id"] for r in plan["jobs"] if not r["cached"]})
    check("all_reservations_after_freeze", all(r["reserved_utc"] >= plan["frozen_utc"] for r in launched))
    for entry in summary["results"]:
        selected, result = entry["selection"], entry["result"]
        tag = selected["candidate_id"]
        source = ROOT / selected["source_structure"]
        check(tag + ":source_hash", sha(source) == selected["source_structure_sha256"])
        check(tag + ":original_source_hash", sha(ROOT / selected["original_source"]) == selected["original_source_sha256"])
        check(tag + ":result_hash", entry["result_sha256"] == sha(ROOT / entry["result_path"]))
        check(tag + ":checkpoint", result["checkpoint_sha256"] == plan["settings"]["checkpoint_sha256"])
        check(tag + ":model_and_device", result["model_version"] == "0.3.0" and result["device"] == "cuda")
        check(tag + ":final_hash", sha(ROOT / result["final_structure"]) == result["final_structure_sha256"])
        initial, final = Structure.from_dict(load(source)), Structure.from_dict(load(ROOT / result["final_structure"]))
        check(tag + ":same_composition_count", initial.composition == final.composition and len(initial) == len(final) == result["atoms"])
        trajectory_path = (ROOT / entry["result_path"]).parent / "trajectory.pkl"
        with trajectory_path.open("rb") as stream:
            trajectory = pickle.load(stream)
        check(tag + ":total_energy", abs(float(trajectory["energy"][-1]) - result["energy_total_eV"]) < 1e-9)
        check(tag + ":per_atom_normalization", abs(result["energy_total_eV"] / len(final) - result["energy_eV_per_atom"]) < 1e-10)
        atomic_fmax = float(np.linalg.norm(trajectory["forces"][-1], axis=1).max())
        stress_gpa = float(np.abs(trajectory["stresses"][-1]).max() * 160.21766208)
        check(tag + ":atomic_force_units", abs(atomic_fmax - result["final_atomic_force_norm_max_eV_A"]) < 1e-8)
        check(tag + ":stress_units", abs(stress_gpa - result["final_stress_max_abs_GPa"]) < 1e-8)
        atoms = AseAtomsAdaptor.get_atoms(initial)
        cell_filter = FrechetCellFilter(atoms)
        atoms.set_cell(trajectory["cell"][-1], scale_atoms=False)
        atoms.set_positions(trajectory["atom_positions"][-1])
        atoms.calc = SinglePointCalculator(atoms, energy=float(trajectory["energy"][-1]),
                                           forces=np.asarray(trajectory["forces"][-1]), stress=np.asarray(trajectory["stresses"][-1]))
        reconstructed = float(np.linalg.norm(cell_filter.get_forces(), axis=1).max())
        check(tag + ":filter_force_reconstructed", abs(reconstructed - result["final_filter_fmax_eV_A"]) < 2e-5,
              reconstructed_eV_A=reconstructed, reported_eV_A=result["final_filter_fmax_eV_A"])
        check(tag + ":convergence_consistent", bool(result["converged"]) == (reconstructed <= .05))
        check(tag + ":maximum_steps", result["optimizer_steps"] <= 200)
        check(tag + ":trajectory_atomic_numbers", list(trajectory["atomic_number"]) == [site.specie.Z for site in initial])
        check(tag + ":finite_saved_geometry", np.isfinite(final.cart_coords).all() and np.isfinite(final.lattice.matrix).all())
        if selected["cached"]:
            check(tag + ":no_new_reservation", all(r["metadata"]["candidate_id"] != tag for r in launched))
            check(tag + ":no_new_charge", entry["charged_wall_seconds_this_phase"] == 0)
        else:
            reserved = next(r for r in launched if r["reservation_id"] == selected["job_id"])
            finished = [r for r in events if r["event"] == "finished" and r["reservation_id"] == selected["job_id"]]
            check(tag + ":one_finish", len(finished) == 1)
            check(tag + ":charged_wall", abs(finished[0]["wall_seconds"] - entry["charged_wall_seconds_this_phase"]) < 1e-9)
            check(tag + ":category", reserved["category"] == selected["category"])
            check(tag + ":reservation_before_worker", reserved["reserved_utc"] <= load((ROOT / entry["result_path"]).parent / "worker_started.json")["started_utc"])
    check("empty_transformer_shortlist_retained", summary["fresh_transformer_shortlist_relaxations"] == 0)
    check("brookite_excluded_without_replacement", len(plan["excluded_references"]) == 1 and plan["excluded_references"][0]["phase"] == "brookite")
    check("no_discovery_claim", summary["new_stable_material_established"] is False)
    result = {"audited_utc": utc(), "status": "passed" if all(row["passed"] for row in checks) else "failed",
              "checks_count": len(checks), "failures": [r for r in checks if not r["passed"]], "checks": checks,
              "new_model_inferences": 0, "new_relaxations": 0,
              "scope": "Recorded checkpoint/source lineage, saved trajectory energy/force/stress and reconstructed cell-filter forces; not DFT validation"}
    dump(OUT / "audit.json", result)
    print(json.dumps({"audit": rel(OUT / "audit.json"), "status": result["status"], "checks": len(checks), "failures": result["failures"]}), flush=True)
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "run", "worker", "summarize", "audit"])
    parser.add_argument("spec", nargs="?")
    args = parser.parse_args()
    if args.action == "worker":
        worker(args.spec)
    else:
        globals()[args.action]()
