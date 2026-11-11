"""Four bounded engineering relaxations; CPU/CUDA pairs are not research samples."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase1/chgnet_relaxation"
SEED = 20261022
SPEC = [("cpu", "primitive"), ("cuda", "primitive"),
        ("cpu", "perturbed_conventional"), ("cuda", "perturbed_conventional")]


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def append(value):
    with (OUT / "ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, allow_nan=False) + "\n")
        handle.flush()


def worker(index):
    attempt_id = f"chgnet_pilot_{index + 1:02d}"
    ledger_path = OUT / "ledger.jsonl"
    events = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()] if ledger_path.exists() else []
    starts = [event for event in events if event.get("attempt_id") == attempt_id and event.get("event") == "start"]
    finished = any(event.get("attempt_id") == attempt_id and event.get("event") == "finish" for event in events)
    if len(starts) != 1 or finished or starts[0].get("worker_token") != os.environ.get("PHASE1_CHGNET_WORKER_TOKEN"):
        raise RuntimeError("Workers must be dispatched once by the budget-recording launcher")
    # Set caps before importing libraries. QE has its own independent four-thread cap.
    os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
    for key in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"]:
        os.environ[key] = "2"
    import numpy as np
    import torch
    import chgnet
    from chgnet.model.model import CHGNet
    from chgnet.model.dynamics import StructOptimizer
    from ase.optimize.fire import FIRE
    from pymatgen.core import Lattice, Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    device, structure_kind = SPEC[index]
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false")
    structure = Structure.from_spacegroup(225, Lattice.cubic(4.212),
                                        ["Mg", "O"], [[0, 0, 0], [.5, .5, .5]])
    if structure_kind == "primitive":
        structure = structure.get_primitive_structure()
    else:
        structure.apply_strain([.04, -.02, .03])
        displacements = np.random.default_rng(SEED).normal(0, .03, (len(structure), 3))
        for atom_index, delta in enumerate(displacements):
            structure.translate_sites([atom_index], delta, frac_coords=False, to_unit_cell=True)
    attempt = OUT / f"attempt_{index + 1:02d}_{device}"
    attempt.mkdir(exist_ok=True)
    structure.to(filename=str(attempt / "initial.cif"))
    write_json(attempt / "initial.json", structure.as_dict())
    model_start = time.perf_counter()
    model = CHGNet.load(model_name="0.3.0", use_device=device)
    if device == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    load_seconds = time.perf_counter() - model_start
    checkpoint = Path(chgnet.__file__).parent / "pretrained/0.3.0/chgnet_0.3.0_e29f68s314m37.pth.tar"
    tracked = {}

    class TrackingFIRE(FIRE):
        def run(self, *args, **kwargs):
            result = super().run(*args, **kwargs)
            tracked["converged"] = bool(result)
            tracked["optimizer_steps"] = int(self.nsteps)
            tracked["final_filter_fmax_eV_A"] = float(
                np.linalg.norm(self.atoms.get_forces(), axis=1).max())
            return result

    optimizer = StructOptimizer(model=model, use_device=device,
                                optimizer_class=TrackingFIRE,
                                on_isolated_atoms="error")
    start = time.perf_counter()
    result = optimizer.relax(structure, fmax=.05, steps=200, relax_cell=True,
                             ase_filter="FrechetCellFilter", verbose=True,
                             save_path=str(attempt / "trajectory.pkl"))
    if device == "cuda":
        torch.cuda.synchronize()
    seconds = time.perf_counter() - start
    final = result["final_structure"]
    final.to(filename=str(attempt / "final.cif"))
    write_json(attempt / "final.json", final.as_dict())
    trajectory = result["trajectory"]
    energy_total = float(trajectory.energies[-1])
    fmax = float(np.linalg.norm(trajectory.forces[-1], axis=1).max())
    matrix = final.distance_matrix.copy()
    np.fill_diagonal(matrix, np.inf)
    # Periodic self images are checked explicitly, including a one-atom edge case.
    from itertools import product
    translations = np.array([x for x in product([-1, 0, 1], repeat=3) if any(x)])
    self_min = float(np.linalg.norm(translations @ final.lattice.matrix, axis=1).min())
    valid = bool(np.isfinite(energy_total) and final.volume > 0
                 and final.composition == structure.composition
                 and min(float(matrix.min()), self_min) > .7)
    record = {
        "attempt_id": f"chgnet_pilot_{index + 1:02d}", "status": "completed",
        "device": device, "structure_kind": structure_kind, "seed": SEED,
        "atoms": len(final), "formula": final.composition.formula,
        "model_version": model.version, "checkpoint_path": str(checkpoint.relative_to(ROOT)),
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "packages": {name: importlib.metadata.version(name) for name in
                     ["chgnet", "torch", "numpy", "ase", "pymatgen"]},
        "model_load_seconds": load_seconds, "relaxation_seconds": seconds,
        "energy_total_eV": energy_total, "energy_eV_per_atom": energy_total / len(final),
        "final_atom_fmax_eV_A": fmax,
        "final_max_abs_stress_GPa": float(np.abs(trajectory.stresses[-1]).max() * 160.21766208),
        "valid_geometry_and_composition": valid,
        "initial_spacegroup_symprec_0_01": int(SpacegroupAnalyzer(structure, symprec=.01).get_space_group_number()),
        "final_spacegroup_symprec_0_01": int(SpacegroupAnalyzer(final, symprec=.01).get_space_group_number()),
        "volume_initial_A3": structure.volume, "volume_final_A3": final.volume,
        "cuda_peak_allocated_MiB": (torch.cuda.max_memory_allocated() / 2**20 if device == "cuda" else None),
        "engineering_only": True, "primary_symmetry_sample": False,
        "trajectory_energy_units": "total eV; divided by actual atom count above",
        **tracked,
    }
    write_json(attempt / "result.json", record)
    print(json.dumps(record), flush=True)


def launch():
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / ".cache/matplotlib").mkdir(parents=True, exist_ok=True)
    # A rerun may inspect prior results but cannot silently consume another four attempts.
    if (OUT / "ledger.jsonl").exists():
        raise SystemExit("A pilot ledger already exists. Inspect it; additional attempts require an explicit revised allocation.")
    records = []
    for index, (device, kind) in enumerate(SPEC):
        attempt_id = f"chgnet_pilot_{index + 1:02d}"
        attempt = OUT / f"attempt_{index + 1:02d}_{device}"
        attempt.mkdir(exist_ok=True)
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(index)]
        start_wall = now()
        worker_token = uuid.uuid4().hex
        worker_environment = dict(os.environ, PHASE1_CHGNET_WORKER_TOKEN=worker_token)
        append({"event": "start", "attempt_id": attempt_id, "utc": start_wall,
                "phase": 1, "device": device, "kind": kind, "command": command,
                "launcher_pid": os.getpid(),
                "worker_token": worker_token,
                "timeout_seconds": 900, "attempts": 1, "engineering_only": True})
        print(f"Starting {attempt_id}: {device}, {kind}", flush=True)
        begin = time.perf_counter()
        with (attempt / "run.log").open("w", encoding="utf-8") as log:
            try:
                completed = subprocess.run(command, cwd=ROOT, stdout=log,
                                           stderr=subprocess.STDOUT, timeout=900,
                                           env=worker_environment)
                returncode, status = completed.returncode, "completed" if completed.returncode == 0 else "failed"
            except subprocess.TimeoutExpired:
                returncode, status = None, "timeout"
        seconds = time.perf_counter() - begin
        record = {"event": "finish", "attempt_id": attempt_id, "utc": now(),
                  "started_utc": start_wall, "wall_seconds": seconds,
                  "budget_charged_seconds": seconds, "status": status, "returncode": returncode,
                  "attempts": 1, "phase": 1, "device": device}
        result_path = attempt / "result.json"
        if result_path.exists():
            record["result"] = json.loads(result_path.read_text(encoding="utf-8"))
        append(record)
        records.append(record)
        print(json.dumps({key: record[key] for key in ["attempt_id", "status", "wall_seconds"]}), flush=True)
        if status != "completed":
            print("Stopping after this failure; inspect its log before allocating any retry.", flush=True)
            break
    summary = {"attempts": len(records), "charged_wall_seconds": sum(r["wall_seconds"] for r in records),
               "successful": sum(r["status"] == "completed" for r in records),
               "converged": sum(r.get("result", {}).get("converged", False) for r in records),
               "all_geometry_valid": all(r.get("result", {}).get("valid_geometry_and_composition", False) for r in records),
               "records": records, "production_steps": 200, "production_fmax_eV_A": .05,
               "thread_cap": 2, "cuda_ready": any(r["device"] == "cuda" and r["status"] == "completed" for r in records)}
    write_json(OUT / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}), flush=True)
    return 0 if summary["successful"] == 4 and summary["converged"] == 4 and summary["all_geometry_valid"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=int, choices=range(4))
    args = parser.parse_args()
    if args.worker is None:
        raise SystemExit(launch())
    try:
        worker(args.worker)
    except Exception:
        traceback.print_exc()
        raise
