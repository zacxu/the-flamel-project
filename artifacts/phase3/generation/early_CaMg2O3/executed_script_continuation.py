"""Budgeted CrystalFormer sampling from frozen Phase 2 protocols.

The supervisor reserves every attempt before launching a CPU worker and records
its finish, including timeouts. No ranking, model fitting or relaxation occurs.
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read(path): return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def event(out, event_type, **values):
    row = {"utc": datetime.now(timezone.utc).isoformat(), "event": event_type, **values}
    with (out / "ledger.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, allow_nan=False) + "\n")
        stream.flush()
    print(json.dumps(row), flush=True)


def case_config(args):
    new_path = ROOT / "artifacts/phase2/compositions/generation_protocol.json"
    controls_path = ROOT / "artifacts/phase2/controls/matched_protocol.json"
    new = read(new_path)
    if args.control:
        controls = read(controls_path)
        case = next(row for row in controls["controls"] if row["label"] == args.control)
        selected = {"formula": case["evaluated_formula"], "conditioning_formula": case["conditioning_formula"],
            "evaluated_formula": case["evaluated_formula"], "exact_expanded_counts": case["exact_element_counts"],
            "evaluated_n_atoms": case["evaluated_n_atoms"], "chemical_system": case["chemical_system"],
            "sampling_seed": controls["seed"], "spacegroup": 1 if args.arm == "p1" else case["nontrivial_spacegroup"],
            "attempts": controls["primary_attempts_per_arm_per_formula"], "batch_size": controls["batch_size"]}
        source_protocol = controls_path
    else:
        selected = next(row for row in new["formulas"] if row["formula"] == args.formula)
        source_protocol = new_path
    config = {"run_id": args.run_id, "phase": args.phase, "case": selected,
        "source_protocol": source_protocol.relative_to(ROOT).as_posix(), "source_protocol_sha256": sha256(source_protocol),
        "source_revision": new["source_revision"], "checkpoint_revision": new["checkpoint_revision"],
        "checkpoint_sha256": new["checkpoint_sha256"], "temperature": new["temperature"], "top_p": new["top_p"],
        "deduplication": new["deduplication"], "minimum_distance_angstrom": new["minimum_distance_angstrom"],
        "expanded_atom_cap": new["expanded_atom_cap"], "symprec_angstrom": new["symprec_angstrom"],
        "angle_tolerance_degrees": new["angle_tolerance_degrees"],
        "architecture": read(ROOT / "artifacts/phase1/generator/config.json")["architecture"],
        "candidate_ids": [f"{args.run_id}_attempt_{index:03d}" for index in range(selected["attempts"])],
        "cpu_affinity_mask": "0xF", "logical_cpu_limit": 4,
        "periodic_distance_definition": "Minimum of distinct-site periodic distance and shortest nonzero lattice translation (includes atom/self-image separation).",
        "timing_interpretation": "First call includes SG-specific JIT compilation and sampling; later same-shape call is warm. Comparison with Phase 1 SG225 changes group and composition, and is not an isolated formula-change experiment."}
    if selected["attempts"] != 8 or selected["batch_size"] != 4:
        raise RuntimeError("This frozen primary sampler requires exactly eight attempts in batches of four")
    return config


def verify_inputs(out, config, filename="verification.json"):
    checkpoint = ROOT / "checkpoints/epoch_044000.pkl"
    actual = sha256(checkpoint)
    if actual != config["checkpoint_sha256"]:
        raise RuntimeError("Checkpoint SHA256 mismatch")
    provenance = read(ROOT / "artifacts/phase1/generator/provenance.json")
    if provenance["source_revision"] != config["source_revision"]:
        raise RuntimeError("Source revision differs from frozen protocol")
    for row in provenance["files"]:
        if sha256(ROOT / "vendor/CrystalFormer" / row["path"]) != row["sha256"]:
            raise RuntimeError(f"Pinned source changed: {row['path']}")
    verification = {"source_files_verified": len(provenance["files"]), "source_revision": config["source_revision"],
        "checkpoint_sha256": actual, "checkpoint_bytes": checkpoint.stat().st_size,
        "protocol_sha256": config["source_protocol_sha256"], "script_sha256": sha256(Path(__file__)),
        "verified_before_budget_reservation": True, "model_draws": 0}
    write(out / filename, verification)
    return verification


def affinity():
    if os.name != "nt": return {"applied": False, "requested_logical_cpus": 4}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    applied = bool(kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 0xF))
    return {"applied": applied, "mask": "0xF", "requested_logical_cpus": 4}


def worker(out, resume_saved_first_batch=False):
    started = time.perf_counter()
    config = read(out / "config.json")
    case = config["case"]
    os.environ["JAX_PLATFORMS"] = "cpu"
    os.environ["JAX_COMPILATION_CACHE_DIR"] = str(out / "jax_cache")
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[name] = "4"
    applied_affinity = affinity()
    sys.path.insert(0, str(ROOT / "vendor/CrystalFormer"))
    event(out, "worker_started", pid=os.getpid(), cpu_affinity=applied_affinity, case=case,
          resume_saved_first_batch=resume_saved_first_batch)
    import numpy as np
    import jax
    import jax.numpy as jnp
    from pymatgen.core import Lattice, Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from crystalformer.src.transformer import make_transformer
    from crystalformer.src.sample import make_sample_crystal
    from crystalformer.src.formula import formula_string_to_composition_vector
    from crystalformer.src.checkpoint import load_data
    from crystalformer.src.wyckoff import symops, mult_table, wmax_table
    if jax.default_backend() != "cpu": raise RuntimeError("Unexpected non-CPU backend")
    init_start = time.perf_counter()
    initial, transformer = make_transformer(jax.random.PRNGKey(42), **config["architecture"])
    path = ROOT / "checkpoints/epoch_044000.pkl"
    if sha256(path) != config["checkpoint_sha256"]: raise RuntimeError("Checkpoint changed before load")
    checkpoint = load_data(str(path))
    params = checkpoint["params"]
    random_leaves, random_tree = jax.tree_util.tree_flatten(initial)
    leaves, tree = jax.tree_util.tree_flatten(params)
    if tree != random_tree or [item.shape for item in leaves] != [item.shape for item in random_leaves]:
        raise RuntimeError("Checkpoint parameter tree/shape mismatch")
    if all(np.array_equal(np.asarray(a), np.asarray(b)) for a, b in zip(leaves, random_leaves)):
        raise RuntimeError("Loaded weights equal random initialization")
    event(out, "checkpoint_loaded", parameter_count=sum(int(item.size) for item in leaves),
          initialization_load_seconds=time.perf_counter() - init_start,
          checkpoint_sha256=config["checkpoint_sha256"], backend=jax.default_backend())
    del checkpoint, initial, random_leaves
    composition = formula_string_to_composition_vector(case["conditioning_formula"])
    sampler = make_sample_crystal(transformer, n_max=21, atom_types=119, wyck_types=28, Kx=16, Kl=4,
        w_mask=None, top_p=config["top_p"], temperature=config["temperature"], K=0,
        g=case["spacegroup"], atom_mask=jnp.ones(119, dtype=int))
    matrices, multiplicity, max_w = np.asarray(symops), np.asarray(mult_table), np.asarray(wmax_table)
    matcher = StructureMatcher(**config["deduplication"])
    representatives, results, timings = [], [], []
    (out / "cifs").mkdir(exist_ok=True)

    def expand(g, lattice, species, wyckoff, points):
        atoms, coords = [], []
        for z, w, point in zip(species, wyckoff, points):
            z, w = int(z), int(w)
            if z == 0: continue
            if w <= 0: raise ValueError("Non-padding atom has no Wyckoff position")
            general = int(max_w[g - 1]); number = int(multiplicity[g - 1, general])
            orbit = matrices[g - 1, general, :number] @ np.r_[point, 1.0]
            orbit %= 1.0
            op = matrices[g - 1, w, 0]
            differences = orbit @ op[:, :3].T + op[:, 3] - orbit
            differences -= np.rint(differences)
            generator = orbit[np.argmin((differences**2).sum(axis=1))]
            number = int(multiplicity[g - 1, w])
            positions = (matrices[g - 1, w, :number] @ np.r_[generator, 1.0]) % 1.0
            atoms.extend([z] * number); coords.extend(positions.tolist())
        return Structure(Lattice.from_parameters(*map(float, lattice)), atoms, coords)

    def minimum_periodic_distance(structure):
        distance = structure.distance_matrix.copy()
        np.fill_diagonal(distance, np.inf)
        pair_minimum = float(distance.min()) if len(structure) > 1 else float("inf")
        reduced = structure.lattice.get_lll_reduced_lattice()
        radius = min(reduced.abc) + 1e-7
        images = reduced.get_points_in_sphere([[0.0, 0.0, 0.0]], [0.0, 0.0, 0.0], radius)
        image_distances = [float(item[1]) for item in images if float(item[1]) > 1e-8]
        if not image_distances: raise ValueError("Cannot determine nonzero periodic self-image distance")
        self_minimum = min(image_distances)
        return min(pair_minimum, self_minimum), pair_minimum, self_minimum

    key = jax.random.PRNGKey(case["sampling_seed"])
    for batch in range(2):
        indexes = list(range(batch * 4, batch * 4 + 4))
        recovering = resume_saved_first_batch and batch == 0
        if not recovering:
            for index in indexes:
                event(out, "attempt_started", candidate_id=config["candidate_ids"][index], attempt_id=index, batch_index=batch)
        sample_start = time.perf_counter()
        try:
            if recovering:
                with np.load(out / "raw_batch_00.npz") as saved:
                    arrays = tuple(saved[name] for name in ("G", "XYZ", "A", "W", "M", "L"))
            else:
                raw = sampler(jax.random.fold_in(key, batch), params, 4, composition)
                arrays = jax.tree_util.tree_map(lambda item: np.asarray(item.block_until_ready()), raw)
            elapsed = time.perf_counter() - sample_start
            G, XYZ, A, W, M, L = arrays
            if not recovering:
                np.savez_compressed(out / f"raw_batch_{batch:02d}.npz", G=G, XYZ=XYZ, A=A, W=W, M=M, L=L)
        except Exception:
            elapsed = time.perf_counter() - sample_start
            failure = traceback.format_exc()
            timings.append({"batch_index": batch, "seconds": elapsed, "sampling_success": False})
            for index in indexes:
                row = {"candidate_id": config["candidate_ids"][index], "attempt_id": index,
                       "batch_index": batch, "valid": False, "duplicate_of": None,
                       "rejection_reasons": ["sampling_failure"], "error": failure}
                results.append(row); event(out, "attempt_completed", **row)
            continue
        if recovering:
            prior = [json.loads(line) for line in (out / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
            first = next(row for row in prior if row["event"] == "attempt_started" and row["attempt_id"] == 0)
            failure = next(row for row in prior if row["event"] == "worker_failed")
            bound = (datetime.fromisoformat(failure["utc"]) - datetime.fromisoformat(first["utc"])).total_seconds()
            timings.append({"batch_index": batch, "seconds": None, "sampling_success": True,
                "kind": "saved_batch_validated_without_resampling",
                "recovery_read_seconds": elapsed, "original_sampling_call_upper_bound_seconds": bound,
                "timing_limit": "Exact timer was lost at the logging exception; upper bound includes persistence and error handling."})
        else:
            kind = ("first_call_of_continuation_process_including_JIT_or_cache_lookup" if resume_saved_first_batch
                    else "first_call_including_compilation" if batch == 0 else "same_shape_warm_call")
            timings.append({"batch_index": batch, "seconds": elapsed, "sampling_success": True, "kind": kind})
        event(out, "batch_sampled", **timings[-1], attempts=4)
        for local, index in enumerate(indexes):
            candidate_id = config["candidate_ids"][index]
            raw_row = {"G": int(G[local]), "XYZ": XYZ[local].tolist(), "A": A[local].tolist(),
                       "W": W[local].tolist(), "M": M[local].tolist(), "L": L[local].tolist()}
            # NPZ is the exact numeric record; JSON retains nonfinite values as
            # explicit strings when necessary instead of emitting invalid JSON.
            def safe(value):
                if isinstance(value, float) and not math.isfinite(value): return str(value)
                if isinstance(value, list): return [safe(item) for item in value]
                if isinstance(value, dict): return {name: safe(item) for name, item in value.items()}
                return value
            raw_path = out / f"raw_attempt_{index:03d}.json"; write(raw_path, safe(raw_row))
            row = {"candidate_id": candidate_id, "attempt_id": index, "batch_index": batch,
                   "valid": False, "duplicate_of": None, "rejection_reasons": [],
                   "raw_json": raw_path.relative_to(ROOT).as_posix()}
            try:
                if not np.isfinite(XYZ[local]).all() or not np.isfinite(L[local]).all():
                    raise ValueError("Nonfinite coordinates or lattice")
                structure = expand(int(G[local]), L[local], A[local], W[local], XYZ[local])
                if not math.isfinite(structure.volume) or structure.volume <= 0:
                    raise ValueError("Nonpositive or nonfinite cell volume")
                structure_path = out / f"structure_{index:03d}.json"
                cif_path = out / "cifs" / f"attempt_{index:03d}.cif"
                write(structure_path, structure.as_dict()); structure.to(filename=str(cif_path), fmt="cif")
                counts = {symbol: int(amount) for symbol, amount in structure.composition.get_el_amt_dict().items()}
                minimum, pair_minimum, self_minimum = minimum_periodic_distance(structure)
                analyzer = SpacegroupAnalyzer(structure, symprec=config["symprec_angstrom"],
                                              angle_tolerance=config["angle_tolerance_degrees"])
                row.update(structure_json=structure_path.relative_to(ROOT).as_posix(),
                    cif=cif_path.relative_to(ROOT).as_posix(), cif_sha256=sha256(cif_path),
                    counts=counts, n_atoms=len(structure), volume_angstrom3=float(structure.volume),
                    minimum_periodic_distance_angstrom=minimum,
                    minimum_distinct_site_periodic_distance_angstrom=pair_minimum if math.isfinite(pair_minimum) else None,
                    minimum_self_image_distance_angstrom=self_minimum,
                    measured_spacegroup=int(analyzer.get_space_group_number()),
                    measured_spacegroup_symbol=analyzer.get_space_group_symbol())
                if counts != case["exact_expanded_counts"]: row["rejection_reasons"].append("exact_composition_mismatch")
                if len(structure) != case["evaluated_n_atoms"] or len(structure) > config["expanded_atom_cap"]:
                    row["rejection_reasons"].append("expanded_atom_count_mismatch")
                if minimum < config["minimum_distance_angstrom"]:
                    row["rejection_reasons"].append("minimum_periodic_distance_below_threshold")
                row["valid"] = not row["rejection_reasons"]
                if row["valid"]:
                    duplicate = next((other["candidate_id"] for other, previous in representatives if matcher.fit(structure, previous)), None)
                    row["duplicate_of"] = duplicate
                    if duplicate is None: representatives.append((row.copy(), structure))
            except Exception:
                row["valid"] = False
                row["rejection_reasons"].append("conversion_or_validation_failure")
                row["validation_error"] = traceback.format_exc()
            results.append(row); event(out, "attempt_completed", **row)
    unique_rows = [row for row, _ in representatives]
    summary = {"run_id": config["run_id"], "formula": case["evaluated_formula"],
        "conditioning_formula": case["conditioning_formula"], "requested_spacegroup": case["spacegroup"],
        "source_protocol_sha256": config["source_protocol_sha256"], "attempts": len(results),
        "valid_count": sum(row["valid"] for row in results), "valid_unique_count": len(unique_rows),
        "batch_timings": timings, "worker_wall_seconds": time.perf_counter() - started,
        "results": results, "valid_unique_representatives": unique_rows,
        "timing_interpretation": config["timing_interpretation"],
        "status": "completed" if all(row["sampling_success"] for row in timings) else "failed"}
    if resume_saved_first_batch:
        summary["budget_accounting"] = {"charged_reservation_attempts": 12, "actual_model_draws": 8,
            "unemitted_engineering_slots_charged": 4,
            "original_reservation_id": read(out / "reservation.json")["reservation_id"],
            "continuation_reservation_id": read(out / "continuation_reservation.json")["reservation_id"],
            "reason": "Original eight-attempt reservation ended after saving batch00 and a logging failure; it remains fully charged. Authorized continuation reserved four additional slots and emitted only original batch01, retaining the original seed, IDs and all first-batch mismatches."}
        summary["source_version_audit"] = {
            "original_executed_script": "executed_script_before_logging_fix.py",
            "original_script_sha256": sha256(out / "executed_script_before_logging_fix.py"),
            "continuation_executed_script": "executed_script_continuation.py",
            "continuation_script_sha256": sha256(out / "executed_script_continuation.py"),
            "raw_first_batch_resampled": False, "continued_key_batch_index": 1,
            "same_shape_warm_timing_available": False}
    assert len(results) == 8 and len({row["candidate_id"] for row in results}) == 8
    write(out / "summary.json", summary)
    write(out / "valid_unique_representatives.json", {"run_id": config["run_id"],
        "formula": case["evaluated_formula"], "representatives": unique_rows,
        "source_protocol_sha256": config["source_protocol_sha256"]})
    event(out, "worker_completed", valid=summary["valid_count"], unique=summary["valid_unique_count"],
          attempts=8, seconds=summary["worker_wall_seconds"])
    return 0 if summary["status"] == "completed" else 1


def main():
    parser = argparse.ArgumentParser()
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument("--formula", default=None)
    choices.add_argument("--control", default=None)
    parser.add_argument("--arm", choices=["nontrivial", "p1"], default="nontrivial")
    parser.add_argument("--run-id", default="phase3_early_CaMg2O3")
    parser.add_argument("--output", default="artifacts/phase3/generation/early_CaMg2O3")
    parser.add_argument("--phase", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--resume-saved-first-batch", action="store_true",
                        help="Explicit engineering continuation: reuse raw batch00 and generate only original batch01 under a new four-slot reservation.")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.formula and not args.control: args.formula = "CaMg2O3"
    out = (ROOT / args.output).resolve()
    if not out.is_relative_to(ROOT / "artifacts"):
        raise RuntimeError("Output must remain inside workspace artifacts")
    out.mkdir(parents=True, exist_ok=True)
    if args.worker:
        try: return worker(out, resume_saved_first_batch=args.resume_saved_first_batch)
        except Exception:
            event(out, "worker_failed", error=traceback.format_exc())
            raise
    config = case_config(args)
    verify_inputs(out, config, "continuation_verification.json" if args.resume_saved_first_batch else "verification.json")
    if args.verify_only:
        print(json.dumps({"verified": True, "formula": config["case"], "model_draws": 0}, indent=2))
        return 0
    if args.resume_saved_first_batch:
        if (out / "continuation_reservation.json").exists() or (out / "summary.json").exists():
            raise RuntimeError("Continuation already reserved/completed; no silent repeat")
        if not (out / "raw_batch_00.npz").is_file() or (out / "raw_batch_01.npz").exists():
            raise RuntimeError("Continuation requires exactly one saved first batch")
        if read(out / "finish.json")["status"] != "failed":
            raise RuntimeError("Only an explicitly failed original run can use this continuation")
        history = [json.loads(line) for line in (out / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
        if [row["attempt_id"] for row in history if row["event"] == "attempt_started"] != [0, 1, 2, 3]:
            raise RuntimeError("Unexpected original attempt ledger")
    elif (out / "reservation.json").exists() or (out / "summary.json").exists():
        raise RuntimeError("Existing reservation/results: inspect artifacts instead of rerunning")
    if (out / "config.json").exists() and read(out / "config.json") != config:
        raise RuntimeError("Existing configuration differs")
    write(out / "config.json", config)
    import research_budget
    reservation_id = args.run_id + "_continuation_batch01" if args.resume_saved_first_batch else args.run_id
    reserved_ids = config["candidate_ids"][4:] if args.resume_saved_first_batch else config["candidate_ids"]
    ticket = research_budget.reserve_job(lane="generation", job_id=reservation_id, attempts=len(reserved_ids),
        max_seconds=args.timeout_seconds, phase=args.phase, category="crystalformer",
        metadata={"formula": config["case"]["evaluated_formula"], "protocol_sha256": config["source_protocol_sha256"],
                  "output_dir": out.relative_to(ROOT).as_posix(), "candidate_ids": reserved_ids,
                  "script_sha256": sha256(Path(__file__)), "source_verified": True,
                  "continuation_of_failed_reservation": args.run_id if args.resume_saved_first_batch else None,
                  "model_batch_index": 1 if args.resume_saved_first_batch else None})
    write(out / ("continuation_reservation.json" if args.resume_saved_first_batch else "reservation.json"), ticket)
    if args.resume_saved_first_batch:
        (out / "executed_script_continuation.py").write_bytes(Path(__file__).read_bytes())
    event(out, "canonical_budget_reserved", **ticket)
    started = time.perf_counter()
    status, returncode = "failed", 1
    try:
        with (out / ("continuation_run.log" if args.resume_saved_first_batch else "run.log")).open("wb") as log:
            command = [sys.executable, "-u", str(Path(__file__).resolve()), "--worker", "--output", str(out)]
            if args.resume_saved_first_batch: command.append("--resume-saved-first-batch")
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=args.timeout_seconds, cwd=ROOT, check=False)
        returncode = process.returncode
        status = "completed" if returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        status, returncode = "timeout", 124
        event(out, "worker_watchdog_timeout", max_seconds=args.timeout_seconds)
    finally:
        elapsed = time.perf_counter() - started
        summary = read(out / "summary.json") if (out / "summary.json").exists() else {}
        metadata = {"output_dir": out.relative_to(ROOT).as_posix(), "attempt_ledger": (out / "ledger.jsonl").relative_to(ROOT).as_posix(),
                    "valid_count": summary.get("valid_count", 0), "valid_unique_count": summary.get("valid_unique_count", 0),
                    "emitted_attempt_records": summary.get("attempts", 0), "returncode": returncode}
        state = research_budget.finish_job(ticket, wall_seconds=elapsed, status=status, metadata=metadata)
        finish = {"status": status, "returncode": returncode, "job_wall_seconds": elapsed,
                  "canonical_generation_charged_attempts": state["generation"]["charged_attempts"],
                  "canonical_generation_remaining_attempts": state["generation"]["remaining_attempts"], **metadata}
        write(out / ("continuation_finish.json" if args.resume_saved_first_batch else "finish.json"), finish)
        event(out, "supervisor_finished", **finish)
    return returncode


if __name__ == "__main__": sys.exit(main())
