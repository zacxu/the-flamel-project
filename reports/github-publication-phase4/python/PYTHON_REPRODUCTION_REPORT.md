# Phase 4 Python reproduction and maintenance decision

Status: COMPLETE. Tested 11 November 2026 on Windows x64 in a clean byte-verified source export. The GitHub remote is still empty; this is a clean source-export test, not a claim of a remote clone.

The final exported PowerShell installer completed all three profiles in a new external destination. It downloads and verifies the standalone Python 3.11.14 archive and uv wheel/executable and uses no installed Python environment or Codex executable. It installs hash-locked packages from PyPI with first-index resolution and checksum-pinned official PyTorch wheel URLs. The final run reused a verified external package cache; the environment directories and bootstrap downloads were new.

| Profile | Exact installed distributions | Result |
| --- | ---: | --- |
| analysis-historical | 51 | Original versions; pip check, imports and simple tensor/structure checks passed. torch 2.6.0+cu124 detected CUDA 12.4/device availability; no checkpoint loaded here. |
| generator-historical | 61 | Original 60 registry pins plus unchanged CrystalFormer 0.6; pip check, JAX CPU array operation and imports passed. Both installed Wyckoff CSVs match the pinned original source hashes. |
| analysis-maintenance-cpu | 52 | Separate patched CPU environment: torch 2.15.0+cpu, filelock 4.2.10, sympy 1.14.0, plus torch's required setuptools 84.2.1. Remaining 48 analysis pins unchanged. Pip check, imports and trusted CHGNet checkpoint load passed. |

The maintenance check verifies the fresh CHGNet 0.4.2 package's checkpoint RECORD and the fixed model SHA256 d14ab7c0f093efe64b60a7bcd540bca10e74fb7f46c86108a079af60524659d1 before loading model 0.3.0 on CPU. It performs no inference, relaxation, training or DFT. Arbitrary pickle/joblib inputs are not loaded.

The original analysis/generator locks, old setup script and Phase 3 portable generator specification remain byte-identical. New specifications and the bootstrap decision are under requirements/phase4; root installer/helper/test files are new. Nine focused guards passed, including source/destination/report overwrite rejection and rejection of arbitrary model bytes even with matching local RECORD metadata.

## Security decision and tool update

The old torch/filelock analysis pins retain 31 recorded advisory groups and are preserved only for historical reproduction. The separate maintenance environment uses patched versions. A fresh OSV batch for all 52 maintenance distributions and 60 generator registry pins returned zero records across 77 distinct package/version queries, with no pagination. The final installed versions match the queried versions exactly. The local CrystalFormer source is outside this registry query. These results are time-scoped database coverage, not a full-security guarantee.

The additional bootstrap audit found four OSV records representing three advisory groups in uv 0.9.7: [entry point path writes](https://github.com/astral-sh/uv/security/advisories/GHSA-4gg8-gxpx-9rph), [RECORD path deletion](https://github.com/astral-sh/uv/security/advisories/GHSA-pjjw-68hj-v9mw), and [the emSign root removal](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62). The final installer instead uses checksum-verified uv 0.13.7, which returned zero OSV matches in its separate query. The old tool remains only as recorded hash-lock-generation provenance and in superseded audit records. Final installation with the patched tool was actually rerun for all three profiles.

Underlying advisory records and original Phase 3 findings are preserved. No exploit was observed or tested. The Python 3.11.14 runtime remains pinned for reproduction and is not included in the PyPI package-advisory query; do not call the whole operating-system/runtime stack security-clean.

## Paths and repeatability

- Tested export: ../source
- Authoritative installer receipt: final-installer-validation/INSTALLATION.json
- Final working profiles: final-installer-validation/envs/<profile>/Scripts/python.exe
- Full summary with every new source hash: PYTHON_COMPLETION.json
- Registry query/request/response: OSV_MAINTENANCE_GENERATOR_SUMMARY.json and osv-maintenance-generator-*.json
- Separate bootstrap checks: osv-bootstrap-uv.json and osv-bootstrap-uv-maintenance.json
- Final generator resources: final-installer-validation/generator-final-resources-verification.json
- Focused guard receipt: PYTHON_GUARD_TESTS.json
- Native prerequisites: native-runtime-prerequisites.json
- Redundant-copy/cache cleanup: PYTHON_CLEANUP.json; final environments are retained.

Use requirements/phase4/README.md and scripts/github_publication/install_python.ps1 from the repository. Its destination must be new and outside the checkout. The native Microsoft Visual C++ x64 runtime was already present on the tested machine; no global runtime, registry or machine Python installation was changed.

The fresh standalone runtime also passed the new read-only saved-evidence auditor from the export: 103 bound inputs, 4 freeze hashes and 75 public payloads, with no model deserialization or recomputed experiments. Its separate receipt is ../SAVED_EVIDENCE_CLEAN.json.

No new scientific results, GPU performance claim, Linux/WSL compatibility, patched CUDA maintenance profile, Git staging/push or deployment is established by this phase.
