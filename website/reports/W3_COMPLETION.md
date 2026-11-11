# W3 complete: recorded acquisition replay

Completed 22 October 2026. All seven core W3 tasks and their exit conditions are complete. W4-W7 remain planned. The website continues to use `data-v1-2a138b7808f0d12c5151`; no experiment, model inference, generation, relaxation or DFT run was performed.

The Replay view now compares five acquisition policies across five recorded splits or their aggregate. It starts at aggregate Quality versus Full with 50 completed queries. Visitors can select the visible policies independently of the policy whose batch they inspect, switch among hits/precision/chemical systems, and choose only 0/10/20/30/40/50 query boundaries. The chart and exact-value table agree and show no future boundaries before their reveal.

## Completed work

| Task | Implemented behaviour |
|---|---|
| W3.1 | All split/policy controls, a distinct inspected-policy choice, persistent selections and protected nonempty comparison set. |
| W3.2 | Three recorded metrics, five-split arithmetic means and sample SD using n−1, raw mean ± SD bands, consistent labelled colours/dashes, keyboard-selectable measured points and a table. Precision is shown as percent in the UI and fraction in CSV. |
| W3.3 | One timer plays five recorded prediction/reveal pairs. Manual Reveal advances ten queries; Preview selects the next batch without revealing it. Completion pauses at exactly 50. Pause, manual selection, navigation, history changes, reset, missing data and unmount invalidate pending work. A hidden-page listener pauses playback. |
| W3.4 | A responsive modal shows exactly ten selected records with material/formula/system/atoms, mean/radius in eV/atom, role, diversity, optional acquisition score and revealed target/hit fields. Random-policy missing scores remain unavailable. |
| W3.5 | Aggregate controls explicitly disable individual playback/query inspection and explain why. At zero, hit/system counts are zero and precision is unavailable. A single split can inspect batch-one predictions at zero. |
| W3.6 | A dedicated display projection nulls all three outcome fields before reveal. Chart data, tooltips, accessible descriptions, table and CSV respect completed budget. The public-data teaching scope is explicit. |
| W3.7 | Restorable URL selections, source/glossary integration, tested clipboard sharing and two full-precision downloads: displayed comparison boundaries and the inspected ten-query batch. CSV includes units, thresholds, source/study/release identity and null explanations. Zero rows explicitly identify their derived origin. |

Main implementation: [Replay](../src/views/Replay.tsx), [chart](../src/components/ReplayChart.tsx), [query drawer](../src/components/QueryDrawer.tsx), [replay model/CSV](../src/replay/model.ts), [playback controller](../src/replay/playback.ts) and [React lifecycle hook](../src/replay/useReplayPlayback.ts). The [replay contract](../contracts/REPLAY_CONTRACT.md) specifies the transition, units, reveal and export rules. The [independent requirements review](W3_REQUIREMENTS_REVIEW.md) found no blocker after reviewing the integrated source.

## Verification

| Evidence | Passed checks | What it establishes |
|---|---:|---|
| [Replay acceptance](W3_REPLAY_VALIDATION.json) | 45,871 | All 25 histories, 125 batches and 1,250 selected events match original saved sources; intermediate and endpoint counts/precision/system coverage agree. All comparison policy subsets, budgets, modes, nulls, full precision and reveal projections are checked independently. |
| [Playback acceptance](W3_PLAYBACK_VALIDATION.json) | 458 | All 25 contexts complete five preview/reveal pairs, cancellation invalidates queued callbacks, and actual platform-timer cancellation works. |
| [Actual download acceptance](W3_DOWNLOAD_VALIDATION.json) | 687 | Five real browser downloads match original source data and current filters. Includes hidden/revealed query exports, single-split comparisons at 10/50 and aggregate comparison at 50. Python independently reconstructs aggregate means/sample SD. |
| [Browser QA](W3_BROWSER_QA.json) | 43 | Real autoplay to 50, manual phases, cancellation, reveal hiding, share/URL restoration, keyboard points/modal focus, 360/390px layouts, source handoff, final production render and injected failure/recovery. |
| [Shared state](W3_STATE_VALIDATION.json) | 606 | Existing normalized route, saved-stage identity, history and timer conventions remain valid. |
| [Data guards](W3_DATA_GUARDS.json) | 202 | All 42 datasets and invalid/corrupt data guards remain valid. |
| [Frozen research](W3_RESEARCH_VALIDATION.json) | 108,571 | Exported scientific facts and saved-source arithmetic remain intact. |
| [Tooling/build copy](W3_TOOLING.json) | 124 | Pinned runtime/dependencies, final production payload and copied research files pass. Strict TypeScript and production build also passed. |

These are software/source verification results, not additional scientific experiments. The negative primary result remains clear: Quality retrieves more near-stable records than Full in all five historical splits; Full's broader chemical-system coverage answers a different question. Split bands describe five overlapping populations, not independent-dataset significance or predictor calibration. Historical retrieval does not establish a new DFT-confirmed stable material.

The final static build has 82 files totalling **4,545,072 bytes**. Initial JavaScript is **319,781 bytes** and chart JavaScript is **374,719 bytes**, loaded separately. Initial CSS is 25,819 bytes; chart CSS is 1,977 bytes. These are uncompressed sizes. No dependency was added. All 103 allowed research input hashes, four numerical-freeze/budget/manifest/event baseline hashes and 75 public release-file hashes match the [W3 baseline](W3_BASELINE.json). Historical W1/W2 verification evidence remains unchanged. The [machine closure](W3_COMPLETION.json) binds source, evidence, documentation and exact build hashes.

## Verification limits and optional scope

The available in-app browser timed out capturing screenshots. Responsive DOM geometry, accessibility trees, real controls and actual downloaded files were checked; no pixel/screenshot review is claimed. Its browser-hide capability and tab switching left `document.visibilityState` visible, so actual native hidden-page event delivery could not be tested. The visibility listener and controller pause/cancellation are verified separately in source and playback tests. W6 retains broader browser/device, motion and visual checks.

Two early clipboard observations ran before the asynchronous write completed; the subsequent success status and actual clipboard matched the current URL. The copy action also immediately offers the browser-address fallback while writing. This resolved observation timing is retained in the QA record.

**O1 scatter is deferred.** The core provides the ten-selection table and policy curves. No selected-only points are described as a complete candidate pool. A genuine saved pool would require archived inputs, explicit allowlisting and a separate payload/reveal review.

No core W3 functional exit item remains open. Owned local development/fault servers were stopped after QA; no hosting login/upload/deployment occurred. Next is **W4: Crystal Lab and saved-stage navigation**, followed by W5 findings/evidence, W6 integration/presentation and W7 InfinityFree deployment. W3 completion is not the W6 local-release or W7 live-deployment milestone.

## Reproduce

From `website/` in PowerShell:

```powershell
.\scripts\npm.ps1 run test:replay
.\scripts\npm.ps1 run test:playback
.\scripts\npm.ps1 run w3:downloads
.\scripts\npm.ps1 run w3:state
.\scripts\npm.ps1 run w3:data-guards
.\scripts\npm.ps1 run w3:research
.\scripts\npm.ps1 run build
.\scripts\npm.ps1 run w3:tooling
.\scripts\npm.ps1 run preview -- --port 4173
```

Open `http://127.0.0.1:4173/#/replay` to explore the recorded experiment. `w3:downloads` rechecks the actual artifacts retained under `reports/downloads/`. W3 commands write W3 evidence and preserve earlier phase reports. The network fault fixture is loopback-only and never enters the public deployment payload.
