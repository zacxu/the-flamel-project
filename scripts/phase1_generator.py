"""Audited, eight-attempt CrystalFormer Phase 1 CPU pilot.

Uses the pinned upstream inference API without modifying vendor source or training.
All raw draws, including invalid/mismatched structures, remain in the ledger.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase1/generator"
VENDOR = ROOT / "vendor/CrystalFormer"
CHECKPOINT = ROOT / "checkpoints/epoch_044000.pkl"
EXPECTED_SHA = "847e8f3962226d0539722c851bd615479d9c7fc2d5be9112898c1cdd2b7b700a"
CONFIG = {
    "source_revision": "31bb734a3fd006af49a021921839061e6184cbf1",
    "checkpoint_revision": "b203f4273158d95b49b60a13433bf1dcc4ccf5d9",
    "checkpoint_path": "alex20s/multi/epoch_044000.pkl",
    "checkpoint_sha256": EXPECTED_SHA,
    "formula": "Mg4O4", "conditioning_formula": "MgO",
    "conditioning_reason": "Training reduces composition counts by their GCD; exact expanded cell counts are validated separately.",
    "exact_counts": {"Mg": 4, "O": 4},
    "spacegroup": 225, "seed": 20261022, "initialization_seed": 42,
    "attempt_limit": 8, "batch_size": 4, "temperature": 1.0, "top_p": 1.0,
    "symprec_angstrom": 0.01, "angle_tolerance_degrees": 5.0,
    "minimum_distance_angstrom": 0.75, "expanded_atom_cap": 20,
    "deduplication": {"ltol": 0.05, "stol": 0.1, "angle_tol": 5.0,
                       "primitive_cell": True, "scale": True,
                       "attempt_supercell": False},
    "architecture": {"Nf": 5, "Kx": 16, "Kl": 4, "n_max": 21,
                     "h0_size": 256, "num_layers": 16, "num_heads": 8,
                     "key_size": 32, "model_size": 256, "embed_size": 256,
                     "atom_types": 119, "wyck_types": 28,
                     "dropout_rate": 0.1, "attn_dropout": 0.1},
}
os.environ.setdefault("JAX_PLATFORMS", "cpu")
for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(variable, "4")
os.environ.setdefault("JAX_COMPILATION_CACHE_DIR", str(OUT / "jax_cache"))
sys.path.insert(0, str(VENDOR))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def event(kind, **fields):
    row = {"utc": utc_now(), "event": kind, **fields}
    with (OUT / "ledger.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, allow_nan=False) + "\n")
    print(json.dumps(row), flush=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def set_cpu_affinity():
    if os.name != "nt":
        return {"requested_logical_cpus": 4, "applied": False}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    applied = bool(kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 0xF))
    return {"requested_logical_cpus": 4, "windows_affinity_mask": "0xF",
            "applied": applied, "error": None if applied else ctypes.get_last_error()}


def main():
    run_start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cifs").mkdir(exist_ok=True)
    ledger_path = OUT / "ledger.jsonl"
    history = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()] if ledger_path.exists() else []
    started = [row for row in history if row["event"] == "attempt_started"]
    if started:
        raise RuntimeError("This pilot already reserved sample attempts; inspect ledger before any authorized continuation.")
    config_path = OUT / "config.json"
    if config_path.exists() and json.loads(config_path.read_text(encoding="utf-8")) != CONFIG:
        raise RuntimeError("Existing pilot configuration differs.")
    dump(config_path, CONFIG)
    event("run_started", python=sys.version, executable=sys.executable,
          platform=platform.platform(), cpu_affinity=set_cpu_affinity())
    checkpoint_sha = sha256_file(CHECKPOINT)
    if checkpoint_sha != EXPECTED_SHA:
        raise RuntimeError("Checkpoint hash mismatch; no model execution permitted.")
    event("checkpoint_verified", bytes=CHECKPOINT.stat().st_size, sha256=checkpoint_sha)

    import numpy as np
    import jax
    import jax.numpy as jnp
    from pymatgen.core import Lattice, Structure
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from crystalformer.src.transformer import make_transformer
    from crystalformer.src.sample import make_sample_crystal
    from crystalformer.src.formula import formula_string_to_composition_vector
    from crystalformer.src.checkpoint import load_data
    from crystalformer.src.wyckoff import mult_table, symops, wmax_table
    event("imports_completed", seconds=time.perf_counter() - run_start,
          backend=jax.default_backend(), devices=[str(device) for device in jax.devices()])
    if jax.default_backend() != "cpu":
        raise RuntimeError("The frozen pilot requires the CPU backend.")
    init_start = time.perf_counter()
    initial_params, transformer = make_transformer(jax.random.PRNGKey(42), **CONFIG["architecture"])
    ckpt = load_data(str(CHECKPOINT))
    if not isinstance(ckpt, dict) or "params" not in ckpt:
        raise RuntimeError("Checkpoint has no parameter tree.")
    params = ckpt["params"]
    initial_leaves, initial_tree = jax.tree_util.tree_flatten(initial_params)
    loaded_leaves, loaded_tree = jax.tree_util.tree_flatten(params)
    if initial_tree != loaded_tree or [p.shape for p in initial_leaves] != [p.shape for p in loaded_leaves]:
        raise RuntimeError("Checkpoint parameter tree does not match the pinned architecture.")
    count = sum(int(p.size) for p in loaded_leaves)
    differs = any(not np.array_equal(np.asarray(a), np.asarray(b)) for a, b in zip(initial_leaves, loaded_leaves))
    if not differs:
        raise RuntimeError("Loaded weights unexpectedly equal random initialization.")
    event("checkpoint_loaded", checkpoint=str(CHECKPOINT), parameter_count=count,
          parameter_leaves=len(loaded_leaves), differs_from_random_initialization=differs,
          initialization_and_load_seconds=time.perf_counter() - init_start)
    del ckpt, initial_params, initial_leaves
    composition = formula_string_to_composition_vector(CONFIG["conditioning_formula"])
    sample = make_sample_crystal(
        transformer, n_max=21, atom_types=119, wyck_types=28, Kx=16, Kl=4,
        w_mask=None, top_p=1.0, temperature=1.0, K=0, g=225,
        atom_mask=jnp.ones(119, dtype=int))
    # Training reduces stoichiometry, while the upstream formula parser does not.
    # Condition on the reduced formula; validate exact expanded counts separately.
    event("sampling_ready", conditioning_vector=np.asarray(composition).tolist())
    base_key = jax.random.PRNGKey(CONFIG["seed"])
    matrices = np.asarray(symops)
    multiplicities = np.asarray(mult_table)
    wmax = np.asarray(wmax_table)
    matcher = StructureMatcher(**CONFIG["deduplication"])
    unique_valid = []
    results = []
    batch_times = []

    def expand(g, lattice, species, wyckoff, coords):
        species_expanded, positions_expanded = [], []
        lattice_obj = Lattice.from_parameters(*[float(v) for v in lattice])
        for atomic_number, position_id, point in zip(species, wyckoff, coords):
            if int(atomic_number) == 0:
                continue
            if int(position_id) <= 0:
                raise ValueError("Non-padding atom has padding Wyckoff position.")
            general_m = int(multiplicities[g - 1, int(wmax[g - 1])])
            equivalents = matrices[g - 1, int(wmax[g - 1]), :general_m] @ np.r_[point, 1.0]
            equivalents %= 1.0
            op0 = matrices[g - 1, int(position_id), 0]
            differences = equivalents @ op0[:, :3].T + op0[:, 3] - equivalents
            differences -= np.rint(differences)
            generator = equivalents[np.argmin(np.sum(differences**2, axis=1))]
            m = int(multiplicities[g - 1, int(position_id)])
            orbit = matrices[g - 1, int(position_id), :m] @ np.r_[generator, 1.0]
            orbit %= 1.0
            species_expanded.extend([int(atomic_number)] * m)
            positions_expanded.extend(orbit.tolist())
        return Structure(lattice_obj, species_expanded, positions_expanded)

    for batch_index in range(2):
        identifiers = list(range(4 * batch_index, 4 * batch_index + 4))
        for attempt_id in identifiers:
            event("attempt_started", attempt_id=attempt_id, batch_index=batch_index,
                  formula=CONFIG["formula"], requested_spacegroup=225)
        started_at = time.perf_counter()
        try:
            generated = sample(jax.random.fold_in(base_key, batch_index), params, 4, composition)
            arrays = jax.tree_util.tree_map(lambda value: np.asarray(value.block_until_ready()), generated)
        except Exception:
            failure = traceback.format_exc()
            for attempt_id in identifiers:
                event("attempt_failed", attempt_id=attempt_id, stage="sampling", error=failure)
            raise
        elapsed = time.perf_counter() - started_at
        batch_times.append(elapsed)
        G, XYZ, A, W, M, L = arrays
        np.savez_compressed(OUT / f"raw_batch_{batch_index:02d}.npz",
                            G=G, XYZ=XYZ, A=A, W=W, M=M, L=L)
        event("batch_sampled", batch_index=batch_index, attempts=4, seconds=elapsed,
              timing_kind="first_call_including_compilation" if batch_index == 0 else "same_shape_second_call")
        for local, attempt_id in enumerate(identifiers):
            raw = {"G": int(G[local]), "XYZ": XYZ[local].tolist(), "A": A[local].tolist(),
                   "W": W[local].tolist(), "M": M[local].tolist(), "L": L[local].tolist()}
            # Preserve nonfinite raw values as explicit strings if necessary.
            raw_path = OUT / f"raw_attempt_{attempt_id:03d}.json"
            raw_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
            row = {"attempt_id": attempt_id, "batch_index": batch_index,
                   "valid": False, "rejection_reasons": [], "raw_path": str(raw_path.relative_to(ROOT))}
            try:
                if not all(np.isfinite(array[local]).all() for array in (XYZ, L)):
                    raise ValueError("Nonfinite coordinates or lattice parameters.")
                structure = expand(int(G[local]), L[local], A[local], W[local], XYZ[local])
                cif_path = OUT / "cifs" / f"attempt_{attempt_id:03d}.cif"
                structure.to(filename=str(cif_path), fmt="cif")
                structure_path = OUT / f"structure_{attempt_id:03d}.json"
                dump(structure_path, structure.as_dict())
                counts = {symbol: int(value) for symbol, value in structure.composition.get_el_amt_dict().items()}
                distance = structure.distance_matrix.copy()
                np.fill_diagonal(distance, np.inf)
                minimum_distance = float(distance.min()) if len(structure) > 1 else None
                measured = SpacegroupAnalyzer(structure, symprec=0.01, angle_tolerance=5.0)
                row.update(cif=str(cif_path.relative_to(ROOT)), structure_json=str(structure_path.relative_to(ROOT)),
                           counts=counts, n_atoms=len(structure), volume_angstrom3=float(structure.volume),
                           minimum_distance_angstrom=minimum_distance,
                           measured_spacegroup=int(measured.get_space_group_number()),
                           measured_spacegroup_symbol=measured.get_space_group_symbol())
                if counts != CONFIG["exact_counts"]:
                    row["rejection_reasons"].append("exact_composition_mismatch")
                if len(structure) != 8 or len(structure) > 20:
                    row["rejection_reasons"].append("expanded_atom_count_mismatch")
                if structure.volume <= 0:
                    row["rejection_reasons"].append("nonpositive_volume")
                if minimum_distance is not None and minimum_distance < 0.75:
                    row["rejection_reasons"].append("minimum_distance_below_threshold")
                row["valid"] = not row["rejection_reasons"]
                if row["valid"]:
                    duplicate = next((other_id for other_id, other in unique_valid if matcher.fit(structure, other)), None)
                    row["duplicate_of"] = duplicate
                    if duplicate is None:
                        unique_valid.append((attempt_id, structure))
            except Exception as exc:
                row["rejection_reasons"].append(f"conversion_or_validation_error:{type(exc).__name__}:{exc}")
            results.append(row)
            event("attempt_completed", **row)

    summary = {"completed_utc": utc_now(), "attempts": len(results),
               "valid_exact_count_structures": sum(row["valid"] for row in results),
               "unique_valid_structures": len(unique_valid),
               "batch_seconds": batch_times,
               "second_batch_seconds_per_attempt": batch_times[1] / 4,
               "run_seconds": time.perf_counter() - run_start,
               "results": results,
               "limits": ["Known MgO control; no novelty or stability evidence.",
                          "No formula-change compilation timing measured.",
                          "Deduplicated representatives are for later seeded selection, not automatic relaxation."]}
    dump(OUT / "summary.json", summary)
    event("run_completed", attempts=len(results), valid=summary["valid_exact_count_structures"],
          unique_valid=len(unique_valid), seconds=summary["run_seconds"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if OUT.exists():
            event("run_failed", error=traceback.format_exc())
        raise
