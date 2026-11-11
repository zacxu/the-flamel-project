"""Bounded, one-job-at-a-time native QE SCF pilot; this is not a stability test."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "phase1" / "qe"
LEDGER = ART / "qe_jobs.jsonl"
LOCK = ART / "qe_active.lock"
EXPECTED_ZIP_HASH = "e50ec7368a5b7a964eb5084e0a13464ba2628d4e147c16227e876002ea34fdf7"
TOTAL_LIMIT_SECONDS = 6 * 3600
TIMEOUT_SECONDS = 600


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ART.mkdir(parents=True, exist_ok=True)
    vendor = json.loads((ART / "qe_distribution_manifest.json").read_text(encoding="utf-8"))
    pseudo_manifest = json.loads((ART / "pseudopotential_manifest.json").read_text(encoding="utf-8"))
    archive = ROOT / vendor["archive"]["path"]
    if sha256(archive) != EXPECTED_ZIP_HASH:
        raise RuntimeError("QE archive SHA256 is not the independently pinned release digest")
    exes = vendor["executables"]
    if len(exes) != 1:
        raise RuntimeError(f"Expected exactly one pw.exe, found {len(exes)}")
    executable = ROOT / exes[0]["path"]
    for record in vendor["files"]:
        path = ROOT / record["path"]
        if path.suffix.lower() in {".exe", ".dll"} and sha256(path) != record["sha256"]:
            raise RuntimeError(f"Staged binary changed: {path}")
    for record in pseudo_manifest["pseudopotentials"]:
        if sha256(ROOT / record["path"]) != record["sha256"]:
            raise RuntimeError(f"Pseudopotential changed: {record['path']}")
    existing = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()] if LEDGER.exists() else []
    consumed = sum(row.get("elapsed_wall_seconds", 0.0) for row in existing)
    if consumed + TIMEOUT_SECONDS > TOTAL_LIMIT_SECONDS:
        raise RuntimeError("Insufficient remaining cumulative QE walltime")
    if (ART / "mgo_scf_pilot_result.json").exists():
        raise RuntimeError("Pilot result already exists; preserve it and use an explicitly named new job")
    pseudopotentials = {row["element"]: row for row in pseudo_manifest["pseudopotentials"]}
    job = ART / "mgo_scf_pilot"
    job.mkdir(exist_ok=True)
    (job / "scratch").mkdir(exist_ok=True)
    # Local copies avoid absolute-path/Fortran parser ambiguity; hashes are checked.
    (job / "pseudo").mkdir(exist_ok=True)
    for element, record in pseudopotentials.items():
        (job / "pseudo" / record["filename"]).write_bytes((ROOT / record["path"]).read_bytes())
    lattice_a = 4.21
    parameters = {"calculation": "scf", "formula": "MgO", "n_atoms": 2,
                  "prototype": "rocksalt", "conventional_a_angstrom": lattice_a,
                  "primitive_cell_angstrom": [[0, lattice_a/2, lattice_a/2],
                      [lattice_a/2, 0, lattice_a/2], [lattice_a/2, lattice_a/2, 0]],
                  "fractional_positions": {"Mg": [0, 0, 0], "O": [0.5, 0.5, 0.5]},
                  "ecutwfc_Ry": 50, "ecutrho_Ry": 400,
                  "k_mesh": [4, 4, 4], "k_offset": [0, 0, 0], "nspin": 1,
                  "occupations": "fixed", "conv_thr_Ry": 1e-8, "electron_maxstep": 100,
                  "status_scope": "Engine/SCF readiness only; lattice, cutoff and k mesh not converged in this pilot"}
    input_text = f"""&CONTROL
 calculation='scf', prefix='mgo_phase1', pseudo_dir='./pseudo', outdir='./scratch',
 tprnfor=.true., tstress=.true., verbosity='high', max_seconds=540,
/
&SYSTEM
 ibrav=0, nat=2, ntyp=2, ecutwfc=50.0, ecutrho=400.0,
 input_dft='PBE', occupations='fixed', nspin=1,
/
&ELECTRONS
 conv_thr=1.0d-8, electron_maxstep=100, mixing_beta=0.5,
/
ATOMIC_SPECIES
Mg 24.305 {pseudopotentials['Mg']['filename']}
O 15.999 {pseudopotentials['O']['filename']}
CELL_PARAMETERS angstrom
0.000000 2.105000 2.105000
2.105000 0.000000 2.105000
2.105000 2.105000 0.000000
ATOMIC_POSITIONS crystal
Mg 0.0 0.0 0.0
O 0.5 0.5 0.5
K_POINTS automatic
4 4 4 0 0 0
"""
    input_path = job / "mgo.scf.in"
    output_path = job / "mgo.scf.out"
    error_path = job / "mgo.scf.stderr.txt"
    input_path.write_text(input_text, encoding="ascii")
    (job / "parameters.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")
    environment = os.environ.copy()
    thread_settings = {"OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
                       "OPENBLAS_NUM_THREADS": "1", "OMP_DYNAMIC": "FALSE", "MKL_DYNAMIC": "FALSE"}
    environment.update(thread_settings)
    environment["PATH"] = str(executable.parent) + os.pathsep + environment.get("PATH", "")
    command = [str(executable), "-in", input_path.name]
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(lock_fd, json.dumps({"runner_pid": os.getpid(), "start_utc": stamp(), "job": str(job)}).encode())
    os.close(lock_fd)
    started_at = stamp()
    started = time.perf_counter()
    process = None
    timed_out = False
    launch_error = None
    try:
        with output_path.open("wb") as output, error_path.open("wb") as error:
            process = subprocess.Popen(command, cwd=job, env=environment, stdout=output, stderr=error,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            print(json.dumps({"event": "qe_job_started", "pid": process.pid,
                              "started_at_utc": started_at, "command": command,
                              "threads": thread_settings, "timeout_seconds": TIMEOUT_SECONDS}), flush=True)
            try:
                process.wait(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                timed_out = True
                # Kill only this identified job and its children; preserve scratch restart files.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                process.wait(timeout=30)
    except Exception as exc:
        launch_error = repr(exc)
    finally:
        elapsed = time.perf_counter() - started
        stdout = output_path.read_text(encoding="utf-8", errors="replace") if output_path.exists() else ""
        energies = re.findall(r"!\s+total energy\s+=\s+([-+0-9.EeDd]+)\s+Ry", stdout)
        energy_ry = float(energies[-1].replace("D", "E")) if energies else None
        iterations = re.findall(r"convergence has been achieved in\s+(\d+)\s+iterations", stdout)
        scf_converged = bool(iterations) and "convergence NOT achieved" not in stdout
        result = {"job_id": "phase1_mgo_scf_pilot", "started_at_utc": started_at,
                  "finished_at_utc": stamp(), "elapsed_wall_seconds": elapsed,
                  "cumulative_qe_wall_seconds": consumed + elapsed,
                  "return_code": process.returncode if process else None,
                  "timed_out": timed_out, "launch_error": launch_error,
                  "scf_converged": scf_converged, "qe_job_done": "JOB DONE." in stdout,
                  "scf_iterations": int(iterations[-1]) if iterations else None,
                  "energy_total_Ry": energy_ry,
                  "energy_eV_per_atom": energy_ry * 13.605693122994 / 2 if energy_ry is not None else None,
                  "has_forces": "Forces acting on atoms" in stdout,
                  "has_stress": "total   stress" in stdout,
                  "threads": thread_settings, "timeout_seconds": TIMEOUT_SECONDS,
                  "command": command, "input_sha256": sha256(input_path),
                  "output_sha256": sha256(output_path), "parameters": parameters,
                  "interpretation": "Known-phase fixed-geometry SCF readiness test; no ionic relaxation, cutoff/k convergence, formation energy or phase stability claim"}
        with LEDGER.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(result) + "\n")
        (ART / "mgo_scf_pilot_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        LOCK.unlink()
        print(json.dumps(result, indent=2), flush=True)
    if launch_error or timed_out or result["return_code"] != 0 or not scf_converged or not result["qe_job_done"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
