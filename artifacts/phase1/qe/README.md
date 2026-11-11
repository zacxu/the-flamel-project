# Phase 1 QE lane: passed known-phase SCF smoke test

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

The run converged in 13 SCF iterations, exit code zero,
with JOB DONE, final residual bound 7.7e-11 Ry,
and total energy -75.53578926 Ry per two-atom cell. Runner elapsed
walltime was 2.103913 seconds; QE reported 1.95 seconds.
The cumulative QE job budget consumed is 2.103913
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
