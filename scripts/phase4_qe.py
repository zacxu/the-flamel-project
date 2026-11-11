"""Phase4 bounded CaO anchor refinement; no generator outcome changes scope.

Forks the frozen Phase3 executor without modifying its source or artifacts.
Only reviewed nonmagnetic CaO geometry descendants are supported.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pymatgen.core import Structure

from phase2_dft_inputs import qe_input
from phase3_qe_parser import parse_job

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "phase4" / "qe"
LEGACY = ROOT / "artifacts" / "phase1" / "qe" / "qe_jobs.jsonl"
EVENTS = ART / "events.jsonl"
LOCK = ROOT / "artifacts" / "phase1" / "qe" / "qe_active.lock"
sys.path.insert(0, str(ROOT))


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def event(value):
    ART.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at_utc": now(), **value}) + "\n")


def memory_bytes(process):
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ["PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
            "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage"]]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    fn = ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    return int(counters.PeakWorkingSetSize) if fn(int(process._handle), ctypes.byref(counters), counters.cb) else None


def prepare(args):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,90}", args.job_id):
        raise ValueError("Unsafe or empty job ID")
    directory = ART / args.job_id
    if directory.exists():
        raise RuntimeError("Job directory already exists; use a new explicit job ID")
    queue_path = ART / "queue_plan.json"
    queue = json.loads(queue_path.read_text())
    if queue.get("status") != "authorized_before_dispatch" or args.job_id not in queue["allowed_job_ids"]:
        raise RuntimeError("Job is outside the bounded authorized Phase4 queue")
    specification = queue["jobs"][args.job_id]
    for key in ("calculation", "role", "max_seconds", "outer_timeout"):
        if getattr(args, key) != specification[key]:
            raise RuntimeError(f"Job {key} is outside predeclared queue settings")
    for key in ("cutoff_multiplier", "k_spacing"):
        allowed = specification.get("allowed_" + key, [specification.get(key)])
        if not any(value is not None and abs(getattr(args, key) - value) < 1e-10 for value in allowed):
            raise RuntimeError(f"Job {key} is outside predeclared queue settings")
    reference_plan_path = ROOT / "artifacts" / "phase2" / "dft" / "primary_reference_plan.json"
    reference_plan = json.loads(reference_plan_path.read_text())
    source_metadata = None
    if args.reference_id:
        source_metadata = next(row for row in reference_plan["records"] if row["material_id"] == args.reference_id)
        geometry_path = ROOT / source_metadata["execution_geometry_path"]
        expected = source_metadata["execution_geometry_sha256"]
        if source_metadata["settings"]["spin_review_required_before_reference_acceptance"]:
            raise RuntimeError("Reference requires explicit spin/occupation review; this wrapper cannot silently run it")
    else:
        if not args.geometry or not args.expected_geometry_sha256:
            raise ValueError("Explicit geometry and expected SHA256 are required")
        geometry_path = (ROOT / args.geometry).resolve()
        expected = args.expected_geometry_sha256.lower()
    if not geometry_path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Geometry lies outside workspace")
    if digest(geometry_path) != expected:
        raise RuntimeError("Geometry checksum mismatch")
    if geometry_path.parent.name not in specification["allowed_parent_jobs"] or geometry_path.name != "final_geometry.json":
        raise RuntimeError("Source geometry is outside the predeclared CaO lineage")
    if geometry_path.parent.name == queue["initial_source_job"] and expected != queue["initial_source_geometry_sha256"]:
        raise RuntimeError("Initial CaO geometry differs from the frozen Phase3 handoff")
    structure = Structure.from_file(geometry_path)
    if structure.composition.reduced_formula != "CaO" or len(structure) != 2:
        raise RuntimeError("Phase4 queue supports only the reviewed two-atom CaO anchor, without source-cell reduction")
    if args.role not in {"reference", "sensitivity"}:
        raise RuntimeError("Candidate and metal/O2 execution are outside this Phase4 queue")
    if args.role == "candidate" and not args.selection_manifest:
        raise ValueError("Candidate requires frozen early-selection manifest provenance")
    inherited_settings_path = geometry_path.parent / "settings.json"
    inherited_settings = json.loads(inherited_settings_path.read_text()) if inherited_settings_path.exists() else {}
    metallic = ((source_metadata is not None and source_metadata["settings"]["occupations"] == "smearing")
                or inherited_settings.get("occupations") == "smearing")
    elements_present = {element.symbol for element in structure.composition.elements}
    inherited_spin_review = (inherited_settings.get("nspin", 1) != 1
        or inherited_settings.get("spin_review_required_before_reference_acceptance", False)
        or inherited_settings.get("molecular_oxygen", False))
    if (not elements_present.issubset({"Ca", "Mg", "O"}) or "O" not in elements_present
            or len(elements_present) < 2 or metallic or inherited_spin_review):
        raise RuntimeError("Phase3 supports nonmagnetic Ca/Mg oxides only; metals, O2, unsupported elements, and inherited spin/occupation-review jobs require a separately authorized protocol")
    fallback_binding = None
    if args.role == "candidate":
        selection_path = (ROOT / args.selection_manifest).resolve()
        if not selection_path.is_relative_to(ROOT.resolve()):
            raise ValueError("Selection manifest outside workspace")
        expected_selection = getattr(args, "expected_selection_sha256", None)
        if expected_selection and digest(selection_path) != expected_selection:
            raise RuntimeError("Frozen DFT handoff checksum mismatch")
        handoff = json.loads(selection_path.read_text())
        matches = [row for row in handoff["DFT_queue_in_frozen_order"]
                   if (ROOT / row["final_structure"]).resolve() == geometry_path.resolve()
                   and row["final_structure_sha256"] == expected]
        if len(matches) != 1:
            raise RuntimeError("Candidate geometry is not an exact member of the frozen DFT queue")
        formula = structure.composition.reduced_formula
        if len(structure) > 10 or formula not in {"CaMg2O3", "MgO"}:
            raise ValueError("Candidate outside frozen Phase3 small-cell formula scope")
        if formula == "MgO":
            fallback_path = ROOT / "artifacts" / "phase3" / "selection" / "fallback_decision.json"
            fallback = json.loads(fallback_path.read_text())
            if not handoff.get("fallback_result") or matches[0]["candidate_id"] != fallback["candidate_id"]:
                raise RuntimeError("Known MgO fallback was not predeclared/frozen")
            fallback_binding = {"candidate_id": fallback["candidate_id"], "decision_path": str(fallback_path.relative_to(ROOT)),
                                "decision_sha256": digest(fallback_path), "scope": "known-control MgO recovery; no new material/composition claim"}
    pseudo_manifest_path = ROOT / "artifacts" / "phase2" / "dft" / "pseudopotentials.json"
    all_pseudos = json.loads(pseudo_manifest_path.read_text())["elements"]
    used_pseudos = {element.symbol: all_pseudos[element.symbol] for element in structure.composition.elements}
    for row in used_pseudos.values():
        if digest(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError("Pseudopotential checksum mismatch")
    vendor = json.loads((ROOT / "artifacts" / "phase1" / "qe" / "qe_distribution_manifest.json").read_text())
    executable = ROOT / vendor["executables"][0]["path"]
    if digest(executable) != vendor["executables"][0]["sha256"]:
        raise RuntimeError("QE executable checksum mismatch")
    directory.mkdir(parents=True)
    (directory / "scratch").mkdir()
    (directory / "pseudo").mkdir()
    for row in used_pseudos.values():
        (directory / "pseudo" / row["filename"]).write_bytes((ROOT / row["path"]).read_bytes())
    prefix = args.job_id.lower()
    text, settings = qe_input(structure, all_pseudos, prefix=prefix, calculation=args.calculation,
                              cutoff_multiplier=args.cutoff_multiplier, k_spacing=args.k_spacing,
                              max_seconds=args.max_seconds, metallic=metallic)
    pressure_threshold = getattr(args, "pressure_threshold", 0.5)
    if not 0 < pressure_threshold <= 0.5:
        raise ValueError("Pressure continuation threshold must be positive and no looser than frozen0.5kbar")
    text = text.replace("press_conv_thr=0.5", f"press_conv_thr={pressure_threshold:.10g}")
    settings["press_conv_thr_kbar"] = pressure_threshold
    settings.update({"prefix": prefix, "molecular_oxygen": False, "source_geometry_sha256": expected})
    input_path = directory / "pw.in"
    input_path.write_text(text, encoding="ascii")
    structure.to(filename=str(directory / "initial_geometry.cif"))
    save(directory / "initial_geometry.json", structure.as_dict())
    save(directory / "settings.json", settings)
    stage = {"job_id": args.job_id, "phase": 4,
             "queue_plan_sha256": digest(queue_path), "queue_plan": str(queue_path.relative_to(ROOT)), "category": args.role, "prepared_at_utc": now(),
             "role": args.role, "reference_id": args.reference_id,
             "source_geometry": str(geometry_path.relative_to(ROOT)), "source_geometry_sha256": expected,
             "source_reference_metadata": source_metadata,
             "inherited_source_settings": str(inherited_settings_path.relative_to(ROOT)) if inherited_settings_path.exists() else None,
             "inherited_source_settings_sha256": digest(inherited_settings_path) if inherited_settings_path.exists() else None,
             "input_sha256": digest(input_path), "settings_sha256": digest(directory / "settings.json"),
             "pseudo_hashes": {element: row["sha256"] for element, row in used_pseudos.items()},
             "pseudo_files": {element: row["filename"] for element, row in used_pseudos.items()},
             "executable": str(executable), "executable_sha256": digest(executable),
             "input_factory_sha256": digest(ROOT / "scripts" / "phase2_dft_inputs.py"),
             "runner_source_sha256": digest(ROOT / "scripts" / "phase4_qe.py"),
             "parser_source_sha256": digest(ROOT / "scripts" / "phase3_qe_parser.py"),
             "python_executable": sys.executable,
             "numerical_protocol_sha256": digest(ROOT / "artifacts" / "phase2" / "dft" / "numerical_protocol.json"),
             "outer_timeout_seconds": args.outer_timeout, "settings": settings,
             "selection_manifest": args.selection_manifest,
             "fallback_binding": fallback_binding,
             "selection_manifest_sha256": digest(ROOT / args.selection_manifest) if args.selection_manifest else None}
    save(directory / "stage.json", stage)
    event({"event": "prepared", "job_id": args.job_id, "input_sha256": stage["input_sha256"]})
    return directory, stage


def execute(directory, stage):
    from research_budget import reserve_job, finish_job
    if (directory / "result.json").exists():
        raise RuntimeError("Cannot overwrite completed attempt")
    input_path = directory / "pw.in"
    if digest(ROOT / stage["queue_plan"]) != stage["queue_plan_sha256"]:
        raise RuntimeError("Authorized queue manifest changed after staging")
    if digest(input_path) != stage["input_sha256"] or digest(Path(stage["executable"])) != stage["executable_sha256"]:
        raise RuntimeError("Pre-dispatch input/executable hash changed")
    for element, filename in stage["pseudo_files"].items():
        if digest(directory / "pseudo" / filename) != stage["pseudo_hashes"][element]:
            raise RuntimeError("Pre-dispatch pseudopotential hash changed")
    prior = [json.loads(line) for line in LEGACY.read_text().splitlines()]
    phase4_seconds = sum(row["elapsed_wall_seconds"] for row in prior if row.get("phase") == 4)
    if phase4_seconds + stage["outer_timeout_seconds"] > 2700:
        raise RuntimeError("Phase4 predeclared45-minute QE ceiling would be exceeded by this reservation")
    command = [stage["executable"], "-in", "pw.in"]
    ticket = reserve_job(lane="qe", job_id=stage["job_id"], attempts=1,
                         max_seconds=stage["outer_timeout_seconds"], phase=4, category=stage["category"],
                         metadata={"queue_plan_sha256": stage["queue_plan_sha256"],
                                   "input_sha256": stage["input_sha256"], "pseudo_hashes": stage["pseudo_hashes"],
                                   "executable_sha256": stage["executable_sha256"], "command": command,
                                   "selection_manifest_sha256": stage["selection_manifest_sha256"],
                                   "source_geometry_sha256": stage["source_geometry_sha256"],
                                   "fallback_binding": stage["fallback_binding"]})
    settings = stage["settings"]
    threads = {"OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "1",
               "OMP_DYNAMIC": "FALSE", "MKL_DYNAMIC": "FALSE"}
    environment = os.environ.copy()
    environment.update(threads)
    environment["PATH"] = str(Path(stage["executable"]).parent) + os.pathsep + environment.get("PATH", "")
    process = None
    locked = False
    timeout = False
    launch_error = None
    peak_memory = 0
    started_at = now()
    start = time.perf_counter()
    try:
        lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(lock_fd, json.dumps({"runner_pid": os.getpid(), "job_id": stage["job_id"], "start_utc": started_at}).encode())
        os.close(lock_fd)
        locked = True
        with (directory / "pw.out").open("wb") as output, (directory / "pw.stderr.txt").open("wb") as error:
            process = subprocess.Popen(command, cwd=directory, env=environment, stdout=output, stderr=error,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            event({"event": "started", "job_id": stage["job_id"], "pid": process.pid,
                   "reservation_id": stage["job_id"], "threads": threads})
            print(json.dumps({"event": "started", "job_id": stage["job_id"], "pid": process.pid}), flush=True)
            while process.poll() is None:
                peak_memory = max(peak_memory, memory_bytes(process) or 0)
                # Preserve a bounded cleanup margin inside the reserved allowance.
                if time.perf_counter() - start > stage["outer_timeout_seconds"] - 15:
                    timeout = True
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                    process.wait(timeout=5)
                    break
                time.sleep(0.1)
    except Exception as exc:
        launch_error = repr(exc)
        if process is not None and process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            process.wait(timeout=5)
    finally:
        elapsed = time.perf_counter() - start
        parsed = parse_job(directory, settings, return_code=process.returncode if process else None, timed_out=timeout)
        record = {"job_id": stage["job_id"], "phase": 4, "category": stage["category"],
                  "started_at_utc": started_at, "finished_at_utc": now(),
                  "elapsed_wall_seconds": elapsed, "return_code": process.returncode if process else None,
                  "timed_out": timeout, "launch_error": launch_error,
                  "peak_working_set_bytes_observed": peak_memory or None,
                  "threads": threads, "input_sha256": stage["input_sha256"],
                  "output_sha256": digest(directory / "pw.out") if (directory / "pw.out").exists() else None,
                  "result": parsed, "provenance": stage}
        with LEGACY.open("a", encoding="utf-8") as legacy:
            legacy.write(json.dumps(record) + "\n")
        save(directory / "result.json", record)
        status = "timeout" if timeout else "completed" if parsed["job_scf_accepted"] and not launch_error else "failed"
        try:
            snapshot = finish_job(ticket, wall_seconds=elapsed, status=status,
                                  metadata={"legacyledger_jobid": stage["job_id"],
                                            "scf_converged": parsed["scf_converged"],
                                            "stationary": parsed["job_stationary_at_this_setting"],
                                            "result_path": str((directory / "result.json").relative_to(ROOT))})
            save(directory / "budget_after.json", snapshot)
        finally:
            if locked:
                LOCK.unlink()
        event({"event": "finished", "job_id": stage["job_id"], "status": status,
               "elapsed_wall_seconds": elapsed, "stationary": parsed["job_stationary_at_this_setting"]})
        print(json.dumps({"job_id": stage["job_id"], "elapsed_wall_seconds": elapsed,
                          "result": parsed}, indent=2), flush=True)
    return 0 if parsed["job_scf_accepted"] and not launch_error else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--reference-id")
    parser.add_argument("--geometry")
    parser.add_argument("--expected-geometry-sha256")
    parser.add_argument("--selection-manifest")
    parser.add_argument("--expected-selection-sha256")
    parser.add_argument("--role", choices=("reference", "sensitivity"), default="reference")
    parser.add_argument("--calculation", choices=("vc-relax", "scf", "relax"), default="vc-relax")
    parser.add_argument("--cutoff-multiplier", type=float, default=1.0)
    parser.add_argument("--k-spacing", type=float, default=0.60)
    parser.add_argument("--pressure-threshold", type=float, default=0.5)
    parser.add_argument("--max-seconds", type=int, default=900)
    parser.add_argument("--outer-timeout", type=int, default=930)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.max_seconds <= 0 or args.outer_timeout <= args.max_seconds or args.outer_timeout > 1230:
        raise ValueError("Invalid bounded job timeouts")
    if not np.isfinite(args.cutoff_multiplier) or args.cutoff_multiplier <= 0 or not np.isfinite(args.k_spacing) or args.k_spacing <= 0:
        raise ValueError("Cutoff multiplier and reciprocal spacing must be finite and positive")
    folder, staged = prepare(args)
    raise SystemExit(0 if args.prepare_only else execute(folder, staged))
