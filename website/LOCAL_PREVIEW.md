# Local production preview and presentation fallback

W1-W6 produce a checked local static release. W7 hosting remains planned. The exact UI build ID, export-manifest identity, payload/ZIP hashes and measured sizes are in the [local package record](reports/W6_RELEASE_PACKAGE.json) and [release verification](reports/W6_RELEASE_VALIDATION.json). The [QA report](QA_REPORT.md) records the actual production-browser rehearsal and verification limits.

## Run the checked production build

Open PowerShell in `C:\Users\Admin\Desktop\bears\website`:

```powershell
.\scripts\npm.ps1 run preview -- --port 4173
```

Open [http://127.0.0.1:4173/](http://127.0.0.1:4173/). Keep that PowerShell session open while presenting. Stop the foreground server with `Ctrl+C` when finished. If the port is already occupied, use another explicit local port and open that matching URL. Do not stop unrelated processes. No hosting authentication is needed for this local fallback.

The production preview serves `dist/`. Opening `dist/index.html` with `file://` does not provide the HTTP origin needed by JavaScript modules and data loading. The site loads its own recorded data, images and modules locally; upstream attribution links require the network if opened. Use the production preview for rehearsal, not only the development server.

## Rebuild, verify and package after an authorized source change

The existing checkout already has pinned dependencies. Reuse them. These commands do not rerun research or regenerate its frozen exports:

```powershell
.\scripts\npm.ps1 run w6:integration -- --run
.\scripts\npm.ps1 run w6:tour
.\scripts\npm.ps1 run build
.\scripts\npm.ps1 run w6:downloads
.\scripts\npm.ps1 run release:package
.\scripts\npm.ps1 run w6:release
.\scripts\npm.ps1 run w6:tooling
.\scripts\npm.ps1 run w6:integration -- --include-tooling
.\scripts\npm.ps1 run preview -- --port 4173
```

`build` prepares a deterministic source-bound UI build identity before strict TypeScript checks and the Vite production build. The study identity and immutable export-manifest hash remain separate. The image derivatives are already saved and checked lossless presentation assets; building does not alter the original scientific figures.

`w6:integration -- --run` runs eleven source/science/state/geometry/lifecycle validators and writes W6-specific reports. Individual lanes are `w6:state`, `w6:data-guards`, `w6:loader`, `w6:research`, `w6:replay`, `w6:playback`, `w6:crystal`, `w6:viewer`, `w6:generation`, `w6:uncertainty` and `w6:evidence`. `w6:downloads` checks retained native-browser files against their recorded selections; it does not itself perform fresh downloads. Run this check after `build` prepares the current UI identity. Recollect affected browser files after any change to their interactions, selection semantics, output or recorded build identity; a validator cannot substitute for fresh native-browser capture.

`w6:tooling` checks the existing production build and dependency tree. Run `build`, `release:package` and `w6:release` first: packaging adds two release-manifest/inventory files, so tooling must bind the fully packaged tree rather than the earlier build alone. It identifies whether its advisory evidence was a recorded audit or a live query. `release:package` writes a document-root-relative ZIP under `releases/<ui-build-id>/` and a versioned public file manifest under `dist/release-manifests/`. `w6:release` verifies file sizes/hashes/MIME, sensitive-content exclusions, the archive and local old/new release coexistence. Read its actual result; packaging alone is not acceptance or deployment. W6 commands preserve historical W1-W5 reports; invoking older phase-specific validation commands can replace their own historical reports.

## Thirteen-step fallback rehearsal

1. Start the production HTTP preview above and open it in a fresh browser tab. Confirm that Overview loads without an error notice. Compare the footer's UI build ID with the current local package record; the pinned data identity is recorded in the package and source metadata.
2. Select **Reset exploration**. Confirm the ordinary default: aggregate Quality versus Full, 50 historical queries, paused. Open **Start guided tour** using the keyboard and confirm focus moves to its Pause control.
3. Let one complete tour run for its actual **180 seconds**. The six timed sections below should appear in order, without starting research jobs. Caption and elapsed time describe the presentation, not compute progress.
4. Restart and use **Pause tour**. The selected scene and presentation time should hold. **Resume tour** continues; **Previous tour step** and **Next tour step** choose the exact initial preset of that step. Exit after checking those controls.
5. In ordinary browsing open Workflow and select its proposal, generation and screening nodes. Explain the separate historical acquisition track, empty new-formula transformer shortlist, known control and prototype baseline paths.
6. Open Replay, select an individual split and Quality/Full, then start at zero. Step the saved five ten-query boundaries; inspect a predictions-only batch before reveal. At zero queries precision is unavailable. Aggregate mode has no individual query history.
7. Finish at 50 queries and compare hits with chemical-system coverage. Quality retrieved more historical near-stable records in every paired split; Full reached broader chemistry. Five overlapping split means/SD are descriptive, not an independent confidence interval.
8. Open Crystal Lab's known-MgO sequence at the accepted DFT stage. Rotate with mouse or keyboard, inspect a physical site and reset the camera. Use the saved scientific figure if WebGL is unavailable; metadata, coordinates and CIF export remain available.
9. Select the six-atom CaMg₂O₃ prototype at its CHGNet-relaxed stage, then the excluded twelve-atom transformer example. Explain the distinct methods and exact-cell eligibility. Changing a displayed stage does not animate a measured scientific trajectory or invent a missing DFT result.
10. Open Findings and compare primary MgO/TiO₂ valid and unique yields. Keep the supplementary MgO denominator separate. Inspect the one-selected-structure-per-arm CHGNet energy pair and its scope; a model-energy contrast does not establish DFT stability or a symmetry-free architecture benefit.
11. In uncertainty controls select Full on splits 20261023 and 20261024 to show coverage below and above nominal 90%. Move retained fraction from 100% to 10%: 342 of 3,418 rows remain after rounding. Return to 100%. A selected subset's MAE does not improve all-population predictions.
12. Open Evidence. Reset QE filters to all nineteen jobs, then inspect the incomplete perturbation. Process completion differs from terminal SCF, stationarity and full finite checks. Reference coverage is 2/161 primary plus 1/57 fallback memberships; three accepted geometries correspond to two original source-reference IDs. No complete hull or new stable material was established.
13. Open and close a source drawer with Escape, download a displayed CSV and a saved-stage CIF, then exercise a deep-link reload and ordinary navigation. Exit any running tour and confirm browsing works. Stop the preview with `Ctrl+C` after rehearsal. If hosting fails during the event, present this already checked local HTTP build and state that live hosting is unavailable.

## Three-minute spoken sequence

| Time | View/preset | Point to say |
|---|---|---|
| 0:00-0:25 | Overview and workflow proposal/generation/screening | An integrated recorded prototype; historical acquisition and fresh structures are separate experiments. |
| 0:25-1:10 | Individual Quality/Full replay at 0, 10, 20, 30, 40, 50 queries; final five-split table | Equal historical label budgets reveal a trade-off: broader coverage, fewer near-stable hits. |
| 1:10-1:45 | Accepted known MgO; model-relaxed six-atom prototype; excluded twelve-atom draw | Real saved geometries have distinct method, eligibility and validation stages. |
| 1:45-2:15 | Primary MgO/TiO₂ yields and the separately scoped selected energy pair | Conditioning changed validity; unique yield and one-pair model energy require their own limits. |
| 2:15-2:40 | Full coverage on splits 20261023/20261024; 10% then 100% retention | Empirical calibration varies. Selective risk is a saved subset diagnostic. |
| 2:40-3:00 | All QE jobs, incomplete perturbation and methods/sources | Known recovery and partial validation are useful prototype evidence; no new stable material or complete hull was established. |

The [guided-tour contract](contracts/GUIDED_TOUR_CONTRACT.md) defines exact automatic presets and cancellation. Normal page controls, navigation, Sources, Glossary, reset, copy link or browser history exit the tour. Hiding a tab is intended to pause presentation; native hidden-page delivery is only claimed for environments actually exercised in the QA report. Reduced motion disables automatic crystal rotation and presentation animation. No physical touchscreen or unavailable browser is certified by a mobile viewport.

## Local package handoff and W7 boundary

Use the archive path recorded in `reports/W6_RELEASE_PACKAGE.json`; no hard-coded provisional build ID is required. The ZIP contains the contents of `dist/` with document-root-relative paths. Keep the package record outside the public upload. Do not upload this source folder, `node_modules`, scientific environments, model checkpoints or full research archives.

W7 still requires authenticated account inspection, exact domain/root/HTTPS verification, backup of existing files, new immutable assets/manifest first, entry HTML last, retention of predecessor immutable paths, fresh public-browser checks and a recoverable rollback record. The local cache-coherence fixture checks bytes served over loopback; it does not certify InfinityFree cache headers or a live deployment. Code repository, one-page account and video controls remain disabled until genuine public destinations are checked. The local website does not complete those hackathon deliverables.
