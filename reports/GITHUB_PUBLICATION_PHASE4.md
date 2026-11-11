# GitHub publication Phase 4

Status: COMPLETE. Date: 11 November 2026, Singapore. Project: D:/bears. Isolated reproduction evidence: D:/Backups/TheFlamelProject/phase4-20261111-reproduction.

## Result and scope

The standalone installation path separates the website, read-only saved-evidence verification, historical research environments and a maintenance CPU profile. The original environments, historical locks, scientific inputs/results and production website source are preserved.

A 5,200-file source export (310,824,522 bytes) matched the complete Phase 3 seal before testing. It contains no installed environments, caches, runtimes or node_modules. Installers and verification helpers are executed from that separate source location with declared tools and assets. This is a clean checkout-content test, not a claim that an actual GitHub clone was available before Phase 5.

Start with [INSTALLATION.md](../INSTALLATION.md). Detailed records are [Python specifications](../requirements/phase4/README.md), [environment/security decision](../publication/phase4/ENVIRONMENT_POLICY.md), [website setup](../publication/phase4/WEBSITE_INSTALLATION.md) and [asset retrieval](../publication/phase4/ASSETS.md).

## Requirement coverage

| Phase 4 requirement | Implementation and measured validation |
| --- | --- |
| Pinned Python environments | Separate hash-pinned historical analysis, historical generator and CPU maintenance profiles; fresh dependency/import checks |
| Dependency security decision | Historical findings retained; maintenance changes isolated; fresh advisory matching; updated installer bootstrap |
| Node and npm versions | Standalone Node 24.22.1 and npm 12.2.1 with pinned archive hashes |
| package-lock installation | npm ci with lifecycle scripts disabled; original manifest/lock hashes unchanged |
| External assets | Strict permitted selector, local archive verification/hydration, real upstream SSSP retrieval and exact UPF placement |
| Separate usage paths | Website-only build, standard-library saved-evidence check and explicit research environment profiles |
| No workstation/Codex dependency | Exported installers use downloaded/pinned tools; Python and Node runtime overrides are explicit |
| Preserved structure and evidence | Original project paths remain; writable checks/builds run in disposable copies; final checksum overlay records metadata changes |

## Python reproduction and security

The installer creates new environments outside the checkout. It bootstraps verified standalone Python 3.11.14 and uv without machine Python or Codex. Each destination must be new. The historical analysis profile has exactly 51 distributions; the generator has 60 registry pins plus the unchanged CrystalFormer 0.6 source. The former absolute C: generator URL is replaced only in the new specifications.

The separate maintenance CPU profile has 52 distributions. It changes torch to 2.15.0+cpu, filelock to 4.2.10 and sympy to 1.14.0, and adds required setuptools 84.2.1. Other analysis versions retain their pins. Fresh checks cover exact versions, dependency consistency, materials/data imports, simple array/tensor operations and JAX CPU. The trusted CHGNet 0.3.0 package checkpoint is hash-checked before CPU loading, with no inference or relaxation.

Phase 3's 31 historical torch/filelock advisory groups remain part of the record. A fresh OSV request covering the 52 maintenance distributions and generator registry pins returned zero matching records across 77 distinct versions. Local vendor source is separately pinned/reviewed. All three profiles passed the actual exported PowerShell installer using uv 0.13.7. The final generator resource check also verified both installed Wyckoff CSVs against original hashes. Nine installer/checkpoint/report guards passed. The bootstrap itself is separately audited: uv 0.9.7 retains historical lock-generation provenance; new installation uses uv 0.13.7 after an explicit current query. Advisory matching is dated database coverage, not proof of complete security.

The original requirements/analysis-lock.txt and generator-lock.txt remain byte-identical. New -lock.txt files contain package hashes; official torch wheel URLs are explicit and PyPI uses first-index resolution. Build constraints and vendor-source provenance are recorded. No original environment is upgraded in place.

Windows native prerequisites are explicit. The tested machine already has Microsoft Visual C++ x64 runtime 14.50.35719.0 and a usable CUDA driver; no system runtime/driver was installed or changed. The historical CUDA profile's availability check does not establish compatibility on another GPU. Maintenance is CPU; native Windows generator uses JAX CPU. Linux/macOS/WSL and a patched CUDA maintenance stack are not asserted tested.

## Website reproduction

The standalone installer verifies all 1,994 regular Node runtime files against the pinned 2,459-entry release ZIP and all 1,942 installed npm-tool files against the pinned npm archive. Child PATH/configuration excludes Codex and global Node/npm dependencies. Five positive/negative cache-integrity checks passed.

Clean npm ci, dependency tree, TypeScript and production build passed. All 86 application/public build files match the frozen archived bytes, with exact UI ID ui-w6-351e6182d7af3a9d062d and research release data-v1-2a138b7808f0d12c5151. The two release-packaging metadata files are not generated by a plain build; packaging remains later work.

A bounded local HTTP preview served all 86 files with status 200 and matching hashes, then terminated. Eleven W6 validators passed 224,507 source regressions and 384 integration checks; tour passed 123 checks, and all 11 publication-guard scenarios passed. Counts include repeated contexts, not independent scientific observations. Fresh npm audit returned zero reported advisories across 117 locked entries.

All 1,232 selected original website files remain unchanged. Existing reports were regenerated only in the disposable export. No native-browser session or live InfinityFree acceptance is claimed; no UI interaction changed in this phase.

## Assets and saved evidence

The public selector includes 11 permitted originals plus the mandatory notice ZIP: 12 archives, 907 members. All archive/member bytes passed verification. Fresh project hydration produced 777 files (4,149,045,899 bytes), independently rehashed. Production recovery plus notices produced 140 files (8,539,590 bytes); its standalone verifier passed 123 captured files and 75 research payloads offline.

The new tool performed one actual upstream HTTPS SSSP retrieval and verified its pinned archive and three canonical UPFs. Forty-one recorded raw input copies can be recreated exactly. Thirty-six QE-serialized scratch UPFs have different bytes and remain private; the tool never substitutes raw UPFs while claiming historical scratch recovery. Other scratch/restart history also remains private. All 34 asset safety tests passed.

The 14-archive historical private manifest remains unchanged. New public availability is still unpublished; its downloader rejects planned URLs before network access. Actual GitHub release downloads remain a later release acceptance check.

The standard-library audit_saved_evidence.py verifies 103 original source inputs, four frozen baseline hashes, 75 public payloads and the authenticity of saved audit/freeze/budget records. It reports the 3,587 historical checks as recorded, not newly re-executed. It loads no models and writes no source reports. It passes from the separate export with standalone Python. Eleven focused tamper/report-path tests passed.

## Integrity, cleanup and later work

The existing integrity gate is reused through verify_phase4.py with a separate baseline/declared-controls overlay. Phase 3 defaults are retained; its 25 tests pass 24 with one OS symlink-creation skip, while simulated reparse checks pass. The current selection contains 5,260 files, including 60 new Phase 4 files and 71 declared new/modified controls. The aggregate recovery-control set contains 147 files. Final Gitleaks scanning of all 5,260 selected files returned zero unresolved findings (only the 13 exact reviewed historical worker UUIDs); final Git policy checked all selected and 100,449 excluded paths, retaining only the eight reviewed vendor exceptions. The exact allowlist, control recovery copies and complete selected-file seal are refreshed independently of the frozen Phase 3 seal.

Verified redundant asset/runtime test copies are removed after their receipts and hashes are preserved. Retained source export, final standalone toolchains, measured build and declared local originals remain on D:. Cleanup receipts distinguish removed test paths from recovery data.

Root Git remains uninitialized. No staging, commit, push, release upload or hosting deployment occurs. No new training, generation, relaxation or DFT experiment runs. Phase 5 owns the first actual Git import and remote clone verification; release-hosted downloads and production acceptance remain later phases.

Current retained Python profiles are under D:/Backups/TheFlamelProject/phase4-20261111-reproduction/python/final-installer-validation/envs. Earlier paths in test receipts are historical measurements and may have been removed as verified redundant copies. See external cleanup receipts for exact retained/removed roles.
