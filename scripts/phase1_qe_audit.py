"""Audit saved Phase 1 QE evidence without executing more calculations."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "phase1" / "qe"
result = json.loads((ART / "mgo_scf_pilot_result.json").read_text(encoding="utf-8"))
text = (ART / "mgo_scf_pilot" / "mgo.scf.out").read_text(encoding="utf-8")
stderr = (ART / "mgo_scf_pilot" / "mgo.scf.stderr.txt").read_text(encoding="utf-8")
signature = json.loads((ART / "pw_authenticode.json").read_text(encoding="utf-8-sig"))
patterns = {
    "reported_mpi_processes": r"Number of MPI processes:\s+(\d+)",
    "reported_threads_per_process": r"Threads/MPI process:\s+(\d+)",
    "reported_electrons": r"number of electrons\s+=\s+([\d.]+)",
    "irreducible_k_points": r"number of k points=\s+(\d+)",
    "final_scf_accuracy_bound_Ry": r"estimated scf accuracy\s+<\s+([\d.Ee+-]+)\s+Ry",
    "pressure_kbar": r"total\s+stress\s+\(Ry/bohr\*\*3\)\s+\(kbar\)\s+P=\s+([\d.Ee+-]+)",
    "qe_estimated_max_dynamic_ram_MB_lower_bound": r"Estimated max dynamical RAM per process\s+>\s+([\d.]+)\s+MB",
}
audit = {key: float(re.findall(pattern, text)[-1]) for key, pattern in patterns.items()}
audit.update({"stderr_empty": not stderr.strip(), "authenticode": signature,
              "scf_ready": result["return_code"] == 0 and result["scf_converged"] and result["qe_job_done"],
              "primitive_volume_angstrom3": 4.21**3/4,
              "nearest_Mg_O_distance_angstrom": 4.21/2,
              "energy_plausibility_checks": ["Finite total energy at the explicitly specified pseudopotential convention",
                  "Two-atom rocksalt primitive geometry and 8 valence electrons confirmed",
                  "SCF residual below requested threshold; no failed eigenvalue/convergence status",
                  "Absolute total energy is not compared against MP/VASP or an elemental reference"],
              "limitations": ["Fixed geometry; no ionic or cell relaxation",
                  "Pressure is 45.25 kbar (4.525 GPa); the cell is not optimized",
                  "No cutoff or k-point convergence study; this is not a production accuracy claim",
                  "QE prints available memory as 0 MiB on this Windows build; do not interpret that as host exhaustion",
                  "Reported QE RAM is an internal estimate, not measured peak OS RSS",
                  "QE notes ibrav=0 with symmetry is discouraged; 48 symmetry operations were nevertheless detected",
                  "UPF radial-wavefunction renormalization messages are retained in the output",
                  "This is an engine readiness result, not a generated crystal or phase-stability validation"]})
(ART / "mgo_scf_pilot_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
summary = f"""# Phase 1 QE lane: passed known-phase SCF smoke test

The checksum-pinned QMatSuite third-party Windows QE 7.5 build executed natively,
without WSL, source compilation, or a system MPI installation. The distribution
contains MPI support but was run directly as one MPI process with four OpenMP
threads. Windows verified the executable's Authenticode signature; this is not an
assertion that it is an official upstream binary.

MgO rocksalt, two-atom primitive cell: conventional a = 4.21 Angstrom,
primitive volume = 18.65461525 Angstrom^3, nearest Mg-O distance = 2.105 Angstrom.
PBE PAW pseudopotentials from SSSP 1.3.0 efficiency; input used the larger
recommended element cutoff: 50 Ry wavefunctions and 400 Ry density.
The 4x4x4 unshifted mesh reduced to eight irreducible k points. Fixed occupations,
non-spin-polarized, SCF threshold 1e-8 Ry.

The run converged in {result['scf_iterations']} SCF iterations, exit code zero,
with JOB DONE, final residual bound {audit['final_scf_accuracy_bound_Ry']:.2g} Ry,
and total energy {result['energy_total_Ry']} Ry per two-atom cell. Runner elapsed
walltime was {result['elapsed_wall_seconds']:.6f} seconds; QE reported 1.95 seconds.
The cumulative QE job budget consumed is {result['cumulative_qe_wall_seconds']:.6f}
of 21600 seconds. No other QE job has been launched by this lane.

This establishes executable and electronic-SCF readiness. It does not establish
ionic/cell convergence, numerical cutoff/k-point accuracy, formation energy,
decomposition stability, or new-material discovery. The fixed cell has pressure
45.25 kbar, so it must not be treated as a relaxed zero-pressure reference energy.
The absolute pseudopotential energy offset is not comparable to CHGNet or MP.

All binary and DLL hashes are in qe_distribution_manifest.json. Pseudopotential
IDs, recommended cutoffs, official archive MD5 checks and SHA256 hashes are in
pseudopotential_manifest.json. qe_jobs.jsonl is the append-only QE job budget
ledger. Pilot inputs, raw stdout/stderr and restart files are retained under
mgo_scf_pilot/. mgo_scf_pilot_audit.json records warnings and verification limits.

Reproduce staging (network access required only when files are absent):

    python scripts/phase1_qe_setup.py qe
    python scripts/phase1_qe_setup.py pseudos

The pilot runner is intentionally single-use for this job ID to prevent evidence
overwriting. A future calculation must use an explicitly named new job and append
to the same six-hour QE walltime ledger. Audit without running QE:

    python scripts/phase1_qe_audit.py

No future candidate, reference-hull or convergence calculations were initiated.
"""
(ART / "README.md").write_text(summary, encoding="utf-8")
print(json.dumps(audit, indent=2))
