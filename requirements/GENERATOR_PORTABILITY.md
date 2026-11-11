# Portable generator installation specification

> **Current installer:** Phase 4 now provides tested, hash-pinned profiles in [phase4/README.md](phase4/README.md) and the [standalone installation guide](../INSTALLATION.md). The earlier minimal commands below describe the Phase 3 proposal; use the current installer for reproducible installation. The historical lock remains unchanged.


The original requirements/generator-lock.txt remains immutable historical evidence, including its old C: local file URL. requirements/generator-portable.txt contains exactly the same 60 registry pins, with only that absolute local CrystalFormer reference removed. It is an installation specification, not a claim that a new environment has passed Phase 4.

This preserves historical dependencies with known advisories; it is not a hardened maintenance environment. Review reports/github-publication-phase3/dependencies/DEPENDENCY_AUDIT_REPORT.md and implement a separate tested security decision in Phase 4 before future research execution. Do not automatically install or load research checkpoints in routine website CI.

From the project root in a separate Python 3.11.14 environment, install the registry packages, then install the retained vendor source without resolving dependencies again:

```powershell
python -m pip install -r requirements/generator-portable.txt
python -m pip install --no-deps ./vendor/CrystalFormer
python -m pip check
```

The retained source is pinned to CrystalFormer revision 31bb734a3fd006af49a021921839061e6184cbf1; its 86 selected original source files are byte-verified against the frozen input manifest. Relative vendor installation removes the machine-specific C: dependency and requires running the commands from the project root. No editable install or dependency upgrade is implied.

The recorded Windows generator uses jax==0.7.2 and jaxlib==0.7.2 on CPU. This specification does not promise JAX CUDA support on native Windows. GPU JAX would require a separately documented and validated Linux/WSL CUDA environment. The analysis lock has torch==2.6.0+cu124 and needs the PyTorch CUDA 12.4 wheel index used by scripts/setup_environments.ps1. A CPU PyTorch installation would be a different, separately validated environment and must not silently replace that frozen CUDA wheel. A 3060 can still serve the analysis workload; it does not imply every generator package uses its CUDA GPU.

Phase 4 must install in a fresh environment, record Python/package/backend versions, run pip check and minimal import/checkpoint tests, and record any pin or platform failure explicitly. Do not run old finalizers or scientific pilots as dependency checks. The current audit only compares specification pins and tests Git transport.

On Git for Windows, use `git -c core.longpaths=true clone <repository-url>` and repository-local `git config core.longpaths true` before staging these retained deployment sidecars. The audit encountered and then resolved an actual MAX_PATH failure in its longer external test directory. No global Git setting is changed. New shell scripts intended for Linux must be saved with LF deliberately; `* -text` preserves existing bytes instead of rewriting historical inputs. Linux execution has not been validated by this Windows-only Git audit.
