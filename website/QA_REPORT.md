# Crystal Lab refresh QA

**Entry cache fix — 23 October 2026: live verified.** Responses for `/`, `/index.html` and the fresh `/refresh` alias return the same exact entry HTML with `no-store, no-cache, must-revalidate, max-age=0`, no-cache Pragma and expired Expires headers. JS/research/image sample hashes and cache policies are unchanged. Actual clicked homepage, Crystal Lab and fresh-entry links loaded current UI `ui-w6-351e6182d7af3a9d062d`; the lattice preset worked with no captured recovery console errors. [Targeted evidence](reports/CACHE_FIX_DEPLOYMENT.json) and [limits](reports/CACHE_FIX_UPDATE.md) retain the result. Current root config: 1230 bytes. No rebuild or broad suite rerun.

**23 October 2026 (Singapore): locally and live verified.** UI: `ui-w6-351e6182d7af3a9d062d`. Research: `data-v1-2a138b7808f0d12c5151`. Typecheck/build, 288 viewer checks, 330 orientation checks and 1,776 package-integrity checks passed. [Refresh report](reports/CRYSTAL_LAB_UPDATE.md), [local/live browser evidence](reports/CRYSTAL_LAB_BROWSER_VALIDATION.json), [viewer](reports/CRYSTAL_LAB_VIEWER_VALIDATION.json), [orientation](reports/CRYSTAL_LAB_ORIENTATION_VALIDATION.json) and [final integrity](reports/CRYSTAL_LAB_FINAL_INTEGRITY.json) retain acceptance.

Actual WebGL controls, saved lattice presets/arrows, the moving XYZ compass, atom inspection, keyboard behavior, opt-in touch, reset and axes visibility were checked. Local 375 px and 320 px layouts were reviewed; live 375 px inner width produced 360 px client/scroll widths with no horizontal overflow and 44 px minimum controls. Live console capture was clean and the public release manifest matched its exact package hash. [Desktop](reports/CRYSTAL_LAB_LIVE_DESKTOP.jpg) and [mobile](reports/CRYSTAL_LAB_LIVE_MOBILE.jpg) screenshots retain the result. The [crystal contract](contracts/CRYSTAL_CONTRACT.md) distinguishes saved lattice vectors from Cartesian orientation and preserves full-precision source/export semantics.

The historical W6 QA body below is preserved; [its standalone prior bytes](deployment/crystal-lab-controls/QA_REPORT.before-controls.md) remain available. This targeted functional update does not recertify the full historical suite or physical devices.

---

# W6 local release QA

Verified 22 October 2026. **Local release ready; not deployed.** Final UI: `ui-w6-62f633585edb6b4dab66`. Frozen data: `data-v1-2a138b7808f0d12c5151`. See the [completion report](reports/W6_COMPLETION.md), [machine closure](reports/W6_COMPLETION.json) and [preview instructions](LOCAL_PREVIEW.md).

| Gate | Result | Evidence |
|---|---|---|
| Frozen science, data, state and geometry | 224,507 assertions across eleven fresh read-only lanes | [Integrated source gate](reports/W6_INTEGRATION_VALIDATION.json) |
| Integrated integrity and contrast | 387 checks, including 33 specified text/graphic contrast pairs | [Integration](reports/W6_INTEGRATION_VALIDATION.json) |
| Tour controller | 123 checks; six steps, 25 scenes, exactly 180 presentation seconds | [Controller](reports/W6_TOUR_VALIDATION.json) |
| Native browser | 48 passing checks | [Browser QA](reports/W6_BROWSER_QA.json) |
| Full timed browser tour | All 25 scenes plus completion; 180.138 seconds; only Start was clicked | [DOM/input console record](reports/W6_TOUR_BROWSER_LOG.json) |
| Displayed exports | 34 checks across seven actual browser files and six kinds | [Downloads](reports/W6_DOWNLOAD_VALIDATION.json) |
| Production tooling | 124 checks; strict TypeScript and build pass | [Tooling](reports/W6_TOOLING.json) |
| Release, archive and old/new coexistence | 1,098 checks; 93 actual loopback HTTP responses | [Release gate](reports/W6_RELEASE_VALIDATION.json) |
| Cold Overview | 629,448 uncompressed response-body bytes; no chart/viewer request before intent | [Actual transfer](reports/W6_BROWSER_TRANSFER.json) |

The scientific lanes reproduce five seeds, five policies and five batches, sample SD and inclusive thresholds, all 1,250 selected events, 26 saved geometries, generation/uncertainty diagnostics, all QE/reference filters, nulls and source identity. These are implementation assertions, not additional scientific observations. No model fitting, inference, generation, matching, relaxation or QE job ran.

Browser coverage includes all five replay split choices and policy controls, zero/full boundaries, complete ordinary autoplay, aggregate restrictions, predictions-only/revealed random queries, source handoff/Escape, camera interaction, accepted CIF, all six views at 390px, actual WebGL context loss and retry, reduced-motion fixture, corrupt optional-image fallback, QE/reference filters, 3D loading on intent, Back/Forward, invalid-link normalization, reload and clean console logs. Wide tables scroll within labelled regions. Native hidden-page delivery and physical-device gestures are not claimed.

Four exports were newly collected in W6: comparison CSV, hidden/revealed query CSVs and accepted MgO CIF. Three actual W5 exports were retained with their original hashes and revalidated against the unchanged current projections: primary symmetry, risk and filtered QE. Their origin is explicit in the [selection manifest](reports/W6_DOWNLOAD_EXPECTATIONS.json). Download verification does not claim that all seven were freshly downloaded in W6.

The timed tour used an observation-only loopback script to record visible DOM scenes and inputs. It did not alter routes, clocks, selections or application code. That completed run used `ui-w6-b9b0eaf5f6cd87924a9e`. A subsequent CSS-only correction changed inherited crystal-control text from pale to dark on a light surface. App, tour, geometry, data and export source remained unchanged. The final source-bound release was rebuilt, and colour, mobile, renderer recovery, navigation and transfer checks were repeated. Earlier interrupted runs and assertion scope/timing corrections are retained separately; they do not count as passing final assertions.

The two large original PNGs remain byte-identical. Their lossless WebP presentation copies preserve every decoded RGBA pixel and reduce combined display bytes from 918,649 to 333,938. Missing or corrupted derivatives fall back through the original verified research loader. [Image verification](reports/W6_IMAGE_OPTIMIZATION.json) records hashes and dimensions.

The final payload has **88 files / 5,621,072 bytes**; the document-root ZIP is **3,093,510 bytes**. Initial JS is 428,395 bytes; initial CSS is 45,913 bytes. JS chunks remain below 900 kB and JSON shards below 500 kB. Two original scientific PNGs retain documented size exceptions; their UI copies are each below 300 kB. Runtime assets are local/same-origin. No service worker, runtime CDN, secret, management URL, checkpoint or scientific environment enters the package. Cache testing verifies local W5/current immutable-file coexistence, not hosting-provider cache behaviour.

Representative captures: [final desktop Overview](reports/W6_OVERVIEW_DESKTOP.jpg), [final mobile crystal controls](reports/W6_MOBILE_CRYSTAL.jpg), and [completed tour/methods panel](reports/W6_TOUR_COMPLETE.jpg). These were inspected as visible-panel screenshots; they do not certify every pixel or a screen reader.

Chrome and Edge connections were explicitly attempted and unavailable. Native testing used the ChatGPT in-app browser on Windows, with desktop and emulated mobile viewports. Physical mobile devices, screen-reader certification and native hidden-page delivery remain untested. Motion/context-loss fixtures are loopback tests, not changes to OS preferences. Advisory evidence in the tooling record is identified as recorded rather than a fresh live security audit.

All 103 original research inputs, four numerical/budget/event baselines, 75 curated content files, two manifest copies and W1-W5 historical evidence remain unchanged. Owned test servers and tabs were closed and viewport/mode overrides reset: [teardown](reports/W6_SERVER_TEARDOWN.json). W7 must inspect the account/root/HTTPS, back up the existing site, upload immutable files before entry HTML, preserve cached-client assets and verify the live site.
