# Phase 5 bounded QE lane

**Outcome:** the single 900-second attempt ended at QE's internal time limit
during its ninth SCF call, after eight completed SCF calls and seven BFGS steps.
Terminal electronic/ionic convergence and final force/stress output were
unavailable. The driver correctly dispatched neither a continuation nor final
geometry probes. This additional robustness check remains incomplete; it does
not change the previously accepted unperturbed MgO result. Charged walltime is
900.4385138 seconds. The saved-evidence audit passed 52 integrity checks.

This lane implements the Phase 2 numerical protocol's optional deterministic
perturbation check on the **already validated known MgO control**. It does not
replace the empty CrystalFormer new-composition shortlist and does not promote a
prototype baseline into the candidate DFT queue.

The saved eight-atom Phase 3 MgO geometry is perturbed once using seed `260022`:
each atomic displacement has length 0.01 A; a symmetric cell strain has maximum
absolute principal value 0.005. The exact vectors, strain and source checksums
are in [the perturbation manifest](perturbation/manifest.json). At a 0.001 A
symmetry tolerance, the perturbation changes space group 225 to 1. This derivative
geometry is a numerical validation probe of an existing candidate, not a new
generation attempt.

[The queue](queue_plan.json) was frozen before dispatch. All jobs retain PBE,
identical Mg/O pseudopotentials, fixed occupations, `nosym`/`noinv`, one MPI
process and four threads. The relaxation uses 90/720 Ry cutoffs, reciprocal
spacing 0.35 inverse A and all atomic/cell degrees of freedom. One same-setting
continuation is allowed only after an accepted SCF result fails independent
stationarity. Electronic/process failure ends the queue. At an accepted final
geometry, 75/600 Ry and spacing 0.45 probes test finite cutoff/k sensitivity.

External acceptance requires an electronic residual at most 1e-8 Ry, maximum
atomic force vector norm at most 0.0205688269904 eV/A, absolute pressure and every
stress component at most 0.5 kbar, and each finite sensitivity energy shift at most
5 meV/atom. Merely reaching QE's ionic-convergence flag is insufficient. The
internal pressure target is 0.1 kbar. The predeclared watchdogs total at most
2,520 seconds and remain subject to the 3,600-second Phase 5 lane cap, global
six-hour QE cap and numerical stop. Every attempt is charged before dispatch and
its entire process walltime is retained in both ledgers.

The comparator reuses Phase 3's strict, unscaled structural-matching tolerances
and 10 meV/atom interpretation tolerance, fixed before the Phase 5 outcome in
[the comparison protocol](comparison_protocol.json). Raw differences below that
resolution do not establish an energy advantage. A single perturbation recovery
does not prove a local minimum, phonon stability, full-inventory hull stability
or experimental synthesizability.

Executed source snapshots are preserved under `executed_sources/`. The final
read-only audit reparses the saved XML/stdout, reproduces the perturbation and
checks geometry/settings/pseudopotential/executable hashes and budget ledgers:

```powershell
.envs/analysis/Scripts/python.exe scripts/phase5_qe_audit.py
```

Final outcomes are recorded in `summary.json`, `audit.json` and, when final
geometry probes completed, `known_control_perturbation_comparison.json`.
