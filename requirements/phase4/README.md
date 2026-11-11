# Python environments for portable installation

These are new Windows x64 specifications. Historical requirements/analysis-lock.txt and generator-lock.txt remain unchanged.

| Profile | Packages and role | Validation |
| --- | --- | --- |
| analysis-historical | Exactly the original 51 package versions, including torch 2.6.0+cu124 and filelock 3.32.3 | Historical reproduction only. Known advisories remain; no checkpoint is loaded in this profile's check. |
| generator-historical | Original 60 registry versions plus the unmodified CrystalFormer 0.6 source at revision 31bb734a3fd006af49a021921839061e6184cbf1 | Native Windows JAX uses CPU. |
| analysis-maintenance-cpu | The analysis pins with torch 2.15.0+cpu, filelock 4.2.10, sympy 1.14.0 and its required setuptools 84.2.1 runtime dependency: 52 packages | Separate compatibility-tested CPU maintenance environment for current evidence tooling. Does not replace historical results. |

Each plain profile file records the intended exact versions. Each corresponding -lock.txt includes hashes generated with uv 0.9.7 for Windows CPython 3.11.14. The torch wheels use direct official URLs with SHA-256 pins; other packages use only https://pypi.org/simple with first-index behavior. No unsafe-best-match multi-index resolution is used. build-tools-lock.txt separately pins the isolated build requirements; they are not silently added to the scientific environments.

## Install

Prerequisites are Windows x64, PowerShell 5.1 or later, built-in tar.exe and internet access. The tested machine has the Microsoft Visual C++ x64 runtime (vcruntime140, vcruntime140_1 and msvcp140 version14.50.35719.0), which native scientific wheels may require. On a machine lacking those DLLs, install the supported x64 runtime using [Microsoft's official instructions](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). The script does not install a global C++ runtime. No existing Python environment, machine Python installation or Codex executable is required. The installer bootstrap uses uv 0.13.7, separately queried in OSV with zero matching records. The historical uv 0.9.7 used to generate these fixed locks has three advisory groups (four aliased records) and is not used by this installer. Lock-generation provenance is retained; installation uses the updated tool. The script verifies the uv wheel and extracts its exact executable, verifies the Python standalone archive and executable, then creates all environments outside the checkout. Nothing is registered globally.

From the repository root:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/install_python.ps1 -Destination 'D:\FlamelRuntime' -Environment analysis-maintenance-cpu
~~~

To reproduce both historical environments and the separate maintenance environment:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/install_python.ps1 -Destination 'D:\FlamelAllEnvironments' -Environment all
~~~

The destination must be new and outside the source checkout. An optional -CacheDirectory selects an external download/build cache; packages still require their declared hashes. The script rejects reparse ancestors and existing destinations, temporarily isolates UV/PIP configuration, restores process environment settings, and copies only the 86 hash-checked public CrystalFormer originals before a generator build. It does not run old setup scripts, finalizers, training, relaxation or DFT.

The resulting executable is:

~~~text
<Destination>\envs\<profile>\Scripts\python.exe
~~~

For example:

~~~powershell
$env:FLAMEL_PYTHON = 'D:\FlamelRuntime\envs\analysis-maintenance-cpu\Scripts\python.exe'
~~~

The installer writes INSTALLATION.json, each environment's verification JSON and private command logs under its destination. It runs uv pip check plus exact installed-version checks and small numerical/import checks. The maintenance check loads only the CHGNet 0.3.0 checkpoint distributed in the fresh pinned CHGNet 0.4.2 package after verifying both its installed RECORD SHA-256 and the fixed model SHA-256 d14ab7c0f093efe64b60a7bcd540bca10e74fb7f46c86108a079af60524659d1. It does not perform inference or relaxation and never loads arbitrary research pickle/joblib data. Generator checks include a small JAX CPU array operation and exact SHA-256 matches for both installed Wyckoff CSV resources.

## Scope of the maintenance decision

The old torch/filelock pins have 31 recorded advisory groups in the Phase 3 report. They are preserved for provenance rather than relabelled safe. The maintenance profile uses current patched versions and a CPU backend so it makes no new claim about CUDA driver compatibility. sympy and setuptools changes satisfy the new torch metadata; the remaining analysis versions stay fixed.

A fresh OSV query of all 52 installed maintenance distributions and the 60 generator registry pins returned no matching vulnerability records across 77 distinct package/version queries on 11 November 2026. Local CrystalFormer source is not covered by a PyPI advisory query. This is time-scoped database coverage, not proof of complete security or a guarantee that every future dependency remains safe.

The historical CUDA environment detected CUDA 12.4 and an available device on the tested machine; that alone does not establish compatibility on another GPU or validate all kernels. The generator uses JAX CPU on native Windows. Linux/WSL, GPU JAX, a patched CUDA maintenance profile and new scientific outcomes were not tested.

Routine website CI should use the separate maintenance Python only where research/crystal validators need its packages. It must not automatically execute historical research scripts. New experiments require a separate output directory, the recorded scientific gates/budgets, trusted hash-verified model inputs, and explicit validation appropriate to the changed environment. Use the repository's current installation guide for scoped public artifact retrieval and saved-evidence auditing.
