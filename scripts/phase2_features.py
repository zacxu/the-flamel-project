"""Extract and freeze shared initial-only descriptors; no labels or fitting."""

from __future__ import annotations

import os
for _thread_variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from pymatgen.core import Lattice, Structure
import research_features as features

OUT = ROOT / "artifacts" / "phase2" / "features"
ELIGIBLE = ROOT / "artifacts" / "phase1" / "data" / "eligible_population.csv"
DATA_MANIFEST = ROOT / "artifacts" / "phase1" / "data" / "dataset_manifest.json"
SOURCE = ROOT / "data" / "wbm" / "2022-10-19-wbm-init-structs.jsonl.gz"
EXPECTED_ROWS = 8294


def now():
    return datetime.now(timezone.utc).isoformat()


def log(message):
    line = f"{now()} {message}"
    print(line, flush=True)
    with (OUT / "audit.log").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def worker(item):
    mid, payload = item
    try:
        structure = Structure.from_dict(payload)
        vector, metadata = features.describe_structure_with_metadata(structure)
        return mid, vector, metadata, None
    except Exception as exception:
        return mid, None, None, {
            "material_id": mid, "exception": type(exception).__name__,
            "message": str(exception), "traceback": traceback.format_exc(),
        }


def invariance_checks(structures):
    records = []
    samples = list(structures.items())[:12]
    samples.extend([
        ("synthetic_single_site", Structure(Lattice.cubic(3.0), ["Mg"], [[0.1, 0.2, 0.3]])),
        ("synthetic_skew_cell", Structure([[3, 0, 0], [5.8, .6, 0], [.1, .2, 4]], ["Mg", "O"], [[0, 0, 0], [.4, .3, .2]])),
    ])
    for index, (mid, structure) in enumerate(samples):
        baseline = features.describe_structure(structure)
        fractional = structure.frac_coords.copy()
        shifts = np.random.default_rng(9000 + index).integers(-3, 4, size=fractional.shape)
        wrapped = Structure(structure.lattice, structure.species, fractional + shifts, to_unit_cell=False)
        perm = np.random.default_rng(19000 + index).permutation(len(structure))
        permuted = Structure(structure.lattice, [structure.species[j] for j in perm], fractional[perm])
        # Arbitrary labels, charge, stresses and energy-like site properties must
        # not be used by the public function, including on future candidates.
        decorated = structure.copy()
        decorated.add_site_property("e_above_hull_mp2020_corrected_ppd_mp", [999.0] * len(structure))
        decorated.add_site_property("relaxed_volume", [-1234.0] * len(structure))
        decorated.add_site_property("stress", [[1e9] * 6] * len(structure))
        direct, _ = features.describe_structure_with_metadata(structure)
        checks = {
            "pbc_wrapping": float(np.max(np.abs(baseline - features.describe_structure(wrapped)))),
            "site_permutation": float(np.max(np.abs(baseline - features.describe_structure(permuted)))),
            "target_stress_site_property_injection": float(np.max(np.abs(baseline - features.describe_structure(decorated)))),
            "shared_public_and_worker_function": float(np.max(np.abs(baseline - direct))),
        }
        passed = all(value <= 2e-5 for value in checks.values())
        records.append({"material_id": mid, "max_absolute_float32_differences": checks, "passed": passed})
    example = samples[0][1]
    with patch.object(features, "SpacegroupAnalyzer", side_effect=RuntimeError("intentional symmetry-fallback test")):
        fallback, diagnostic = features.describe_structure_with_metadata(example)
    fallback_index = features.FEATURE_NAMES.index("initial_symmetry_failed")
    sg_indices = [i for i, name in enumerate(features.FEATURE_NAMES) if name.startswith("initial_spacegroup_")]
    wyckoff_indices = [i for i, name in enumerate(features.FEATURE_NAMES) if name.startswith("initial_wyckoff_site_count_")]
    fallback_ok = bool(np.isfinite(fallback).all() and fallback[fallback_index] == 1 and not np.any(fallback[sg_indices]) and not np.any(fallback[wyckoff_indices]) and diagnostic["symmetry_failed"])
    invalid_recorded = False
    try:
        features.describe_structure(Structure(Lattice.cubic(3.0), [], []))
    except ValueError:
        invalid_recorded = True
    report = {
        "passed": all(item["passed"] for item in records) and fallback_ok and invalid_recorded,
        "samples": records, "explicit_symmetry_fallback_passed": fallback_ok,
        "invalid_structure_raises_explicit_error": invalid_recorded,
        "signature": str(inspect.signature(features.describe_structure)),
        "summary_or_target_arguments_accepted": False,
        "summary_files_read_by_extractor": False,
        "scope": "Integer coordinate wrapping and site-order invariance; lattice-basis/cell-size invariance is not claimed.",
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    log(f"extraction started workers={args.workers} dimension={features.FEATURE_DIMENSION}")
    source_manifest = json.loads(DATA_MANIFEST.read_text(encoding="utf-8"))
    if sha256(SOURCE) != source_manifest["files"]["initial_structures"]["sha256"]:
        raise ValueError("Pinned initial-structure SHA256 mismatch")
    if sha256(ELIGIBLE) != source_manifest["outputs"]["eligible_population.csv"]["sha256"]:
        raise ValueError("Phase 1 eligible index SHA256 mismatch")
    with ELIGIBLE.open(encoding="utf-8", newline="") as stream:
        eligibility = list(csv.DictReader(stream))
    ids = [row["material_id"] for row in eligibility]
    if len(ids) != EXPECTED_ROWS or len(set(ids)) != EXPECTED_ROWS:
        raise ValueError("Expected 8294 unique eligible IDs")
    desired = set(ids)
    structures = {}
    selected_payloads = {}
    # Selected initial records are copied verbatim, without adding any labels.
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream, gzip.open(OUT / "initial_structures.jsonl.gz", "wt", encoding="utf-8", newline="\n") as selected:
        scanned = 0
        for line in stream:
            scanned += 1
            record = json.loads(line)
            if record["material_id"] in desired:
                mid = record["material_id"]
                if mid in selected_payloads:
                    raise ValueError(f"Duplicate selected initial ID: {mid}")
                selected.write(json.dumps(record, separators=(",", ":")) + "\n")
                selected_payloads[mid] = record["initial_structure"]
    if set(selected_payloads) != desired:
        raise ValueError("Initial structures do not cover all eligible IDs")
    log(f"source streamed rows={scanned} selected={len(selected_payloads)}")
    X = np.full((len(ids), features.FEATURE_DIMENSION), np.nan, dtype=np.float32)
    metadata_rows = []
    errors = []
    positions = {mid: index for index, mid in enumerate(ids)}
    inputs = ((mid, selected_payloads[mid]) for mid in ids)
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for processed, (mid, vector, diagnostic, error) in enumerate(executor.map(worker, inputs, chunksize=16), start=1):
            if error:
                errors.append(error)
            else:
                X[positions[mid]] = vector
                original = eligibility[positions[mid]]
                metadata_rows.append({
                    "material_id": mid, "formula": diagnostic["formula"],
                    "reduced_formula": diagnostic["reduced_formula"],
                    "chemical_system": diagnostic["chemical_system"], "n_sites": diagnostic["n_sites"],
                    "reserved_mg_o_control": original["reserved_mg_o_control"],
                    "initial_spacegroup": diagnostic["initial_spacegroup"],
                    "symmetry_failed": diagnostic["symmetry_failed"],
                    "symmetry_error": diagnostic["symmetry_error"] or "",
                    "inequivalent_site_count": diagnostic["inequivalent_site_count"],
                    **{f"missing_{name}_atom_fraction": fraction for name, fraction in diagnostic["missing_elemental_atom_fractions"].items()},
                })
            if processed % 1000 == 0:
                log(f"described={processed}/{len(ids)} structural_errors={len(errors)}")
    json_write(OUT / "structural_errors.json", {"count": len(errors), "errors": errors})
    if errors or not np.isfinite(X).all():
        raise ValueError(f"Feature coverage incomplete: {len(errors)} explicit structural errors; no successful feature archive emitted")
    for mid in ids[:12]:
        structures[mid] = Structure.from_dict(selected_payloads[mid])
    validation = invariance_checks(structures)
    json_write(OUT / "validation_report.json", validation)
    if not validation["passed"]:
        raise ValueError("Descriptor invariance/lineage validation failed")
    np.savez_compressed(OUT / "features.npz", X=X, material_ids=np.asarray(ids), feature_names=np.asarray(features.FEATURE_NAMES))
    with (OUT / "row_metadata.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metadata_rows[0]))
        writer.writeheader()
        writer.writerows(metadata_rows)
    schema = {
        "schema_version": features.SCHEMA_VERSION, "dimension": features.FEATURE_DIMENSION,
        "features": [{"index": i, "name": name, "unit": unit} for i, (name, unit) in enumerate(zip(features.FEATURE_NAMES, features.FEATURE_UNITS, strict=True))],
        "input_allowlist": ["initial_structure.lattice.matrix", "initial_structure.sites[].species (element identities)", "initial_structure.sites[].abc (fractional positions)"],
        "transforms": {
            "elemental_fraction": "Atomic count divided by number of atoms; fixed Z=1..118 columns",
            "elemental_properties": "pymatgen Element.Z, atomic_mass, X and atomic_radius; weighted population mean/std and constituent min/max",
            "missing_elemental_properties": "Nonfinite/None values replaced by constant 0.0; atomic fraction missing recorded separately for each property; no fitted imputation",
            "geometry": "Initial volume per atom, original initial-cell length ratios and angles, minimum periodic distances and per-site nearest-neighbor statistics including nonzero periodic self images",
            "symmetry": "Recomputed from cleaned initial coordinates by SpacegroupAnalyzer(symprec=0.01 angstrom, angle_tolerance=5 degrees); 230 one-hot groups, symmetry-failed flag, inequivalent count, 26 per-input-site Wyckoff counts",
            "symmetry_failure": "SG/Wyckoff/inequivalent-count features set to zero; failure flag=1; row retained; error text kept in row metadata",
            "site_properties": "Ignored and stripped, including stress, energies, labels and arbitrary metadata",
        },
        "forbidden_sources": ["released WBM energies and hull distances", "bandgap_pbe", "relaxed volume or coordinates", "relaxed symmetry/prototype labels", "initial-to-final changes", "unique_prototype or eligibility flags", "material_id/substitution step", "calibration/pool labels", "CHGNet/QE outputs"],
        "fitted_state": None,
    }
    json_write(OUT / "feature_schema.json", schema)
    module = ROOT / "research_features.py"
    manifest = {
        "status": "passed", "completed_at_utc": now(), "elapsed_seconds": time.perf_counter() - start,
        "rows": len(ids), "columns": features.FEATURE_DIMENSION, "dtype": "float32", "all_values_finite": True,
        "selected_initial_records": len(selected_payloads), "scanned_initial_records": scanned,
        "structural_failures": len(errors), "symmetry_fallback_rows": sum(row["symmetry_failed"] for row in metadata_rows),
        "worker_count": args.workers, "threads_per_worker": 1,
        "row_order": "Phase 1 eligible_population.csv order; NPZ material_ids, metadata rows and X align",
        "copied_initial_file_order": "Source WBM initial-structure order; join by material_id, not row number",
        "oracle_labels_in_features_archive": False, "summary_csv_read": False,
        "input_sources": {"initial_structures": {"path": str(SOURCE.relative_to(ROOT)), "sha256": sha256(SOURCE)}, "eligible_population": {"path": str(ELIGIBLE.relative_to(ROOT)), "sha256": sha256(ELIGIBLE)}, "phase1_manifest": {"path": str(DATA_MANIFEST.relative_to(ROOT)), "sha256": sha256(DATA_MANIFEST)}},
        "implementation": {"module": "research_features.py", "module_sha256": sha256(module), "public_entrypoint": "research_features.describe_structure(structure)", "public_function_source_sha256": hashlib.sha256(inspect.getsource(features.describe_structure).encode()).hexdigest(), "extraction_script_sha256": sha256(Path(__file__))},
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pymatgen", "spglib")},
        "outputs": {},
    }
    for filename in ("features.npz", "row_metadata.csv", "initial_structures.jsonl.gz", "feature_schema.json", "validation_report.json", "structural_errors.json"):
        path = OUT / filename
        manifest["outputs"][filename] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "size_bytes": path.stat().st_size}
    json_write(OUT / "feature_manifest.json", manifest)
    log(f"PASSED rows={len(ids)} columns={X.shape[1]} symmetry_fallbacks={manifest['symmetry_fallback_rows']} elapsed={time.perf_counter()-start:.3f}s")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exception:
        OUT.mkdir(parents=True, exist_ok=True)
        json_write(OUT / "fatal_error.json", {"status": "failed", "at_utc": now(), "exception": type(exception).__name__, "message": str(exception), "traceback": traceback.format_exc()})
        log(f"FAILED {type(exception).__name__}: {exception}")
        raise
