# Python environment and security decision

The frozen scientific results retain their historical package versions. The publication installation work adds separate reproducible profiles; it does not relabel those results as having been obtained with newer dependencies.

## Tested profiles

| Profile | Exact installed distributions | Role |
| --- | ---: | --- |
| analysis-historical | 51 | Historical analysis/CUDA 12.4 stack, including torch 2.6.0+cu124 and filelock 3.32.3 |
| generator-historical | 61 | Original 60 registry pins plus CrystalFormer 0.6 from the exact retained vendor revision |
| analysis-maintenance-cpu | 52 | Separate CPU tooling/research compatibility profile with the changes below |

The maintenance profile changes torch to 2.15.0+cpu, filelock to 4.2.10 and sympy to 1.14.0. It adds setuptools 84.2.1 because the newer torch metadata requires it. Other analysis versions retain their original pins. The specifications and hash locks are under requirements/phase4. The historical requirements files remain unchanged.

The generator installs only the 86 public, hash-checked upstream original files at CrystalFormer revision 31bb734a3fd006af49a021921839061e6184cbf1. Its private MCP .env and generated build copies are not used. Source is copied to the new installation target before building so installation never writes egg-info/build output into the source checkout. This avoids the former absolute C: reference.

## Security disposition

Phase 3 recorded 31 alias-deduplicated advisory groups affecting the historical torch/filelock versions. That evidence remains visible and unchanged in reports/github-publication-phase3/dependencies. Historical profiles preserve those versions for reproduction and are not the default for new research execution.

The Phase 4 default is the separate maintenance CPU environment. A fresh OSV query covered its 52 installed distributions and the generator registry pins, giving 77 distinct package/version queries after overlap. It returned HTTP 200, no pagination and zero matching vulnerability records. Local CrystalFormer source is separately pinned/reviewed and is not represented as a registry advisory query.

This is a dated advisory-database result, not proof of absence of vulnerabilities. It does not establish that all possible code paths are safe, that every source distribution has been audited or that CPU/GPU results are numerically equivalent.

The installer pins uv 0.13.7 after its separate OSV query returned zero records. The earlier uv 0.9.7 lock-generation tool had three alias-deduplicated advisory groups; its provenance is retained and it is not the installation bootstrap. The installer uses SHA-pinned uv and standalone Python, hash-pinned package specifications, explicit official torch wheel URLs, PyPI's first-index policy and pinned build constraints. It clears inherited pip/uv configuration, disables keyring lookup and keeps cache/runtime destinations outside the checkout. Source-build and locally built vendor components are recorded separately; a source hash is not a claim that every resulting binary is reproducibly compiled.

## What compatibility checks establish

Fresh environments passed dependency checks and exact installed-version comparisons. Smoke checks cover the base scientific/materials packages, simple array/tensor operations and JAX's CPU backend. Historical CUDA availability is a local driver/runtime observation, not a throughput or new-material result.

The maintenance profile additionally loads CHGNet model 0.3.0 on CPU from the fresh official CHGNet 0.4.2 distribution. The packaged checkpoint's SHA-256 is verified against the installed distribution's RECORD before loading. No model prediction, structure relaxation, training or DFT calculation is included in that check. Arbitrary external pickle/joblib/checkpoint files are not loaded by the asset verification or saved-evidence commands.

No fresh generation or experiment is needed to install/view the website or validate its recorded evidence. Use the maintenance profile for parsing and compatibility work. A future GPU maintenance profile or new study needs its own tested environment, study directory and numerical protocol; the original budget ledger and freeze remain unchanged.

## Platform and reproduction limits

These installers are validated on Windows x64 with standalone CPython 3.11.14. The native Windows generator uses JAX CPU. Linux, macOS, WSL GPU JAX and an updated CUDA analysis stack are not claimed tested.

The clean source export is an exact-byte stand-in for the future clone while the remote remains empty. The full end-to-end installer is run from that separate source location using only declared toolchains/downloads. Actual GitHub clone and release-hosted retrieval are later publication checks.

Existing environments are never upgraded in place. Each Python installation destination must be new; select all profiles in one invocation or use separate destinations. The installed environments are disposable and recreated at their target paths.
