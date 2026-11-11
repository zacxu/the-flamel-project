# Phase 1 execution report

**Phase 1 is complete; proceed to Phase 2.** This report records executed local pilots, rather than proposed timings. Audit timestamp: 2026-10-21T16:42:25.736270+00:00. Phase 1 began at 2026-10-22 00:24:44 Singapore time. No predictor training, acquisition replay, new-composition search or candidate DFT stability validation was performed.

## Results against the exit criteria

| Requirement | Executed result |
|---|---|
| Isolated environments | Workspace Python 3.11.14; separate `.envs/generator` and `.envs/analysis`; both dependency checks pass; exact package freezes retained |
| Hardware | 12th Gen Intel(R) Core(TM) i5-12600; 12 logical processors; 31.74 GiB RAM; NVIDIA GeForce RTX 3060 Ti, 8192 MiB, 6925 MiB, 610.88 |
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

CrystalFormer ran on four logical CPUs. First batch of four: **28.903s**, including compilation; second same-shape batch: **9.486s**, or **2.371s per attempted structure**. Full model initialization, sampling and conversion took **55.423s**. The two batches do not separately isolate pure compiler time, and changing formula/space group has not been benchmarked. At this throughput, a further 72 same-shape attempts would require about 2.8 minutes of sampling, excluding new compilation and setup; this is a forecast, not an executed result.

CHGNet used FIRE with unconstrained positions/cell, FrechetCellFilter, at most 200 steps and filter fmax <=0.05 eV/A. The eight-atom structure has deterministic small displacement and anisotropic strain; these are known-reference engineering controls, not generated research samples or additions to the symmetry comparison.

| Device | Initial structure | Atoms | Steps | Relaxation s | Entire subprocess s | Final filter fmax eV/A | Final eV/atom |
|---|---|---:|---:|---:|---:|---:|---:|
| cpu | primitive | 2 | 4 | 0.290 | 5.549 | 0.02507 | -6.313887 |
| cuda | primitive | 2 | 4 | 0.561 | 5.563 | 0.02509 | -6.313888 |
| cpu | perturbed conventional | 8 | 19 | 1.565 | 6.171 | 0.04388 | -6.313824 |
| cuda | perturbed conventional | 8 | 19 | 1.210 | 5.895 | 0.04388 | -6.313826 |

The total energy in CHGNet trajectories is divided by actual atom count. Model-predicted energies are not fresh DFT. CPU and GPU results are comparable within numerical precision. Peak allocated CUDA tensor memory across these tiny pilots was 133.8 MiB; this is not a memory estimate for all future structures.

Freeze generator affinity at four logical CPUs, CHGNet on CUDA with two CPU threads, and one QE process at a time using four OpenMP/MKL threads (OpenBLAS one). Avoid additional concurrent numerical jobs that oversubscribe the 12 logical processors.

## QE readiness and its limits

The executed MgO input uses a 4.21 A rocksalt conventional lattice represented by a two-atom primitive cell; SSSP1.3.0 PBE PAW Mg/O pseudopotentials; ecutwfc=50 Ry, ecutrho=400 Ry; 4x4x4 unshifted mesh; nonmagnetic fixed occupations; conv_thr=1e-8 Ry. The job took **2.104s** (entire process), exited zero, reported SCF convergence and JOB DONE, and produced **-75.53578926 Ry** total energy. Input, pseudopotentials, executable and output are hashed.

This pilot is a known-phase, fixed-geometry electronic calculation. Its pressure is **45.25 kbar = 4.525 GPa**; it is not a relaxed zero-pressure reference. Cutoff/k-mesh convergence, candidate/reference ionic and cell relaxation, reference completeness and novelty checks remain later work. Absolute QE energy offsets must not be compared with CHGNet/MP/VASP values. A two-atom SCF timing does not establish the cost of magnetic, metallic or larger-cell relaxation jobs. QE's internal RAM estimate is not measured OS peak RSS; its Windows available-memory message is not a valid host-memory reading.

## Attempts, failures and remaining scope

| Budget | Charged so far | Remaining |
|---|---:|---:|
| Generation, 128 attempts | 8 | 120 |
| CHGNet, 40 launches | 8 | 32 |
| CHGNet, 14,400 cumulative seconds | 23.863 | 14376.137 |
| QE, 21,600 cumulative seconds | 2.104 | 21597.896 |

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
