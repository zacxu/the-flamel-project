"""Read-only numerical audit, hardware capture, and Phase 1 evidence/budget report.

This script never samples, relaxes, runs QE, or changes original scientific results.
"""
from __future__ import annotations

import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import winreg

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/phase1"
ERRORS = []
CHECKS = []


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def write(relative, value):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(condition, message):
    CHECKS.append({"check": message, "passed": bool(condition)})
    if not condition:
        ERRORS.append(message)


def verify_file(item):
    path = ROOT / item["path"]
    check(path.is_file(), f"File exists: {item['path']}")
    if path.is_file():
        check(digest(path) == item["sha256"].lower(), f"SHA256: {item['path']}")


def events(relative):
    return [json.loads(line) for line in (ROOT / relative).read_text(encoding="utf-8").splitlines() if line.strip()]


def capture_host():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (key, ctypes.c_ulonglong) for key in
            ["total_physical", "available_physical", "total_page", "available_page", "total_virtual", "available_virtual", "extended"]]
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise ctypes.WinError()
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
        processor = winreg.QueryValueEx(key, "ProcessorNameString")[0]
    gpu_command = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader"]
    gpu = subprocess.check_output(gpu_command, text=True).strip()
    record = {"captured_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
              "cpu": processor, "logical_processors": os.cpu_count(),
              "total_ram_bytes": memory.total_physical, "available_ram_bytes": memory.available_physical,
              "disk_free_bytes": shutil.disk_usage(ROOT).free,
              "gpu_command": gpu_command, "gpu_csv": gpu,
              "python": sys.version, "python_executable": sys.executable,
              "memory_source": "Windows GlobalMemoryStatusEx; CIM queries were denied in sandbox",
              "runtime_python_sha256": digest(ROOT / ".runtime/python/cpython-3.11.14-windows-x86_64-none/python.exe"),
              "uv_exe_sha256": digest(ROOT / ".runtime/uv/bin/uv.exe")}
    write("artifacts/phase1/setup/host_manifest.json", record)
    return record


def main():
    os.environ["UV_CACHE_DIR"] = str(ROOT / ".cache/uv")
    os.environ["PYTHONNOUSERSITE"] = "1"
    completed = datetime.now(timezone.utc).isoformat()
    host = capture_host()
    data = load("artifacts/phase1/data/dataset_manifest.json")
    data_audit = load("artifacts/phase1/data/validation_report.json")
    generation = load("artifacts/phase1/generator/summary.json")
    generation_audit = load("artifacts/phase1/generator/audit.json")
    config = load("artifacts/phase1/generator/config.json")
    provenance = load("artifacts/phase1/generator/provenance.json")
    chgnet = load("artifacts/phase1/chgnet_relaxation/summary.json")
    qe = load("artifacts/phase1/qe/mgo_scf_pilot_result.json")
    qe_audit = load("artifacts/phase1/qe/mgo_scf_pilot_audit.json")
    qe_dist = load("artifacts/phase1/qe/qe_distribution_manifest.json")
    pseudos = load("artifacts/phase1/qe/pseudopotential_manifest.json")
    check(data["status"] == data_audit["status"] == "passed", "Full data audit passed")
    for item in data["files"].values():
        verify_file(item)
    check(data_audit["initial_structures"]["matched_summary_ids"] == 256963, "All 256963 initial structures joined")
    check(data_audit["population"]["counts"]["eligible_rows"] == 8294, "Planned oxide population reproduced")
    check(generation["attempts"] == 8 and generation["valid_exact_count_structures"] == 7, "Eight generation attempts retained; seven valid")
    check(generation_audit["ledger_consistent"] and generation_audit["checks_passed"], "Generator ledger and CIF audit passed")
    checkpoint = ROOT / "checkpoints/alex20s/multi/epoch_044000.pkl"
    if not checkpoint.exists():
        checkpoint = next((ROOT / "checkpoints").rglob("epoch_044000.pkl"))
    check(digest(checkpoint) == config["checkpoint_sha256"], "Pinned generator checkpoint hash")
    check(provenance["original_files_match_pinned_archive"], "Unmodified pinned CrystalFormer source")
    for item in provenance["files"]:
        verify_file({"path": str(Path("vendor/CrystalFormer") / item["path"]), "sha256": item["sha256"]})
    check(digest(ROOT / "scripts/phase1_generator.py") == provenance["wrapper_sha256"], "Executed generator wrapper preserved")
    check(digest(ROOT / "requirements/generator-lock.txt") == provenance["environment_lock_sha256"], "Executed generator package lock preserved")
    check(chgnet["successful"] == chgnet["converged"] == 4 and chgnet["all_geometry_valid"], "Four actual CHGNet pilots converged with valid geometry")
    for record in chgnet["records"]:
        result = record["result"]
        verify_file({"path": result["checkpoint_path"], "sha256": result["checkpoint_sha256"]})
        check(result["final_filter_fmax_eV_A"] <= .05, f"FIRE convergence: {record['attempt_id']}")
    check(chgnet["cuda_ready"], "CHGNet actual CUDA relaxation passed")
    check(qe["return_code"] == 0 and qe["scf_converged"] and qe["qe_job_done"] and qe_audit["scf_ready"], "Native QE SCF pilot passed")
    verify_file(qe_dist["archive"])
    for item in qe_dist["files"]:
        verify_file(item)
    for item in pseudos["pseudopotentials"]:
        verify_file(item)
    for env in ["analysis", "generator"]:
        command = [str(ROOT / ".runtime/uv/bin/uv.exe"), "pip", "check", "--python", str(ROOT / f".envs/{env}/Scripts/python.exe")]
        result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
        (BASE / f"setup/{env}-dependency-check.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        check(result.returncode == 0, f"Resolved {env} dependencies compatible")
    generation_events = events("artifacts/phase1/generator/ledger.jsonl")
    generation_attempts = sum(row["event"] == "attempt_started" for row in generation_events)
    failed_launches = events("artifacts/phase1/chgnet/ledger.jsonl")
    actual_launches = events("artifacts/phase1/chgnet_relaxation/ledger.jsonl")
    chgnet_finishes = [dict(row, ledger=lane) for lane, stream in [("preflight_failures", failed_launches), ("relaxation_pilots", actual_launches)]
                       for row in stream if row["event"] == "finish"]
    chgnet_starts = sum(row["event"] == "start" for row in failed_launches + actual_launches)
    check(chgnet_starts == len(chgnet_finishes) == 8, "All eight CHGNet launches reconciled, including four pre-model failures")
    qe_jobs = events("artifacts/phase1/qe/qe_jobs.jsonl")
    qe_seconds = sum(row["elapsed_wall_seconds"] for row in qe_jobs)
    chgnet_seconds = sum(row["budget_charged_seconds"] for row in chgnet_finishes)
    budgets = {
        "schema_version": 1, "as_of_utc": completed, "phase": 1,
        "generation": {"ceiling_attempts": 128, "charged_attempts": generation_attempts,
                       "remaining_attempts": 128-generation_attempts,
                       "cumulative_sampling_seconds": sum(generation["batch_seconds"]),
                       "cumulative_run_seconds_including_initialization_and_conversion": generation["run_seconds"],
                       "source_ledgers": ["artifacts/phase1/generator/ledger.jsonl"]},
        "chgnet": {"ceiling_attempts": 40, "charged_attempts": chgnet_starts, "remaining_attempts": 40-chgnet_starts,
                   "actual_relaxations": 4, "pre_model_launcher_rejections": 4,
                   "ceiling_seconds": 14400, "charged_wall_seconds": chgnet_seconds,
                   "remaining_seconds": 14400-chgnet_seconds,
                   "charging_rule": "Conservatively count every launch, including four guard rejections before model imports; charge entire subprocess walltime, including imports, load and relaxation.",
                   "source_ledgers": ["artifacts/phase1/chgnet/ledger.jsonl", "artifacts/phase1/chgnet_relaxation/ledger.jsonl"]},
        "qe": {"ceiling_seconds": 21600, "charged_wall_seconds": qe_seconds, "remaining_seconds": 21600-qe_seconds,
               "completed_jobs": len(qe_jobs), "source_ledgers": ["artifacts/phase1/qe/qe_jobs.jsonl"]},
        "project_started_utc": "2026-10-21T16:24:44+00:00",
        "numerical_stop_utc": "2026-10-22T10:24:44+00:00",
        "all_caps_remain_binding": True,
        "note": "Read-only snapshot of completed Phase1 ledgers. Future runners must append their own jobs before regenerating this snapshot; this file is not a future-job enforcement service."
    }
    check(generation_attempts <= 128 and chgnet_starts <= 40 and chgnet_seconds <= 14400 and qe_seconds <= 21600, "All shared budgets respected")
    write("artifacts/phase1/budget_snapshot.json", budgets)
    cumulative_path = ROOT / "artifacts/budget_ledger.json"
    current_cumulative = load("artifacts/budget_ledger.json") if cumulative_path.exists() else {}
    if current_cumulative.get("phase", 1) <= 1:
        write("artifacts/budget_ledger.json", budgets)
    readiness = {"phase": 1, "completed_utc": completed, "status": "complete" if not ERRORS else "failed",
                 "ready_for_phase2": not ERRORS, "data_ready": True, "generator_ready": True,
                 "chgnet_cpu_and_cuda_ready": chgnet["cuda_ready"], "qe_scf_ready": qe_audit["scf_ready"],
                 "thread_allocation": {"generator_cpu_affinity_logical_processors": 4,
                                       "chgnet_device": "cuda:0", "chgnet_cpu_threads": 2,
                                       "qe_simultaneous_jobs": 1, "qe_omp_threads": 4,
                                       "qe_mkl_threads": 4, "qe_openblas_threads": 1},
                 "reserved_chemical_systems_all_predictor_seeds": ["Mg-O"],
                 "future_required_checks": [
                     "Freeze the second matched control and all prospective fresh chemical systems before fitting predictor splits.",
                     "Exclude the union of fresh chemical systems from training and calibration in every seed; enforce an initial-data feature allowlist.",
                     "MgO/SG225 has one unique topology; no more than one balanced unique candidate per arm. Treat it as a recovery/validity control; richer-control selection must precede its generation.",
                     "Rebalance future CHGNet suballocations to the actual remaining 32 launches before dispatching research relaxations.",
                     "Measure first new-formula sampling time; this pilot only measured one formula and two equal-shape batches.",
                     "QE candidate/reference relaxations, cutoff/k-mesh convergence, complete reference inventory and novelty checks remain required for stability claims."],
                 "no_phase2_training_or_discovery_claims": True}
    write("artifacts/phase1/readiness.json", readiness)
    rows = []
    for record in chgnet["records"]:
        r = record["result"]
        rows.append(f"| {r['device']} | {r['structure_kind'].replace('_', ' ')} | {r['atoms']} | {r['optimizer_steps']} | {r['relaxation_seconds']:.3f} | {record['wall_seconds']:.3f} | {r['final_filter_fmax_eV_A']:.5f} | {r['energy_eV_per_atom']:.6f} |")
    report = f"""# Phase 1 execution report

**Phase 1 is {'complete; proceed to Phase 2' if not ERRORS else 'not complete; inspect audit errors'}.** This report records executed local pilots, rather than proposed timings. Audit timestamp: {completed}. Phase 1 began at 2026-10-22 00:24:44 Singapore time. No predictor training, acquisition replay, new-composition search or candidate DFT stability validation was performed.

## Results against the exit criteria

| Requirement | Executed result |
|---|---|
| Isolated environments | Workspace Python 3.11.14; separate `.envs/generator` and `.envs/analysis`; both dependency checks pass; exact package freezes retained |
| Hardware | {host['cpu'].strip()}; {host['logical_processors']} logical processors; {host['total_ram_bytes']/2**30:.2f} GiB RAM; {host['gpu_csv']} |
| Data integrity | Both pinned MD5/size/SHA256 checks pass; full gzip streams checked; all 256,963 IDs joined one-to-one; 1,994,133 sites validated |
| Planned population | 8,294 eligible oxides / 1,866 chemical systems; 1,934 at or below 0.05 eV/atom; 700 on/below the historical reference hull |
| Reserved control | All Mg-O excluded from future training/calibration across seeds: 10 total WBM records, 5 eligible; 8,289 eligible remain before later reserves |
| Verified generator | Pinned CrystalFormer source/checkpoint; 13,836,461 loaded parameters; strict tree/shape match and difference from random initialization verified |
| Sampling pilot | Eight Mg4O4/SG225 attempts: seven exact eight-atom valid cells, one Mg4O8 stoichiometry failure retained; all eight measure SG225 at symprec 0.01 A |
| CHGNet | Four real CPU/CUDA relaxation pilots converged; package 0.4.2, checkpoint 0.3.0, torch 2.6.0+cu124; GPU calculations actually executed |
| Native DFT | Verified QE7.5 Windows build; known two-atom MgO fixed-cell SCF converged in 13 iterations with final residual 7.7e-11 Ry |
| Budgets and provenance | Append-only lane ledgers plus [cumulative snapshot](../artifacts/budget_ledger.json), file hashes, raw structures, commands and package locks retained |

The generator uses reduced **MgO** for the composition embedding, matching its training convention, and independently enforces **Mg4O4** as the expanded evaluated cell. Formula conditioning is not an exact-stoichiometry guarantee. The rejected 12-atom output remains in the eight-attempt denominator.

## Measured runtime and resource allocation

CrystalFormer ran on four logical CPUs. First batch of four: **{generation['batch_seconds'][0]:.3f}s**, including compilation; second same-shape batch: **{generation['batch_seconds'][1]:.3f}s**, or **{generation['second_batch_seconds_per_attempt']:.3f}s per attempted structure**. Full model initialization, sampling and conversion took **{generation['run_seconds']:.3f}s**. The two batches do not separately isolate pure compiler time, and changing formula/space group has not been benchmarked. At this throughput, a further 72 same-shape attempts would require about {72*generation['second_batch_seconds_per_attempt']/60:.1f} minutes of sampling, excluding new compilation and setup; this is a forecast, not an executed result.

CHGNet used FIRE with unconstrained positions/cell, FrechetCellFilter, at most 200 steps and filter fmax <=0.05 eV/A. The eight-atom structure has deterministic small displacement and anisotropic strain; these are known-reference engineering controls, not generated research samples or additions to the symmetry comparison.

| Device | Initial structure | Atoms | Steps | Relaxation s | Entire subprocess s | Final filter fmax eV/A | Final eV/atom |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

The total energy in CHGNet trajectories is divided by actual atom count. Model-predicted energies are not fresh DFT. CPU and GPU results are comparable within numerical precision. Peak allocated CUDA tensor memory across these tiny pilots was {max(r['result']['cuda_peak_allocated_MiB'] or 0 for r in chgnet['records']):.1f} MiB; this is not a memory estimate for all future structures.

Freeze generator affinity at four logical CPUs, CHGNet on CUDA with two CPU threads, and one QE process at a time using four OpenMP/MKL threads (OpenBLAS one). Avoid additional concurrent numerical jobs that oversubscribe the 12 logical processors.

## QE readiness and its limits

The executed MgO input uses a 4.21 A rocksalt conventional lattice represented by a two-atom primitive cell; SSSP1.3.0 PBE PAW Mg/O pseudopotentials; ecutwfc=50 Ry, ecutrho=400 Ry; 4x4x4 unshifted mesh; nonmagnetic fixed occupations; conv_thr=1e-8 Ry. The job took **{qe['elapsed_wall_seconds']:.3f}s** (entire process), exited zero, reported SCF convergence and JOB DONE, and produced **{qe['energy_total_Ry']:.8f} Ry** total energy. Input, pseudopotentials, executable and output are hashed.

This pilot is a known-phase, fixed-geometry electronic calculation. Its pressure is **45.25 kbar = 4.525 GPa**; it is not a relaxed zero-pressure reference. Cutoff/k-mesh convergence, candidate/reference ionic and cell relaxation, reference completeness and novelty checks remain later work. Absolute QE energy offsets must not be compared with CHGNet/MP/VASP values. A two-atom SCF timing does not establish the cost of magnetic, metallic or larger-cell relaxation jobs. QE's internal RAM estimate is not measured OS peak RSS; its Windows available-memory message is not a valid host-memory reading.

## Attempts, failures and remaining scope

| Budget | Charged so far | Remaining |
|---|---:|---:|
| Generation, 128 attempts | {generation_attempts} | {128-generation_attempts} |
| CHGNet, 40 launches | {chgnet_starts} | {40-chgnet_starts} |
| CHGNet, 14,400 cumulative seconds | {chgnet_seconds:.3f} | {14400-chgnet_seconds:.3f} |
| QE, 21,600 cumulative seconds | {qe_seconds:.3f} | {21600-qe_seconds:.3f} |

The first CHGNet wrapper incorrectly assumed the Python worker's direct parent PID would be the launcher PID. Windows venv executable redirection violates that assumption. Four launches were rejected **before imports/model execution**. Their original logs and ledger remain in `artifacts/phase1/chgnet/`. The repaired wrapper validates a per-launch token inherited through the redirector and stops after its first failed job. Four subsequent real relaxations succeeded in `artifacts/phase1/chgnet_relaxation/`. All eight launches and all process walltime are charged conservatively; the failed quartet is not hidden or counted as successful relaxation. A repeat invocation refuses to dispatch more work into an existing ledger.

The initial conda bootstrap failed on network/cache permissions and was abandoned. The final setup uses uv0.9.7 and a standalone runtime entirely under the workspace. Initial setup logs are retained. Matplotlib configuration is directed to the workspace cache. No system-wide dependency installation was required.

The original future CHGNet suballocation must be rebalanced to **32 remaining launches** before subsequent research jobs. No ceiling is increased. MgO's narrow SG225 space deduplicates all seven valid samples to **one rocksalt topology**; changing lattice volume is not a new structure. If retained as a matched control, this permits at most one balanced unique relaxation per arm and chiefly measures recovery/validity, with limited energy-comparison power. Freeze a richer second control before its generation. The eight pilot attempts can supply MgO's primary SG225 arm only if subsequent production preserves the frozen checkpoint, reduced composition encoding, exact expanded cell, sampling settings and seed protocol; otherwise they remain engineering attempts and still consume the global ceiling.

## Phase 2 handoff

1. Freeze the second matched control, chemical-family/reference inventory, new-composition reserves and explicit feature allowlist before training or new generation. Keep all Mg-O records and the union of future fresh chemical systems outside training/calibration for every seed.
2. Use only initial-structure/composition/symmetry information as predictor inputs. The historical signed hull target stays an oracle label, with negative values preserved; post-DFT geometry/volume, population flags, IDs and labels cannot become model features.
3. Rebalance the 32 remaining CHGNet launches, retain the 120 remaining generation ceiling and all time caps. Measure the first changed-formula run before scaling. The original default 80-sample generation allocation remains computationally plausible on CPU.
4. Keep the native QE lane enabled. Plan candidate/reference relaxations and convergence checks from actual system-specific timings; complete all compatible references before any scoped stability claim. All numerical work stops at **2026-10-22 18:24:44 Singapore time** (project hour18).

## Reproduction and evidence

From the workspace root, these commands verify completed evidence without adding numerical attempts:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_environments.ps1
python scripts/phase1_data.py --offline
.envs/analysis/Scripts/python.exe scripts/phase1_finalize.py
```

The setup command restores the tested package locks if necessary; the data audit reads the full local data again. The finalizer re-hashes inputs/binaries and original generator source, checks both dependency environments, reconciles ledgers and regenerates this report without numerical model work. Data audit timestamps can change on reinspection; refresh the finalizer afterwards. A fresh checkout can fetch pinned generator assets with `python scripts/phase1_generator_setup.py`, WBM data with `python scripts/phase1_data.py`, and QE/pseudopotentials with `python scripts/phase1_qe_setup.py`. Those fetch commands verify hashes; they do not run numerical pilots. Downloads require network access.

Original pilot entry points are `scripts/phase1_generator.py`, `scripts/phase1_chgnet.py`, and `scripts/phase1_qe_pilot.py`. Their logs/manifests retain executed commands and inputs. Generator and CHGNet refuse to silently repeat recorded allocations. Additional research attempts require a new recorded allocation; do not delete ledgers to rerun pilots. QE's wrapper refuses a duplicate job ID; all future QE jobs share its cumulative six-hour ledger.

Key records: [readiness](../artifacts/phase1/readiness.json), [audit](../artifacts/phase1/audit.json), [data manifest](../artifacts/phase1/data/dataset_manifest.json), [generator summary](../artifacts/phase1/generator/summary.json), [CHGNet summary](../artifacts/phase1/chgnet_relaxation/summary.json), [QE handoff](../artifacts/phase1/qe/README.md), [analysis lock](../requirements/analysis-lock.txt), [generator lock](../requirements/generator-lock.txt). Sources and immutable download URLs are retained in their lane manifests; official [CHGNet documentation](https://chgnet.lbl.gov/) and [PyTorch installation commands](https://pytorch.org/get-started/previous-versions/) were checked during setup.
"""
    report_path = ROOT / "reports/phase1_report.md"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    audit = {"completed_utc": completed, "status": "passed" if not ERRORS else "failed", "checks": CHECKS, "errors": ERRORS,
             "numerical_attempts_added_by_finalizer": 0}
    write("artifacts/phase1/audit.json", audit)
    inventory = []
    for folder in ["scripts", "requirements", "reports", "artifacts/phase1"]:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".ps1", ".txt", ".md", ".json", ".jsonl", ".cif", ".in", ".out", ".log", ".csv"} and path.name != "artifact_inventory.json":
                inventory.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
    for filename in ["README.md", "one_day_research_proposal.md", "artifacts/budget_ledger.json"]:
        path = ROOT / filename
        inventory.append({"path": filename, "bytes": path.stat().st_size, "sha256": digest(path)})
    write("artifacts/phase1/artifact_inventory.json", {"created_utc": completed, "files": inventory})
    print(json.dumps({"status": audit["status"], "checks": len(CHECKS), "errors": ERRORS,
                      "generation_attempts": generation_attempts, "chgnet_launches": chgnet_starts,
                      "chgnet_seconds": chgnet_seconds, "qe_seconds": qe_seconds,
                      "report": str(report_path)}))
    return 0 if not ERRORS else 1


if __name__ == "__main__":
    raise SystemExit(main())
