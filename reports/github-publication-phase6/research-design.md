# Research CI design and local verification

Research CI runs actual acquisition, budget, optional-work gate, composition
and streaming parser code against synthetic inputs in temporary directories.
It preserves the recorded experiment rather than rerunning it.

| Area | Tests | Behavior checked |
|---|---:|---|
| Acquisition and calibration | 9 | Energy ordering and stable ID ties; uncertainty exploration; seven conservative plus three optimistic choices; seeded sampling without replacement; within-batch diversity updates; bounded fresh pair; quantile/floor; initial-training normalization; invalid arrays rejected |
| Atomic budget reservations | 9 | Attempts charged before dispatch and retained after failure; attempt ceiling; in-flight watchdog reservations; walltime ceiling; one active QE job; duplicate finish/job rejection; category cap; numerical stop/invalid requests; missing baseline |
| Composition-stretch gates | 3 | Each of six prerequisites independently disables optional work; all prerequisites require an explicit bounded plan; prior decision never overwritten |
| Composition rules and streamed catalog JSON | 6 | Fraction/repeated-element normalization; invalid formulas rejected; deterministic bounded charge-balanced enumeration; one-byte numeric read boundaries; column filtering without object decoding; truncated/trailing input rejected |

The suite uses original functions from research_acquisition.py,
research_budget.py, scripts/phase4_gates.py,
scripts/phase2_formula_rules.py and scripts/phase2_json_columns.py. Budget
and gate module paths are redirected to per-test temporary directories before
calling any function that writes. The clock is fixed in synthetic fixtures;
the historical numerical deadline remains unchanged.

The only third-party test dependency is numpy==2.2.6. Its exact requirement
and SHA-256 wheel hashes are copied from the frozen
requirements/phase4/analysis-historical-lock.txt; the original lock stays
unchanged. CI installs with --require-hashes --no-deps --only-binary=:all:.
It does not install research environments, torch, CHGNet, pymatgen, JAX or QE,
download datasets/checkpoints, generate structures or dispatch calculations.
These tests cover acquisition and engineering safeguards, not geometry
relaxation, scientific model accuracy or successful QE output parsing.

The workflow runs on Ubuntu 24.04 with Python 3.11.14. Pull requests and pushes
to main are filtered to research inputs and shared publication/CI safeguards;
manual dispatch is also available. Official checkout and setup-python actions
use immutable reviewed commit pins, contents permission is read-only and
checkout credentials are not persisted. The pinned actionlint runner validates
workflow syntax. Retained publication, artifact-rejection and saved-evidence
checks run alongside the new fixtures. All nine Windows Python-installer guard tests run in Website CI, because the legacy guards invoke Windows powershell; Linux Research CI does not run them.

Before and after the synthetic suite, SHA-256 snapshots compare every tracked
research source, configuration, artifact, dataset and requirement file. The
workflow also verifies the complete checkout and accepted browser/scientific
evidence before and after all checks. Reports and fixture outputs go to
RUNNER_TEMP, outside historical outputs.

A clean local test environment was created under
D:/Backups/TheFlamelProject/phase6-20261111-ci/research/numpy-only,
using the previously verified standalone CPython 3.11.14 runtime. Installation
downloaded and hash-verified only the NumPy 2.2.6 wheel. All **27 tests passed**;
**3,774 tracked research inputs** had identical before/after SHA-256 hashes.
The receipt and log are LOCAL_RESEARCH_CHECKS.json and
LOCAL_RESEARCH_CHECKS.log in that external research audit directory. An early
synthetic fixture accidentally reached the numerical deadline before the
walltime branch; its retained private receipt is INITIAL_FIXTURE_CHECKS.json.
The fixture now gives that case an isolated 100-second budget and tests
60-second plus 50-second reservation rejection. No scientific source changed.

This local result does not substitute for the hosted workflow result. The
phase-level completion record supplies the final GitHub run and source commit.

Nine additional standard-library policy fixtures exercise permitted current source paths and reject metadata that attempts to exempt frozen artifacts, data, configurations, dependencies, contracts, historical reports or vendor inputs. Withholding is rejected. The final preservation step runs with if: always(), including when an earlier check fails.

The nine policy tests passed locally against the implemented helpers. LOCAL_POLICY_CHECKS.json and LOCAL_POLICY_CHECKS.log in the external research audit directory bind this result to the exact test/verifier SHA-256 bytes. The verifier invokes the restrictive control policy before the generic overlay check.
