# W6 complete: integrated QA, guided tour and local release

Completed 22 October 2026. **All eight W6 tasks are complete. The website is local release ready. W7 deployment remains planned.** No account login or upload occurred.

| Task | Completed output |
|---|---|
| W6.1 data/science | Eleven fresh read-only validation lanes reproduce aggregates, sample SD, thresholds, conversions, selected metadata, saved geometry/stages, nulls, failures and overlapping inventories. No research was rerun. |
| W6.2 interaction | Integrated controls, all split/policy choices, recorded batch autoplay, reveal, source handoff, stage/CIF, evidence filters, history, invalid URLs, reload and exports checked. |
| W6.3 accessibility/browser | Keyboard tour focus/exit, labelled controls, tables/text alternatives, explicit statuses, darker policy graphics, corrected crystal-control contrast, six mobile layouts, reduced-motion fixture and actual context-loss recovery. Unavailable browser/device coverage is explicit. |
| W6.4 performance | Viewer/chart chunks remain lazy; compact Overview starts with its real saved figure and opens 3D on intent. Existing demand rendering/mobile pixel-ratio limits remain. Two pixel-identical lossless WebP copies reduce figure transfer. Cold Overview is 629,448 bytes. |
| W6.5 file gate | Every production file and ZIP entry checked for sizes, hashes, MIME, missing chunks, source/runtime exclusions, credentials/local paths/management URLs and retained attribution. Frozen PNG exceptions are documented. |
| W6.6 coherence | Deterministic source-bound UI identity, separately pinned research release, versioned manifest and file inventory. Actual HTTP verifies W5/current immutable files coexist and old entry paths still resolve. |
| W6.7 tour | Start, pause/resume, previous/next, finish/restart and exit. Six timed sections, 25 exact scene presets, saved stages and local filters; full 180-second native run completed with no intervening input. Conflicting playback stops and ordinary browsing exits the tour. |
| W6.8 handoff | [QA report](../QA_REPORT.md), [preview/fallback rehearsal](../LOCAL_PREVIEW.md), screenshots, final optional-item register, source/build/file evidence and a checked document-root ZIP. |

Final UI: **`ui-w6-62f633585edb6b4dab66`**. Data remains **`data-v1-2a138b7808f0d12c5151`**, manifest SHA-256 `3b55f64687a8dd270482b3a2dfc9395672dbbce836fd90041712d2750e228e3d`.

Verification passed: **224,507 source assertions, 387 integrated checks, 123 tour checks, 48 native-browser checks, 34 export checks, 124 tooling checks and 1,098 release checks**. Exact scopes and counts are linked in [QA](../QA_REPORT.md); repeated contexts are not independent scientific evidence. Seven browser files were revalidated: four newly collected W6 exports and three hash-bound retained W5 exports.

The complete native timed run recorded all 25 scenes plus completion in **180.138 seconds**. A subsequent CSS-only contrast correction was rebuilt and retested on the final release; tour/application/geometry/data/export logic did not change. The browser record explicitly distinguishes the timed build from the final cosmetic revision. See [browser acceptance](W6_BROWSER_QA.json) and [tour log](W6_TOUR_BROWSER_LOG.json).

The payload contains **88 files, 5,621,072 bytes**. The ZIP is **3,093,510 bytes** and contains document-root-relative files, with no enclosing `dist/` folder. [Package record](W6_RELEASE_PACKAGE.json), [release acceptance](W6_RELEASE_VALIDATION.json) and [machine closure](W6_COMPLETION.json) bind exact hashes and identities.

[Download the local release ZIP](../releases/ui-w6-62f633585edb6b4dab66/ui-w6-62f633585edb6b4dab66.zip). To present locally, run from `website/`:

```powershell
.\scripts\npm.ps1 run preview -- --port 4173
```

Open `http://127.0.0.1:4173/`, select **Start guided tour**, and keep the server running during presentation. Use `Ctrl+C` afterwards. The [local preview guide](../LOCAL_PREVIEW.md) contains rebuild/package commands and the manual fallback script. The owned QA server was stopped after acceptance.

The independent [requirements review](W6_REQUIREMENTS_REVIEW.md) and [baseline](W6_BASELINE.json) preserve the scientific boundaries. All 103 research sources, four frozen baselines, 75 curated content files, both research manifest copies and historical W1-W5 evidence are unchanged. No dependency or scientific experiment was added. No newly discovered stable material, global novelty, complete hull or symmetry-free architecture benefit is claimed.

Optional dispositions: O1 scatter remains deferred; the selected-query table and curves meet core scope. O2 rich saved stages and O3 saved deciles are implemented. O4 extra camera effects are excluded from this release to preserve readability/performance and avoid fictitious trajectories. O5 records actual available browser coverage; publication controls remain disabled until real destinations exist.

Chrome and Edge connections were unavailable when attempted. Desktop/emulated mobile checks used the in-app browser; physical touch devices, screen-reader certification and native hidden-page delivery are not claimed. Those limits are explicit and do not represent missing core controls. Provider-specific HTTPS, cache headers, document root, backup/upload/rollback and live verification belong to **W7**. The checked local ZIP has not been deployed.
