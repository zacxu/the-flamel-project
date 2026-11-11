# W4 complete: interactive Crystal Lab

Completed 22 October 2026. All seven core W4 tasks and their exit conditions are complete. The optional rich viewer coverage O2 is also implemented. W5-W7 remain planned; no hosting login or deployment occurred.

The Crystal Lab now renders actual saved structures in Three.js, with the same viewer used by the Overview hero. All **14 distinct entities and 26 saved stages** are inspectable, including all eleven model-result records, the excluded twelve-atom transformer diagnostic and two separate accepted source-reference cells. Actual browser checks rendered every stage successfully in WebGL2.

## Completed work

| Task | Implemented behaviour |
|---|---|
| W4.1 catalog | All core examples, both symmetry control pairs and every additional saved prototype/reference have working selection, stage controls, 3D, metadata, coordinate inspection and export. The catalog retains method, role, atom count, available stages and model-result status. |
| W4.2 shared viewer | Lazy Three.js renderer with the true cell edges, species colours, occupancy/site inspection, mouse rotation, zoom/reset buttons, keyboard camera controls and an accessible camera readout. Auto-rotation starts off. Overview and Lab mount the same component on their respective routes; comparison figures use no extra renderer. |
| W4.3 geometry fidelity | Fractional positions multiply the row-vector lattice. Physical site indices and counts stay intact. Wrapping applies only along periodic axes for display; original coordinates remain in the table and export. Independent validation covers actual non-orthogonal cells, cell metrics/volume, Cartesian roundtrips and exact closest-image distances, including a skew-cell counterexample. |
| W4.4 stage identity | Only recorded stages can be selected; unavailable DFT is disabled and explained. Parent/source identity is inspectable. Separate entities remain separate, including the eight-atom MgO control and two-atom accepted QE source reference. Comparisons show labelled snapshots without morphing or invented trajectories. |
| W4.5 scientific metadata | Stage-specific method, SG/requested group, tolerance or explicit unknown, engine-qualified energy, volume, periodic minimum distance, exact-cell/workload eligibility, frozen queue and DFT status. Differences require the same composition, engine, units and complete actual settings. |
| W4.6 accessibility/fallback | Labelled keyboard camera/site controls, opt-in touch rotation, vertical page pan by default and reduced-motion support. Missing WebGL, missing renderer chunk, construction/draw failure and context loss preserve the real saved figure, metadata, coordinate access and CIF download. Retry reconstructs one viewer. Frame ownership and cleanup cover hidden/offscreen states, stage changes, route unmount and partial construction. |
| W4.7 export | Current-stage CIF with full-precision original coordinates, species/occupancies, exact source basis and stage/source/release identity. P1 explicitly encodes physical sites; recorded symmetry is provenance rather than a newly inferred/expanded structure. Blob URLs are replaced/revoked with the saved selection. |

Main implementation: [Crystal Lab](../src/views/CrystalLab.tsx), [shared display/fallback](../src/components/CrystalDisplay.tsx), [Three.js viewer](../src/components/CrystalViewer.tsx), [coordinates](../src/components/CrystalCoordinates.tsx), [geometry/CIF/comparison helpers](../src/crystal/geometry.ts) and [frame/resource ownership](../src/crystal/lifecycle.ts). The [geometry/export contract](../contracts/CRYSTAL_CONTRACT.md) defines the conventions. The [independent requirements review](W4_REQUIREMENTS_REVIEW.md) found no scientific-scope blocker.

## Verification

| Evidence | Passed checks | Scope |
|---|---:|---|
| [Geometry/export acceptance](W4_GEOMETRY_VALIDATION.json) | 7,060 | All 26 source-bound stages, 26 independent NumPy/pymatgen CIF roundtrips, 676 ordered energy compatibility checks, real non-orthogonal cells, raw coordinates, species/occupancy, SG provenance and source hashes. |
| [Renderer acceptance](W4_VIEWER_VALIDATION.json) | 288 | Shipped frame/resource/failure helpers, stale callback invalidation, hidden/offscreen cancellation, partial/StrictMode cleanup, actual Three.js geometry/material disposal and OrbitControls camera behaviour across five aspect ratios. These Node checks are separate from native GPU verification. |
| [Actual CIF downloads](W4_DOWNLOAD_VALIDATION.json) | 524 | Six real browser files: accepted eight-atom MgO, six-atom CaMg2O3 prototype, excluded twelve-atom CaMg2O3, non-orthogonal TiO2 P1 and independent two-atom MgO/CaO references. Exact source geometry/provenance and independent parser metrics/distances agree. |
| [Browser QA](W4_BROWSER_QA.json) | 69 | All 26 stages rendered in WebGL2; actual camera/site controls, comparison gates, hero/route replacement, mobile layouts, simulated motion/touch policy and actual GPU context-loss/draw-error recovery. |
| [Shared state](W4_STATE_VALIDATION.json) | 606 | Existing candidate/stage normalization, links, history and cancellation remain valid. |
| [Runtime guards](W4_DATA_GUARDS.json) | 202 | All 42 datasets and invalid/corrupt boundary cases remain valid. |
| [Frozen research](W4_RESEARCH_VALIDATION.json) | 108,571 | Public export facts and original saved-source arithmetic remain intact. |
| [Tooling/build copy](W4_TOOLING.json) | 124 | Runtime/dependency pins, final production bytes and copied research assets pass. Strict TypeScript and production build also passed. |

The two selected CHGNet pairs reproduce P1-minus-nontrivial differences of **356.879234 meV/atom for MgO** and **55.806478 meV/atom for TiO2**. Their supplementary/primary pool scopes and one-per-arm limitation remain explicit. The same pretrained architecture is conditioned differently; these pairs do not isolate a symmetry-free architecture, establish an energy distribution or demonstrate DFT stability. The accepted MgO QE reference/control difference is blocked because their actual k-mesh differs despite a shared settings-scope label. Cross-composition and model-versus-DFT comparisons are also blocked.

The final build contains **84 files, 5,138,412 bytes** uncompressed. Initial JavaScript is 338,844 bytes; lazy viewer JavaScript is 567,301 bytes and lazy chart JavaScript is 374,724 bytes. Each JS chunk remains below 900 kB. No dependency was added. Loopback-only fault controls are absent from production assets.

The [W4 baseline](W4_BASELINE.json) and [machine closure](W4_COMPLETION.json) bind all 103 original research inputs, the four frozen numerical/budget/manifest/event baselines, 75 curated content files and both manifest copies. All remain unchanged. Historical W1-W3 completion evidence is preserved. Geometry arithmetic and UI tests do not run a predictor, infer symmetry, perform new structure matching or dispatch relaxation/DFT. No new scientific result or stable-material claim is introduced.

## Verification limits and next work

Screenshot capture timed out in the available in-app browser. Real WebGL2 rendering, responsive DOM geometry, accessibility state, camera readouts and actual interactions were checked; no pixel/screenshot review is claimed. Touch-pointer policy and reduced motion were exercised through loopback browser fixtures. No physical touchscreen gesture, system preference change or native page-hidden delivery is claimed. Source wiring and independently injected frame-owner cancellation cover hidden/offscreen behaviour; W6 retains broader visual/device checks.

Core context-loss acceptance used the browser's actual `WEBGL_lose_context` extension. Draw failure, missing WebGL/chunk/stage and reduced-motion/touch fixtures were injected only by the loopback QA server, without changing `dist/`, public data or the deployed application. Actual context loss preserved the selected evidence, and retry restored one renderer.

**No core W4 functional exit item remains open.** O2 is implemented for every currently exported stage. Extra visual effects O4 remain optional for W6 review; replay scatter O1 remains deferred from W3. Owned local development/fault servers were stopped after QA. Next is **W5: findings and evidence**, then W6 integration/presentation and W7 InfinityFree deployment. W4 completion is not the final local-release or live-deployment milestone.

## Reproduce

From `website/` in PowerShell:

```powershell
.\scripts\npm.ps1 run test:crystal
.\scripts\npm.ps1 run test:viewer
.\scripts\npm.ps1 run w4:downloads
.\scripts\npm.ps1 run w4:state
.\scripts\npm.ps1 run w4:data-guards
.\scripts\npm.ps1 run w4:research
.\scripts\npm.ps1 run build
.\scripts\npm.ps1 run w4:tooling
.\scripts\npm.ps1 run preview -- --port 4173
```

Open `http://127.0.0.1:4173/#/crystals`. `w4:downloads` checks retained actual browser artifacts under `reports/structure-downloads/`; geometry acceptance separately roundtrips all saved stages. W4 commands preserve earlier phase reports.
