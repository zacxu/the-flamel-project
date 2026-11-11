# Phase 3 native Quantum ESPRESSO evidence

The frozen known-MgO fallback completed a genuine PBE variable-cell DFT relaxation and recovered the rock-salt MgO reference. This is a numerically indistinguishable known-control recovery, not a new material or stability discovery. The eight primary CaMg2O3 generation attempts produced zero structures meeting the frozen exact-six-atom rule, so no primary-composition candidate reached DFT.

The authoritative machine-readable files are `summary.json` and `audit.json`. Every job directory retains its input, settings, stage provenance, pseudopotentials, stdout/stderr, XML, final geometry, result, and post-job budget snapshot. All 14 Phase 3 QE subprocesses completed, with no active QE reservation or mutex remaining.

| Accepted geometry | Cell retained | Energy (eV/atom) | Max force norm (eV/angstrom) | Max full-stress component (kbar) |
|---|---:|---:|---:|---:|
| `p3_ref_mgo_90_k035_cont1` | 2 atoms | -513.8780439713 | 0.000003593 | 0.037025 |
| `p3_candidate_mgo_fallback_90` | 8 atoms | -513.8780495046 | 0.000009863 | 0.042641 |

Both accepted runs satisfy electronic residual <=1e-8 Ry, final ionic convergence, max force-vector norm <=0.0205688269904 eV/angstrom, max absolute component of the complete residual stress tensor <=0.5 kbar, and absolute scalar pressure <=0.5 kbar. The final rebuilt-cell SCF is included. The earlier `p3_ref_mgo_90_k035` run passed QE's ionic flag but failed the independent full-stress criterion (0.7332 kbar); it is retained and was continued with a stricter internal pressure threshold. It is not an accepted final reference.

Final settings are identical PBE pseudopotentials and 90/720 Ry wavefunction/charge-density cutoffs, with reciprocal-grid spacing target 0.35 inverse angstrom. The original reference and candidate cells remain 2 and 8 atoms, respectively. Their final meshes are 8x8x8 and 5x5x5 because comparable reciprocal spacing, rather than the same integer mesh, is used. All relaxations use `nosym` and `noinv` without imposing a space group. A separate symmetry-breaking perturbation or phonon calculation was not performed.

At each accepted final geometry, the cutoff probe uses 75/600 Ry with the accepted dense mesh, and the k-point probe uses 90/720 Ry with spacing 0.45 inverse angstrom. All four probes converge electronically and change the energy by less than the frozen 5 meV/atom threshold:

| Final-geometry sensitivity | Reference (meV/atom) | Candidate (meV/atom) |
|---|---:|---:|
| 75 -> 90 Ry, dense mesh | 0.933869 | 0.931629 |
| 0.45 -> 0.35 reciprocal spacing, 90 Ry | 0.191407 | 0.033909 |

Stationarity is required at the accepted 90/720 Ry setting. Some lower-cutoff probe stresses exceed the relaxation criterion; those are fixed-geometry sensitivity measurements, not accepted relaxed structures. These finite cutoff/k tests establish the declared numerical acceptance criteria, not a rigorous energy error bound.

The raw candidate-minus-reference difference is -0.005533 meV/atom, far smaller than the measured numerical sensitivity. It supplies no evidence of a lower-energy phase. Primitive/supercell-aware StructureMatcher comparison passes with `scale=False`, `ltol=0.01`, `stol=0.01`, and angle tolerance 0.5 degrees; both final structures have space group 225 at symmetry tolerance 0.01 angstrom. Matching does not alter either execution cell.

Four CPU threads and one native QE process were used per job. Phase 3 charged 1205.0889291 seconds (20.08 minutes), within the initial 2700-second phase allocation. Including the Phase 1 fixed-cell pilot, cumulative QE walltime is 1207.1928419 seconds, within the 21600-second total ceiling. The legacy JSONL and canonical budget ledger agree, and the audit verifies all completed input, geometry, executable, output, settings, and pseudopotential hashes. Davidson eigenvalue warnings remain in the raw logs; acceptance requires the final electronic residual and XML/stdout checks, which pass.

No Materials Project energies are combined with QE energies. CaO has a completed starting-setting relaxation, but its final cutoff/k convergence remains pending and it does not enter the known-MgO comparison. No elemental metal, O2, complete decomposition hull, vibrational free energy, or fresh new-stable-material result is established. The Phase 3 wrapper rejects unsupported chemistries, pure elements, inherited spin-review jobs, and metallic occupations before dispatch.

Read-only refresh commands:

```powershell
& '.envs/analysis/Scripts/python.exe' -W ignore::FutureWarning scripts/phase3_qe_summary.py
& '.envs/analysis/Scripts/python.exe' -W ignore::FutureWarning scripts/phase3_qe_audit.py
```

The summaries regenerate JSON only; they do not dispatch QE or rewrite final geometries. Reproduction of calculations requires new unique job IDs and the canonical budget API, rather than overwriting these attempts.
