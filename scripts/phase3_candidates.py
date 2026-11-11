"""Frozen early-pool scoring and budgeted CHGNet pre-relaxation.

Model scores use initial generated structures exclusively. Relaxed energies never
enter selection; the original conservative/optimistic order is retained.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
for key in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"]:
    os.environ[key] = "2"
OUT = ROOT / "artifacts/phase3/selection"
MLIP = ROOT / "artifacts/phase3/chgnet"


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def append(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, allow_nan=False)+"\n")
        stream.flush()
        os.fsync(stream.fileno())


def select():
    import joblib
    import numpy as np
    from pymatgen.core import Structure
    from research_features import describe_structure, FEATURE_NAMES
    from research_models import predict_bundle
    from research_acquisition import transform_diversity, distances_to_labeled, select_fresh_pair
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "early_pool_selection.json"
    if target.exists():
        raise RuntimeError("Initial selection already frozen; inspect/reuse it rather than choosing again")
    protocol_path = ROOT / "config/phase2_protocol.json"
    summary_path = ROOT / "artifacts/phase3/generation/early_CaMg2O3/summary.json"
    summary = load(summary_path)
    manifest_path = ROOT / "artifacts/phase3/models/fresh_selector_seed_20261022.manifest.json"
    manifest = load(manifest_path)
    model_path = ROOT / manifest["path"]
    if manifest["status"] != "committed_before_any_pool_query" or sha(model_path) != manifest["sha256"]:
        raise RuntimeError("Initial immutable selector hash/status invalid")
    if manifest["pool_queries_revealed_before_snapshot"] != 0 or manifest["paired_seed"] != 20261022:
        raise RuntimeError("Fresh selector was not frozen before replay")
    bundle = joblib.load(model_path)
    if list(bundle["feature_names"]) != list(FEATURE_NAMES):
        raise RuntimeError("Model/structure descriptor schemas differ")
    representatives = summary["valid_unique_representatives"]
    ranking = []
    if representatives:
        matrices = []
        for row in representatives:
            path = ROOT / row["structure_json"]
            structure = Structure.from_dict(load(path))
            if len(structure) != 6 or structure.composition.as_dict() != {"Ca": 1, "Mg": 2, "O": 3}:
                raise RuntimeError("A purported valid representative fails exact expanded counts")
            matrices.append(describe_structure(structure))
        X = np.vstack(matrices)
        mean, std, radius = predict_bundle(bundle, X)
        diversity = transform_diversity(X, bundle["normalization"])
        distance = distances_to_labeled(diversity, bundle["initial_training_diversity_features"])
        chosen, decisions = select_fresh_pair([r["candidate_id"] for r in representatives], mean, radius, diversity, distance)
        selected = []
        for row, mu, sigma, width, dist in zip(representatives, mean, std, radius, distance):
            ranking.append({**row, "source_structure_sha256": sha(ROOT / row["structure_json"]),
                            "predicted_mean_eV_atom": float(mu), "ensemble_std_eV_atom": float(sigma),
                            "calibrated_radius_eV_atom": float(width), "distance_to_initial_training": float(dist)})
        for index, decision in zip(chosen, decisions):
            selected.append({**ranking[int(index)], "selection": decision})
        np.savez_compressed(OUT / "early_unique_initial_features.npz", X=X,
                            candidate_ids=np.array([r["candidate_id"] for r in representatives]))
    else:
        selected = []
    record = {"frozen_utc": now(), "status": "frozen_before_CHGNet_and_candidate_QE",
              "cohort": "First8CaMg2O3SG2attempts, not the later six-formula pool",
              "attempt_count": len(summary["results"]), "all_attempt_ids": [r["candidate_id"] for r in summary["results"]],
              "source_summary": summary_path.relative_to(ROOT).as_posix(), "source_summary_sha256": sha(summary_path),
              "protocol_sha256": sha(protocol_path), "initial_selector_path": model_path.relative_to(ROOT).as_posix(),
              "initial_selector_sha256": sha(model_path), "selector_frozen_utc": manifest["completed_at_utc"],
              "source_features_module_sha256": sha(ROOT / "research_features.py"),
              "selection_module_sha256": sha(ROOT / "research_acquisition.py"),
              "valid_unique_candidates": ranking, "selected": selected,
              "zero_candidate_behavior": "FrozenknownMgOattempt000fallback; no additional CaMg2O3 sampling or candidate substitution",
              "model_scoring_uses_initial_geometry_only": True, "CHGNet_or_QE_energies_used_for_selection": False}
    dump(target, record)
    print(json.dumps({"selection": str(target), "valid_unique": len(ranking), "selected": [r["candidate_id"] for r in selected]}), flush=True)


def worker(spec_path):
    import numpy as np
    spec_path = Path(spec_path)
    spec = load(spec_path)
    job = spec_path.parent
    if os.environ.get("PHASE3_CHGNET_WORKER_TOKEN") != spec["worker_token"]:
        raise RuntimeError("Only the budgeted launcher may dispatch a relaxation worker")
    marker = job / "worker_started.json"
    with marker.open("x", encoding="utf-8") as stream:
        json.dump({"started_utc": now(), "pid": os.getpid()}, stream)
    import torch
    import chgnet
    from chgnet.model.model import CHGNet
    from chgnet.model.dynamics import StructOptimizer
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from ase.optimize.fire import FIRE
    from research_features import describe_structure
    sys.path.insert(0, str(ROOT / "scripts"))
    from phase2_dft_inputs import k_grid
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(20261022)
    source = ROOT / spec["source_structure"]
    if sha(source) != spec["source_structure_sha256"]:
        raise RuntimeError("Selected initial geometry changed")
    initial = Structure.from_dict(load(source))
    model = CHGNet.load(model_name="0.3.0", use_device="cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("Frozen CUDA device is unavailable")
    tracked = {}

    class TrackingFIRE(FIRE):
        def run(self, *args, **kwargs):
            converged = super().run(*args, **kwargs)
            tracked.update(converged=bool(converged), optimizer_steps=int(self.nsteps),
                           final_filter_fmax_eV_A=float(np.linalg.norm(self.atoms.get_forces(), axis=1).max()))
            return converged

    optimizer = StructOptimizer(model=model, use_device="cuda", optimizer_class=TrackingFIRE,
                                on_isolated_atoms="error")
    dump(job / "relaxation_started.json", {"utc": now(), "model_version": model.version})
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    result = optimizer.relax(initial, fmax=.05, steps=200, relax_cell=True,
                             ase_filter="FrechetCellFilter", verbose=True,
                             save_path=str(job / "trajectory.pkl"))
    torch.cuda.synchronize()
    elapsed = time.perf_counter()-start
    final = result["final_structure"]
    dump(job / "final.json", final.as_dict())
    final.to(filename=str(job / "final.cif"))
    # Used exclusively for post-relaxation geometry/workload checks, never model scoring.
    post_features = describe_structure(final)
    protocol = load(ROOT / "config/phase2_protocol.json")
    gate = protocol["fresh_shortlist"]["DFT_pre_relaxation_eligibility"]
    geometry_ok = bool(final.composition == initial.composition and len(final) == len(initial)
                       and post_features[146] >= .75 and np.isfinite(final.lattice.matrix).all())
    grid = k_grid(final)
    reasons = []
    if not tracked.get("converged", False): reasons.append("CHGNet_nonconvergence")
    if not geometry_ok: reasons.append("invalid_final_geometry_or_stoichiometry")
    vpa = final.volume / len(final)
    if not gate["volume_per_atom_A3_inclusive"][0] <= vpa <= gate["volume_per_atom_A3_inclusive"][1]: reasons.append("volume_workload_gate")
    if max(final.lattice.abc) > gate["max_cell_vector_length_A"]: reasons.append("lattice_vector_workload_gate")
    condition = float(np.linalg.cond(final.lattice.matrix))
    if condition > gate["max_lattice_matrix_condition_number"]: reasons.append("lattice_condition_workload_gate")
    if int(np.prod(grid)) > gate["max_initial_full_kmesh_points_nosym"]: reasons.append("initial_kmesh_workload_gate")
    trajectory = result["trajectory"]
    checkpoint = Path(chgnet.__file__).parent / "pretrained/0.3.0/chgnet_0.3.0_e29f68s314m37.pth.tar"
    record = {"candidate_id": spec["candidate_id"], "status": "completed", "device": "cuda",
              "source_structure_sha256": sha(source), "final_structure": (job / "final.json").relative_to(ROOT).as_posix(),
              "final_structure_sha256": sha(job / "final.json"), "model_version": model.version,
              "checkpoint_sha256": sha(checkpoint), "relaxation_started": True,
              "relaxation_seconds": elapsed, "atoms": len(final), "formula": final.composition.formula,
              "energy_total_eV": float(trajectory.energies[-1]),
              "energy_eV_per_atom": float(trajectory.energies[-1])/len(final),
              "final_atomic_force_norm_max_eV_A": float(np.linalg.norm(trajectory.forces[-1], axis=1).max()),
              "final_stress_max_abs_GPa": float(np.abs(trajectory.stresses[-1]).max()*160.21766208),
              "final_spacegroup": int(SpacegroupAnalyzer(final, symprec=.01, angle_tolerance=5).get_space_group_number()),
              "volume_per_atom_A3": vpa, "minimum_periodic_separation_A": float(post_features[146]),
              "lattice_condition_number": condition, "initial_QE_kmesh": grid,
              "initial_QE_full_kmesh_points": int(np.prod(grid)), "DFT_eligible": not reasons,
              "DFT_ineligibility_reasons": reasons,
              "workload_gates_are_representation_sensitive_not_stability_labels": True,
              "post_relaxation_features_used_for_model_scoring": False,
              "cuda_peak_allocated_MiB": torch.cuda.max_memory_allocated()/2**20, **tracked}
    dump(job / "result.json", record)
    print(json.dumps(record), flush=True)


def launch_one(row, category, selection_sha):
    from research_budget import reserve_job, finish_job
    MLIP.mkdir(parents=True, exist_ok=True)
    candidate_id = row["candidate_id"]
    expected_source_hash = row.get("source_structure_sha256")
    if expected_source_hash is not None and sha(ROOT / row["structure_json"]) != expected_source_hash:
        raise RuntimeError("Frozen selected source geometry changed before relaxation dispatch")
    job_id = f"p3_chgnet_{candidate_id}"
    job = MLIP / candidate_id
    job.mkdir(exist_ok=True)
    result_path = job / "parent_result.json"
    if result_path.exists():
        return load(result_path)
    if (job / "spec.json").exists():
        raise RuntimeError("Unfinished job spec exists; reconcile its reservation before retrying")
    spec = {"candidate_id": candidate_id, "job_id": job_id, "source_structure": row["structure_json"],
            "source_structure_sha256": sha(ROOT / row["structure_json"]), "worker_token": uuid.uuid4().hex,
            "selection_sha256": selection_sha, "category": category}
    dump(job / "spec.json", spec)
    command = [sys.executable, "-u", str(Path(__file__).resolve()), "worker", str(job / "spec.json")]
    ticket = reserve_job("chgnet", job_id, attempts=1, max_seconds=900, category=category,
                         metadata={"candidate_id": candidate_id, "source_structure_sha256": spec["source_structure_sha256"],
                                   "selection_sha256": selection_sha, "command": command})
    dump(job / "reservation.json", ticket)
    environment = dict(os.environ, PHASE3_CHGNET_WORKER_TOKEN=spec["worker_token"])
    append(MLIP / "ledger.jsonl", {"event": "started", "utc": now(), "job_id": job_id, "candidate_id": candidate_id, "category": category})
    begin = time.perf_counter()
    status, returncode = "failed", None
    try:
        with (job / "run.log").open("w", encoding="utf-8") as log:
            try:
                completed = subprocess.run(command, cwd=ROOT, env=environment,
                                           stdout=log, stderr=subprocess.STDOUT, timeout=900)
                returncode = completed.returncode
                status = "completed" if returncode == 0 else "failed"
            except subprocess.TimeoutExpired:
                status = "timeout"
    finally:
        elapsed = time.perf_counter()-begin
        result = load(job / "result.json") if (job / "result.json").exists() else {}
        started = (job / "relaxation_started.json").exists()
        finish_job(ticket, wall_seconds=elapsed, status=status,
                   metadata={"candidate_id": candidate_id, "relaxation_started": started,
                             "DFT_eligible": result.get("DFT_eligible", False),
                             "result_path": (job / "result.json").relative_to(ROOT).as_posix()})
        record = {"job_id": job_id, "candidate_id": candidate_id, "status": status, "returncode": returncode,
                  "charged_wall_seconds": elapsed, "category": category, "result": result, "finished_utc": now()}
        dump(result_path, record)
        append(MLIP / "ledger.jsonl", {"event": "finished", **record})
    print(json.dumps({"candidate_id": candidate_id, "status": status, "DFT_eligible": result.get("DFT_eligible", False), "wall_seconds": elapsed}), flush=True)
    return record


def relax():
    existing_handoff = OUT / "DFT_handoff.json"
    if existing_handoff.exists():
        print(json.dumps({"status": "existing_frozen_handoff_preserved", "path": str(existing_handoff)}))
        return
    selection_path = OUT / "early_pool_selection.json"
    selection = load(selection_path)
    records = [launch_one(row, "new_composition_shortlist", sha(selection_path)) for row in selection["selected"]]
    eligible = [r for r in records if r["result"].get("DFT_eligible", False)]
    fallback = None
    if not eligible:
        protocol = load(ROOT / "config/phase2_protocol.json")
        frozen = protocol["fresh_shortlist"]["known_MgO_DFT_fallback"]
        if sha(ROOT / frozen["source_structure"]) != frozen["source_structure_sha256"]:
            raise RuntimeError("The predeclared fallback control differs from its frozen source hash")
        fallback_path = OUT / "fallback_decision.json"
        if not fallback_path.exists():
            import joblib
            import numpy as np
            from pymatgen.core import Structure
            from research_features import describe_structure
            from research_models import predict_bundle
            model_path = ROOT / selection["initial_selector_path"]
            if sha(model_path) != selection["initial_selector_sha256"]:
                raise RuntimeError("Immutable initial selector changed before fallback scoring")
            bundle = joblib.load(model_path)
            initial = Structure.from_dict(load(ROOT / frozen["source_structure"]))
            mean, std, radius = predict_bundle(bundle, describe_structure(initial)[None, :])
            dump(fallback_path, {"frozen_utc": now(), "trigger": "No valid primary structure or none of the preselected primary structures passed CHGNet/DFT workload eligibility",
                                 "candidate_id": frozen["candidate_id"], "source_structure": frozen["source_structure"],
                                 "source_sha256": frozen["source_structure_sha256"],
                                 "initial_selector_sha256": selection["initial_selector_sha256"],
                                 "predicted_mean_eV_atom": float(mean[0]), "ensemble_std_eV_atom": float(std[0]),
                                 "calibrated_radius_eV_atom": float(radius[0]),
                                 "predetermined_candidate_not_replaced_by_scoring": True,
                                 "original_selection_sha256": sha(selection_path),
                                 "original_attempts_and_failures_retained": True, "DFT_energies_used": False})
        row = {"candidate_id": frozen["candidate_id"], "structure_json": frozen["source_structure"],
               "source_structure_sha256": frozen["source_structure_sha256"]}
        fallback = launch_one(row, "contingency", sha(fallback_path))
        if fallback["result"].get("DFT_eligible", False): eligible.append(fallback)
    # Keep frozen selection order; detect collapsed relaxed structures without replacements.
    from pymatgen.core import Structure
    from pymatgen.analysis.structure_matcher import StructureMatcher
    matcher = StructureMatcher(ltol=.05, stol=.1, angle_tol=5, primitive_cell=True, scale=True, attempt_supercell=False)
    unique, unique_structures = [], []
    for record in eligible:
        structure = Structure.from_dict(load(ROOT / record["result"]["final_structure"]))
        match = next((prior["candidate_id"] for prior, geometry in zip(unique, unique_structures) if matcher.fit(structure, geometry)), None)
        if match is None:
            unique.append(record)
            unique_structures.append(structure)
        else:
            record["relaxed_duplicate_of"] = match
    handoff = {"frozen_utc": now(), "selection_sha256": sha(selection_path), "original_selected": selection["selected"],
               "primary_results": records, "fallback_result": fallback,
               "DFT_queue_in_frozen_order": [{"candidate_id": r["candidate_id"], "final_structure": r["result"]["final_structure"],
                                              "final_structure_sha256": r["result"]["final_structure_sha256"],
                                              "CHGNet_result_path": f"artifacts/phase3/chgnet/{r['candidate_id']}/result.json"} for r in unique],
               "no_reordering_by_CHGNet_energy": True, "deduplicated_relaxed_candidates": len(unique),
               "new_DFT_outcomes_used": False}
    dump(OUT / "DFT_handoff.json", handoff)
    print(json.dumps({"DFT_handoff": str(OUT / "DFT_handoff.json"), "queue": [r["candidate_id"] for r in handoff["DFT_queue_in_frozen_order"]]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("select")
    sub.add_parser("relax")
    item = sub.add_parser("worker")
    item.add_argument("spec")
    args = parser.parse_args()
    if args.command == "select": select()
    elif args.command == "relax": relax()
    else: worker(args.spec)
