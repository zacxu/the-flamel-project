"""Execute and audit only the frozen primary Phase 4 CrystalFormer cohorts.

No model ranking, relaxation, QE, retries, supplementary sampling, or protocol
changes occur here. The existing budgeted sampler owns pre-dispatch reservations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase4/generation"
SAMPLER = ROOT / "scripts/phase3_generate.py"
sys.path.insert(0, str(ROOT))


def utc(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rel(path): return path.relative_to(ROOT).as_posix()


def fingerprint(directory):
    names = ["config.json", "summary.json", "ledger.jsonl", "raw_batch_00.npz", "raw_batch_01.npz"]
    names += [f"raw_attempt_{i:03d}.json" for i in range(8)]
    names += [f"structure_{i:03d}.json" for i in range(8)]
    names += [f"cifs/attempt_{i:03d}.cif" for i in range(8)]
    return [{"path": rel(directory / name), "sha256": sha(directory / name)}
            for name in names if (directory / name).is_file()]


def freeze():
    if (OUT / "run_plan.json").exists():
        raise RuntimeError("Primary run plan already frozen; use run/audit without replacement")
    controls_path = ROOT / "artifacts/phase2/controls/matched_protocol.json"
    formulas_path = ROOT / "artifacts/phase2/compositions/generation_protocol.json"
    controls, generation = read(controls_path), read(formulas_path)
    cohorts = []
    for label, arm in [("mgo_rocksalt", "p1"), ("tio2_rutile", "nontrivial"), ("tio2_rutile", "p1")]:
        control = next(row for row in controls["controls"] if row["label"] == label)
        cohorts.append({"kind": "control", "control": label, "arm": arm,
            "formula": control["evaluated_formula"], "sampling_seed": controls["seed"],
            "spacegroup": 1 if arm == "p1" else control["nontrivial_spacegroup"],
            "exact_counts": control["exact_element_counts"], "attempts": 8,
            "run_id": f"phase4_{label}_{arm}"})
    for formula in generation["formulas"]:
        if formula["cohort"] != "default" or formula["formula"] == "CaMg2O3": continue
        cohorts.append({"kind": "new_composition", "formula": formula["formula"],
            "sampling_seed": formula["sampling_seed"], "spacegroup": formula["spacegroup"],
            "exact_counts": formula["exact_expanded_counts"], "attempts": 8,
            "run_id": f"phase4_new_{formula['formula']}"})
    assert len(cohorts) == 8 and sum(row["attempts"] for row in cohorts) == 64
    for cohort in cohorts:
        cohort["output_dir"] = rel(OUT / cohort["run_id"])
        cohort["candidate_ids"] = [f"{cohort['run_id']}_attempt_{i:03d}" for i in range(8)]
    plan = {"status": "frozen_before_new_model_draws", "frozen_at_utc": utc(),
        "phase": 4, "new_actual_draws_planned": 64, "primary_attempts_per_cohort": 8,
        "new_cohorts": cohorts, "reused_cohorts": [
            {"run_id": "phase1_mgo_nontrivial", "kind": "control", "control": "mgo_rocksalt",
             "arm": "nontrivial", "formula": "Mg4O4", "spacegroup": 225,
             "sampling_seed": 20261022, "exact_counts": {"Mg": 4, "O": 4},
             "output_dir": "artifacts/phase1/generator", "attempts": 8,
             "files": fingerprint(ROOT / "artifacts/phase1/generator")},
            {"run_id": "phase3_early_CaMg2O3", "kind": "new_composition",
             "formula": "CaMg2O3", "spacegroup": 2, "sampling_seed": 20262024,
             "exact_counts": {"Ca": 1, "Mg": 2, "O": 3},
             "output_dir": "artifacts/phase3/generation/early_CaMg2O3", "attempts": 8,
             "files": fingerprint(ROOT / "artifacts/phase3/generation/early_CaMg2O3")}],
        "source_protocols": [{"path": rel(path), "sha256": sha(path)} for path in (controls_path, formulas_path)],
        "sampler_source": {"path": rel(SAMPLER), "sha256": sha(SAMPLER),
                           "snapshot": rel(OUT / "executed_primary_sampler.py")},
        "orchestrator_source_sha256": sha(Path(__file__)),
        "checkpoint_sha256": generation["checkpoint_sha256"],
        "source_revision": generation["source_revision"], "temperature": 1.0, "top_p": 1.0,
        "primary_denominators": {"controls": 32, "new_compositions": 48, "total": 80},
        "supplementary_sampling": "Not authorized by this primary run plan",
        "attempt_policy": "No invalid-draw replacement; original cohorts/keys and exact expanded cells remain fixed.",
        "timing_policy": "Each independent cohort's first batch includes group-specific compilation; second same-shape batch is warm. MgO SG225 timings are reused from Phase 1, so conditions and start times differ.",
        "resource_policy": {"generator_logical_cpu_affinity_mask": "0xF", "batch_size": 4,
                            "cohorts_concurrent": 1, "cohort_watchdog_seconds": 600}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "executed_primary_sampler.py").write_bytes(SAMPLER.read_bytes())
    (OUT / "executed_primary_orchestrator.py").write_bytes(Path(__file__).read_bytes())
    write(OUT / "run_plan.json", plan)
    print(json.dumps({"frozen": True, "plan_sha256": sha(OUT / "run_plan.json"), "draws": 64}), flush=True)


def verify_plan(plan):
    for item in plan["source_protocols"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item
    assert sha(SAMPLER) == plan["sampler_source"]["sha256"]
    assert sha(ROOT / plan["sampler_source"]["snapshot"]) == plan["sampler_source"]["sha256"]
    assert sha(OUT / "executed_primary_orchestrator.py") == plan["orchestrator_source_sha256"]
    for cohort in plan["reused_cohorts"]:
        for item in cohort["files"]: assert sha(ROOT / item["path"]) == item["sha256"], item


def run():
    plan = read(OUT / "run_plan.json")
    verify_plan(plan)
    if (OUT / "dispatch_started.json").exists():
        raise RuntimeError("This primary run was already dispatched; inspect completed artifacts. No repeated dispatch.")
    write(OUT / "dispatch_started.json", {"started_at_utc": utc(), "pid": os.getpid(),
        "run_plan_sha256": sha(OUT / "run_plan.json"), "sampler_source_sha256": sha(SAMPLER)})
    results = []
    for case in plan["new_cohorts"]:
        verify_plan(plan)
        command = [str(ROOT / ".envs/generator/Scripts/python.exe"), "-u", str(SAMPLER),
            "--phase", "4", "--run-id", case["run_id"], "--output", case["output_dir"],
            "--timeout-seconds", "600"]
        command += (["--control", case["control"], "--arm", case["arm"]]
                    if case["kind"] == "control" else ["--formula", case["formula"]])
        write(OUT / f"dispatch_{case['run_id']}.json", {"utc": utc(), "command": command,
            "run_plan_sha256": sha(OUT / "run_plan.json"), "candidate_ids": case["candidate_ids"]})
        with (OUT / f"supervisor_{case['run_id']}.log").open("wb") as stream:
            proc = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False)
        directory = ROOT / case["output_dir"]
        summary = read(directory / "summary.json") if (directory / "summary.json").exists() else {}
        result = {"run_id": case["run_id"], "returncode": proc.returncode,
            "completed_at_utc": utc(), "actual_attempts": summary.get("attempts", 0),
            "valid_count": summary.get("valid_count", 0), "valid_unique_count": summary.get("valid_unique_count", 0)}
        results.append(result)
        write(OUT / "progress.json", {"cohorts": results, "primary_plan_unchanged": True})
        print(json.dumps(result), flush=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Cohort failed: {case['run_id']}; no automatic retry or replacement")
    write(OUT / "sampling_complete.json", {"completed_at_utc": utc(), "cohorts": results,
        "actual_new_draws": sum(row["actual_attempts"] for row in results),
        "run_plan_sha256": sha(OUT / "run_plan.json")})


def audit():
    plan = read(OUT / "run_plan.json"); verify_plan(plan)
    (OUT / "audited_primary_orchestrator.py").write_bytes(Path(__file__).read_bytes())
    os.environ["JAX_PLATFORMS"] = "cpu"
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"): os.environ[key] = "4"
    import ctypes
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        assert kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 0xF)
    import numpy as np
    from pymatgen.core import Structure, Lattice, Composition
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.io.cif import CifParser
    from scipy.optimize import linear_sum_assignment
    sys.path.insert(0, str(ROOT / "vendor/CrystalFormer"))
    from crystalformer.src.wyckoff import symops, mult_table, wmax_table
    matrices, multiplicity, max_w = np.asarray(symops), np.asarray(mult_table), np.asarray(wmax_table)
    protocol = read(ROOT / "artifacts/phase2/compositions/generation_protocol.json")
    matcher = StructureMatcher(**protocol["deduplication"])
    roundtrip = StructureMatcher(ltol=1e-4, stol=1e-4, angle_tol=1e-3,
                                primitive_cell=False, scale=False, attempt_supercell=False)
    checks = 0
    def check(value, message):
        nonlocal checks
        checks += 1
        if not value: raise AssertionError(message)
    def expand(raw):
        atoms, coords = [], []; g = int(raw["G"])
        for z, w, point in zip(raw["A"], raw["W"], raw["XYZ"]):
            z, w = int(z), int(w)
            if z == 0: continue
            general = int(max_w[g-1]); number = int(multiplicity[g-1, general])
            orbit = (matrices[g-1, general, :number] @ np.r_[point, 1.0]) % 1.0
            op = matrices[g-1, w, 0]
            differences = orbit @ op[:, :3].T + op[:, 3] - orbit
            differences -= np.rint(differences)
            generator = orbit[np.argmin((differences**2).sum(axis=1))]
            number = int(multiplicity[g-1, w])
            positions = (matrices[g-1, w, :number] @ np.r_[generator, 1.0]) % 1.0
            atoms.extend([z] * number); coords.extend(positions.tolist())
        return Structure(Lattice.from_parameters(*map(float, raw["L"])), atoms, coords)
    def minimum_distance(structure):
        distance = structure.distance_matrix.copy(); np.fill_diagonal(distance, np.inf)
        pairs = float(distance.min()) if len(structure) > 1 else float("inf")
        reduced = structure.lattice.get_lll_reduced_lattice()
        images = reduced.get_points_in_sphere([[0., 0., 0.]], [0., 0., 0.], min(reduced.abc) + 1e-7)
        self_distance = min(float(item[1]) for item in images if float(item[1]) > 1e-8)
        return min(pairs, self_distance)
    cohorts = []
    for case in plan["reused_cohorts"] + plan["new_cohorts"]:
        directory = ROOT / case["output_dir"]; summary = read(directory / "summary.json")
        config = read(directory / "config.json"); prior = case["run_id"] == "phase1_mgo_nontrivial"
        cfg = config if prior else config["case"]
        check(cfg["seed" if prior else "sampling_seed"] == case["sampling_seed"], "sampling seed changed")
        check(cfg["spacegroup"] == case["spacegroup"], "spacegroup changed")
        check(config["temperature"] == 1.0 and config["top_p"] == 1.0, "sampling settings changed")
        check(config["checkpoint_sha256"] == plan["checkpoint_sha256"], "checkpoint changed")
        check(config["source_revision"] == plan["source_revision"], "vendor revision changed")
        check(len(summary["results"]) == 8, "cohort must retain all eight primary attempts")
        if not prior:
            expected_protocol = next(item for item in plan["source_protocols"]
                                     if ("controls" in item["path"]) == (case["kind"] == "control"))
            check(config["source_protocol_sha256"] == expected_protocol["sha256"], "protocol not frozen")
        if case in plan["new_cohorts"]:
            check(read(directory / "reservation.json")["attempts"] == 8, "reservation not eight")
            check(read(directory / "finish.json")["status"] == "completed", "new cohort unfinished")
            check(read(directory / "verification.json")["script_sha256"] == plan["sampler_source"]["sha256"], "sampler script changed")
            ledger = [json.loads(line) for line in (directory / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
            check([item["attempt_id"] for item in ledger if item["event"] == "attempt_started"] == list(range(8)), "attempt repeat/drop")
            check([item["attempt_id"] for item in ledger if item["event"] == "attempt_completed"] == list(range(8)), "result repeat/drop")
        batches = [np.load(directory / f"raw_batch_{b:02d}.npz") for b in (0, 1)]
        representatives, rows = [], []
        for item in summary["results"]:
            index = item["attempt_id"]; candidate_id = item.get("candidate_id", f"phase1_mgo_attempt_{index:03d}")
            raw_path = ROOT / item.get("raw_json", item.get("raw_path"))
            raw = read(raw_path); batch = batches[index // 4]
            for name in ("G", "XYZ", "A", "W", "M", "L"):
                check(np.array_equal(np.asarray(raw[name]), batch[name][index % 4]), f"raw JSON differs from NPZ {candidate_id}/{name}")
            check(int(raw["G"]) == case["spacegroup"], "requested generated group mismatch")
            structure = Structure.from_dict(read(ROOT / item["structure_json"]))
            rebuilt = expand(raw)
            check(np.array_equal(rebuilt.atomic_numbers, structure.atomic_numbers), "raw expanded species mismatch")
            check(np.allclose(rebuilt.lattice.matrix, structure.lattice.matrix, atol=1e-9), "raw expanded lattice mismatch")
            check(np.allclose(rebuilt.frac_coords, structure.frac_coords, atol=1e-9), "raw expanded coordinates mismatch")
            # Preserve sampled coordinates: the parser's default idealization
            # rounds near-special fractions and is not a file roundtrip test.
            cif = CifParser(ROOT / item["cif"], frac_tolerance=0).parse_structures(primitive=False)[0]
            check(roundtrip.fit(structure, cif), f"CIF roundtrip failed: {candidate_id}")
            check(np.allclose(structure.lattice.matrix, cif.lattice.matrix, atol=1e-6, rtol=0), "CIF lattice differs")
            check(structure.composition == cif.composition and len(structure) == len(cif), "CIF species/count differs")
            for atomic_number in sorted(set(structure.atomic_numbers)):
                original_indices = [i for i,z in enumerate(structure.atomic_numbers) if z == atomic_number]
                cif_indices = [i for i,z in enumerate(cif.atomic_numbers) if z == atomic_number]
                distances = structure.lattice.get_all_distances(structure.frac_coords[original_indices], cif.frac_coords[cif_indices])
                ri, ci = linear_sum_assignment(distances)
                check(bool((distances[ri, ci] <= 1e-5).all()), "CIF periodic Cartesian coordinate differs")
            counts = {symbol: int(amount) for symbol, amount in structure.composition.get_el_amt_dict().items()}
            check(counts == item["counts"] and len(structure) == item["n_atoms"], "counts mismatch")
            minimum = minimum_distance(structure)
            exact = counts == case["exact_counts"] and len(structure) == sum(case["exact_counts"].values())
            geometry_valid = minimum >= .75 and math.isfinite(structure.volume) and structure.volume > 0
            valid = exact and len(structure) <= 20 and geometry_valid
            check(valid == item["valid"], "frozen primary validity mismatch")
            measured = SpacegroupAnalyzer(structure, symprec=.01, angle_tolerance=5.0).get_space_group_number()
            check(measured == item["measured_spacegroup"], "measured group mismatch")
            duplicate = next((other_id for other_id, other in representatives if matcher.fit(structure, other)), None) if valid else None
            if valid and duplicate is None: representatives.append((candidate_id, structure))
            saved_duplicate = item.get("duplicate_of")
            if isinstance(saved_duplicate, int): saved_duplicate = f"phase1_mgo_attempt_{saved_duplicate:03d}"
            if valid: check(duplicate == saved_duplicate, "deduplication mismatch")
            rows.append({**item, "candidate_id": candidate_id, "structure_sha256": sha(ROOT / item["structure_json"]),
                "raw_sha256": sha(raw_path), "cif_sha256": sha(ROOT / item["cif"]),
                "audited_valid": valid, "audited_duplicate_of": duplicate,
                "exact_expanded_counts_match": exact, "minimum_periodic_distance_angstrom": minimum,
                "same_reduced_formula_diagnostic_only": structure.composition.reduced_composition == Composition(case["exact_counts"]).reduced_composition,
                "geometry_valid_diagnostic_only": geometry_valid,
                "reduced_formula_geometry_valid_within_atom_cap_diagnostic_only": (
                    structure.composition.reduced_composition == Composition(case["exact_counts"]).reduced_composition
                    and geometry_valid and len(structure) <= 20),
                "cif_roundtrip": True, "raw_expansion_verified": True})
        for batch in batches: batch.close()
        valid_count = sum(item["audited_valid"] for item in rows)
        check(valid_count == summary["valid_exact_count_structures" if prior else "valid_count"], "valid total mismatch")
        check(len(representatives) == summary["unique_valid_structures" if prior else "valid_unique_count"], "unique total mismatch")
        timings = summary.get("batch_timings", [{"batch_index": i, "seconds": t,
            "kind": "first_call_including_compilation" if i == 0 else "same_shape_warm_call"}
            for i, t in enumerate(summary.get("batch_seconds", []))])
        wall_seconds = summary["run_seconds"] if prior else read(directory / "finish.json")["job_wall_seconds"]
        if (directory / "continuation_finish.json").exists():
            wall_seconds += read(directory / "continuation_finish.json")["job_wall_seconds"]
        cohorts.append({"run_id": case["run_id"], "kind": case["kind"], "formula": case["formula"],
            "control": case.get("control"), "arm": case.get("arm"), "spacegroup": case["spacegroup"],
            "sampling_seed": case["sampling_seed"], "reused": case in plan["reused_cohorts"],
            "summary_path": rel(directory / "summary.json"), "summary_sha256": sha(directory / "summary.json"),
            "attempts": 8, "valid_count": valid_count, "valid_unique_count": len(representatives),
            "valid_requested_symmetry_count": sum(item["audited_valid"] and item["measured_spacegroup"] == case["spacegroup"] for item in rows),
            "reduced_formula_matches_diagnostic_only": sum(item["same_reduced_formula_diagnostic_only"] for item in rows),
            "reduced_formula_geometry_valid_within_atom_cap_diagnostic_only": sum(item["reduced_formula_geometry_valid_within_atom_cap_diagnostic_only"] for item in rows),
            "recorded_run_wall_seconds": wall_seconds,
            "walltime_definition": "Phase 1 recorded run including initialization, or supervisor full worker walltime; includes both failed and continuation workers for Phase 3 CaMg2O3. Timing comparisons are descriptive because cohorts ran at different times.",
            "batch_timings": timings, "results": rows,
            "valid_unique_representatives": [item for item in rows if item["audited_valid"] and item["audited_duplicate_of"] is None]})
    controls = [case for case in cohorts if case["kind"] == "control"]
    formulas = [case for case in cohorts if case["kind"] == "new_composition"]
    assert len(controls) == 4 and len(formulas) == 6
    write(OUT / "summary.json", {"status": "completed", "audited_at_utc": utc(),
        "run_plan_sha256": sha(OUT / "run_plan.json"), "new_draws_phase4": 64,
        "new_charged_attempts_phase4": 64,
        "reused_actual_draws": 16, "all_primary_actual_draws": 80,
        "control_primary_attempts": 32, "new_composition_primary_attempts": 48,
        "new_formulas_attempted": 6, "new_formulas_with_exact_valid_structure": sum(case["valid_count"] > 0 for case in formulas),
        "new_composition_valid_count": sum(case["valid_count"] for case in formulas),
        "new_composition_valid_unique_count": sum(case["valid_unique_count"] for case in formulas),
        "controls": controls, "new_compositions": formulas, "cohorts": cohorts,
        "topups_performed": 0, "posthoc_cell_count_admissions": 0,
        "interpretation": "Within one trained architecture, changing sampling group affects composition validity and structure recovery. No architecture-level or stable-material discovery claim follows from these draws."})
    write(OUT / "audit.json", {"status": "passed", "audited_at_utc": utc(), "checks_passed": checks,
        "model_draws_in_audit": 0, "run_plan_sha256": sha(OUT / "run_plan.json"),
        "audit_source_sha256": sha(Path(__file__)),
        "cif_parser_options": {"frac_tolerance": 0, "primitive": False},
        "cif_roundtrip_tolerances": {"lattice_matrix_absolute_angstrom": 1e-6, "species_matched_periodic_cartesian_angstrom": 1e-5},
        "earlier_read_only_audit_diagnostic": "The initial strict CIF check used the parser default, which rationalized near-special sampled fractions and failed. Disabling parser idealization preserves the file coordinates. No raw/CIF/JSON artifact or primary eligibility was changed; no numerical job was rerun.",
        "summary_sha256": sha(OUT / "summary.json"), "cohorts_audited": 10,
        "raw_attempts_audited": 80, "source_protocols_unchanged": True,
        "all_raw_batches_expanded_and_checked": True, "all_cif_roundtrips_pass": True,
        "reused_cohorts_unchanged": True, "no_primary_invalid_replacement": True})
    print(json.dumps({"audit": "passed", "checks": checks,
        "controls": [{"control": item["control"], "arm": item["arm"], "valid": item["valid_count"], "unique": item["valid_unique_count"]} for item in controls],
        "new_compositions": [{"formula": item["formula"], "valid": item["valid_count"], "unique": item["valid_unique_count"]} for item in formulas]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["freeze", "run", "audit"])
    action = parser.parse_args().action
    {"freeze": freeze, "run": run, "audit": audit}[action]()
