# Website CI implementation

This is the Website CI portion of publication Phase 6. Hosted acceptance is recorded by the parent Phase 6 completion report; the results below are a real local reproduction against the independently verified Phase 5 clone.

## Workflow

The separate .github/workflows/website-ci.yml runs on website, publication tooling, Phase 6 policy, or Phase 4 runtime-specification changes in pushes to main and pull requests. Manual dispatch is also supported. It uses Windows 2025, read-only contents permission, an immutable checkout action revision, no persisted Git credential and no hosting credentials.

The source verifier runs before the website work and again with always() afterward. All existing historical validators run in a new external source export made from the exact selected Git HEAD. Their dated reports are replaced only in that disposable copy. The original Git checkout must remain clean, with the same commit.

The helper scripts reject existing audit/parser destinations, source-contained destinations and reparse paths. Git archive accepts only a source tree containing regular file modes. The temporary export tar is removed after successful extraction; the project and previous recovery data are not cleaned.

## Exact tool and dependency choices

- Node 24.22.1 and npm 12.2.1 use the existing standalone website installer, pinned upstream archive integrity and all 1,942 installed npm file checks.
- package-lock.json is installed with npm ci, lifecycle scripts disabled and isolated npm configuration. TypeScript checking and the production build run using the pinned executable.
- The existing Phase 4 hash-pinned standalone CPython 3.11.14 and uv 0.13.7 bootstrap is reused. GitHub's official Python version manifest provides Windows 3.11.9 rather than 3.11.14, so this workflow does not silently downgrade the tested runtime.
- website-parsers-lock.txt contains the 40-package nonoptional transitive dependency closure of NumPy and pymatgen, copied exactly from the tested Phase 4 maintenance lock. The same pinned build constraints are used. NumPy 2.2.6 and pymatgen 2025.10.7 independently parse saved cells/CIFs.
- Dependency consistency and parser imports are checked. Absence of torch, CHGNet, JAX and JAXlib is asserted. No generator, model checkpoint, research archive or DFT backend is installed or run.

pymatgen declares plotting, tabular and HTTP libraries among its base dependencies; these account for the parser closure's size. This is a parser environment, not the complete analysis-maintenance environment.

## Actual command coverage

The existing installer executes typecheck and build, then w6:integration -- --run, w6:tour, verify-short-urls.mjs, verify-orientation.mjs and deployment/latest-link/test.mjs. Integration reruns all eleven existing saved-source validators: research export, loader, data guards, state, replay, playback, saved crystal/CIF geometry, viewer, generation, uncertainty and evidence.

The new helper additionally runs w6:downloads. That command compares seven retained actual browser-download files with current export projection logic. It does not open a new browser session. The workflow separately runs the nine existing Windows Python installer guards; those guards start no scientific installation or model.

Any nonzero child command or failed validation stops the workflow. A successful receipt requires the saved-source integration, tour and retained-download reports to report passed.

## Measured local verification

A clean independent clone at commit f592e0c13888bfc62ff55413c91dc0721b6b35cb was exported into D:/Backups/TheFlamelProject/phase6-20261111-ci/website-local. The helper downloaded and verified new standalone tools, installed the exact parser and frontend dependencies, built the application and passed the complete sequence.

| Check | Measured result |
| --- | --- |
| Parser dependency resolution and consistency | 40 packages; PASS |
| Parser imports and excluded model packages | PASS |
| Strict TypeScript check and production build | PASS |
| W6 integration | 384 integration checks; 224,507 saved-source regression assertions across 11 reports |
| Guided tour | 123 checks; six steps, 25 subscenes, 180 seconds |
| Compact/legacy URL equivalence | 76,491 checks |
| Crystal orientation | 330 checks across 26 saved stages |
| Publication guard | 11 adversarial filesystem scenarios |
| Retained download projections | Seven files; 34 checks |
| Existing Windows Python installer guards | Nine tests |
| New destination protection checks | Four expected rejections, preserving source/existing destinations |
| Original independent clone | Same commit and clean working tree after all checks |

Local evidence is sealed in WEBSITE_LOCAL_CHECKS.json and WEBSITE_HELPER_GUARDS.json under the Phase 6 audit directory. The local helper's initial summary used the tour's nonexistent checksPassed field; the actual successful report has checkCount=123. The current helper uses checkCount. The external local summary explicitly records this receipt-only correction and hashes the original reports. Regression commands did not change.

Assertion totals include repeated verification contexts and are not independent scientific observations. These checks do not establish a fresh native-browser session, accessibility acceptance, new scientific calculations, new materials or live hosting acceptance. The existing InfinityFree website remains deployed independently of this CI implementation.
