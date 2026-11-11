# Website implementation status

Updated 22 October 2026. **W1-W7 are complete in full; live deployed and verified.** Open [The Flamel Project](https://theflamelproject.42web.io/). The research numerical freeze, experiment events and budgets are unchanged. [Deployment record](DEPLOYMENT_RECORD.md) retains authenticated-root, upload, live QA and rollback evidence.

| Phase | State | Evidence / next work |
|---|---|---|
| W1: sources, contracts and setup | Complete | [Completion report](reports/W1_COMPLETION.md), [machine record](reports/W1_COMPLETION.json) |
| W2: experience and shared shell | Complete | [Completion report](reports/W2_COMPLETION.md), [machine record](reports/W2_COMPLETION.json), [browser checks](reports/W2_BROWSER_QA.json) |
| W3: acquisition replay | Complete | [Completion report](reports/W3_COMPLETION.md), [machine record](reports/W3_COMPLETION.json), [browser checks](reports/W3_BROWSER_QA.json) |
| W4: Crystal Lab | Complete | [Completion report](reports/W4_COMPLETION.md), [machine record](reports/W4_COMPLETION.json), [browser checks](reports/W4_BROWSER_QA.json) |
| W5: findings and evidence | Complete | [Completion report](reports/W5_COMPLETION.md), [machine record](reports/W5_COMPLETION.json), [browser checks](reports/W5_BROWSER_QA.json), [findings/evidence contract](contracts/FINDINGS_EVIDENCE_CONTRACT.md) |
| W6: QA and presentation | Complete; local release ready | [Completion report](reports/W6_COMPLETION.md), [machine record](reports/W6_COMPLETION.json), [QA report](QA_REPORT.md), [release verification](reports/W6_RELEASE_VALIDATION.json), [preview/rehearsal](LOCAL_PREVIEW.md) |
| W7: InfinityFree deployment | Complete; live verified | [Completion](reports/W7_COMPLETION.md), [machine closure](reports/W7_COMPLETION.json), [deployment/rollback](DEPLOYMENT_RECORD.md), [live QA](reports/W7_LIVE_BROWSER_QA.json) |

## W1 task closure

| Task | Complete output |
|---|---|
| W1.1 tooling | Node 24.19.0, workspace npm 12.2.1, exact dependency pins/lockfile, strict TypeScript and Vite configuration |
| W1.2 integrity | Four frozen baseline hashes, 103 individually verified source inputs and read-only before/after checks |
| W1.3 selected metadata | 1,250 events joined to formula/system metadata for 720 distinct queried IDs; full metadata and evaluation target-ID set excluded |
| W1.4 stage registry | 14 distinct entities and 26 saved stages with verified source/parent identity, actual atoms, eligibility and acceptance flags |
| W1.5 contracts | [Typed schemas](src/data/contracts.ts), [contract guide](contracts/DATA_CONTRACT.md), strict booleans, nulls, units and full precision |
| W1.6 versioned export | 42 JSON datasets and 33 assets; one immutable manifest, content hashes, generated build pin and integrity-checking loader |
| W1.7 geometry | Row-vector lattice/fractional contract; original coordinates, occupancies/PBC, stage-specific recorded settings; independent nonorthogonal/periodic checks |
| W1.8 content | Scoped claims, glossary, policy/element colours, methods, source credits, retained dependency licences, five research figures and 26 stage-specific fallback PNGs |

## W1 verification (historical closure)

- Export: **3,082 checks passed**; 103 allowed source hashes and four frozen baseline files unchanged.
- Independent data/source validation: **108,571/108,571 passed**.
- Actual loader through local HTTP: **10/10 passed**, including altered-manifest/data rejection and nested-base loading.
- Tooling/production-copy checks: **124/124 passed**; strict TypeScript and production smoke build passed.
- Active data release: `data-v1-2a138b7808f0d12c5151`. All final records bind this release and its manifest hash.
- Recorded npm advisory query: zero reported vulnerabilities at the recorded check time.

The W1 smoke entry has now been replaced by the application. W1's dated completion records remain historical evidence. W3 adds full replay/downloads; W4 adds interactive saved structures and CIF export; W5 adds complete findings/evidence interactions and analysis downloads. At W1 closure the three-minute tour and integrated local release closure remained W6 deliverables. W6 now provides the local release; live deployed/verified remains a W7 milestone.

Two original research PNGs exceed the normal 300 kB image goal (488 kB and 431 kB). Their original research bytes remain faithfully retained. W6 adds separate lossless, pixel-identical WebP presentation derivatives below 300 kB; the original PNG exceptions and exact transfer/file measurements are recorded in the W6 release gate. All JSON shards are below 500 kB; all 26 new fallback PNGs are below 36 kB. No W1 exit item remains unresolved.

## W2 task closure

| Task | Complete output |
|---|---|
| W2.1 skeleton | Six navigable React/TypeScript views, same-origin pinned data and static hash routes |
| W2.2 design | Warm paper/graphite/copper/blue system, serif/system typography, labelled statuses, numeric formatting, actual policy colours and distinct narrative/workflow/table/crystal layouts |
| W2.3 overview | Exact headline/supporting copy, both working actions, research hypothesis, actual accepted eight-atom MgO fallback, recorded-mode and discovery limits |
| W2.4 workflow | Seven clickable real input/output/status stages; separate historical/fresh tracks, empty new-formula path, predetermined known control and prototype branches |
| W2.5 shared state | All specified fields, normalized reloadable links, real candidate/stage validation and temporary-state separation |
| W2.6 defaults/reset | Aggregate Quality versus Full at 50 queries, paused; complete reset, Back/Forward and registered timer cancellation |
| W2.7 interpretation | Searchable glossary, reusable modal source/method drawer, inclusive thresholds/units, calibrated-radius formula, scoped attribution and unavailable publication links |
| W2.8 responsive/failures | Mobile navigation/layout, labelled scrollable tables, skip/focus handling, modal Escape/return, reduced-motion support and scoped loading/empty/error/retry |

Final results: **606 state checks, 202 runtime-guard checks, 42 actual browser checks and 124 tooling/build-copy checks passed**. Strict TypeScript and production build passed. Independent research validation passed **108,571 checks**; the same 103 sources, four baseline hashes and public release are unchanged. The final production shell is 298,636 bytes JS and 21,581 bytes CSS; the complete static tree is 4,142,993 bytes.

Browser screenshot capture timed out in the available in-app browser. Responsive DOM geometry, accessibility state and real interactions were checked; no pixel/screenshot review is claimed. This verification limit is retained for W6's broader visual/device pass. No W2 functional exit item remains open. See the completion report for exact browser coverage and remaining W3-W7 scope.

## W3 task closure

| Task | Complete output |
|---|---|
| W3.1 comparison | Aggregate plus five splits, five policy toggles, separate inspected policy, default Quality/Full and measured budget boundaries |
| W3.2 metrics/chart | Hits, precision and system coverage; single-split outcomes or five-split mean/sample SD; lazy chart, accessible points and displayed table |
| W3.3 playback | Preview/reveal phases for five saved ten-query batches; Play/Pause/Next/Start at zero/full reset; one timer and cancellation on incompatible changes |
| W3.4 query drawer | Ten saved selections with formula/system, atoms, predictions/radius, role, diversity, optional score and correctly gated target/hit fields |
| W3.5 aggregate/zero | Disabled individual playback/query controls with explanation; zero counts, unavailable zero precision and first-batch prediction inspection |
| W3.6 reveal/scope | Future boundaries excluded from chart/table; hidden outcomes absent from display projection and query CSV; explicit teaching/public-data scope |
| W3.7 share/export | Restorable URL identity, actual clipboard action, source handoff, full-precision comparison/query CSVs with units, nulls, release/source IDs and zero-origin labels |

Final acceptance: **45,871 replay checks, 458 playback checks, 687 checks across five actual CSV downloads and 43 browser checks passed**. Regression checks passed: **606 shared-state, 202 runtime-guard, 108,571 frozen-research and 124 tooling/production-copy checks**. Strict TypeScript and production build passed. The 82-file static tree is 4,545,072 bytes; initial JS is 319,781 bytes and lazy chart JS is 374,719 bytes. All 103 allowed research sources, four frozen baseline files and 75 public release files remain unchanged; dated W1/W2 evidence is preserved.

Browser QA covers actual complete autoplay, manual phases, pause/selection/navigation/reset cancellation, reload/Back/Forward, chart keyboard selection, mobile drawer/layout, source handoff, label hiding and production recovery from missing history/chart files. Screenshot capture remained unavailable, and IAB's hide capability kept `document.visibilityState` visible. Native hidden-page event delivery therefore remains unverified in this browser; the hook wiring, timer invalidation and pause action were checked separately. Broader device/visual QA remains W6 work. Optional O1 scatter is explicitly deferred. **No core W3 functional exit item remains open.**

## W4 task closure

| Task | Complete output |
|---|---|
| W4.1 catalog | All 14 entities, including 11 model-result records, excluded 12-atom diagnostic and two distinct source references; all 26 saved stages have rich viewing |
| W4.2 shared 3D | Lazy Three.js viewer in Lab and Overview; true cell edges, species/occupancy, atom selection, mouse/keyboard controls, zoom/reset and camera readout |
| W4.3 geometry | Row-vector Cartesian conversion, original site identity, PBC-only display wrapping, non-orthogonal volume/periodic-distance/roundtrip verification |
| W4.4 stage identity | Existing recorded stages only; explicit unavailable DFT; parent/source tracing; separate snapshots rather than invented morphs |
| W4.5 comparison | Stage-specific SG/tolerance/energy and eligibility/queue/DFT flags; complete actual-settings gate; both scoped one-per-arm CHGNet pairs |
| W4.6 fallback/accessibility | Actual saved image, metadata/coordinates/export on GPU failure; native context-loss recovery, keyboard site/camera controls, touch pan by default, opt-in rotation and reduced motion |
| W4.7 export | Full-precision explicit-site P1 CIF with original source basis, stage/source/release identity, eligibility and recorded symmetry; independent parser roundtrips and actual download checks |

Final acceptance: **7,060 geometry/export checks, 288 renderer/lifecycle checks, 524 checks across six actual CIF downloads and 69 browser checks passed**. All 26 saved stages rendered in real WebGL2. Browser checks include camera changes/reset, shared hero, stage replacement/unmount, both energy pairs and rejected comparisons, 360/390px layout, simulated reduced motion, touch-pointer page-pan policy and recovery from actual context loss, draw failure, missing WebGL/chunk/stage data. Shared-state 606, runtime-guard 202, frozen-research 108,571 and tooling/copy 124 checks also passed. Strict TypeScript and production build passed.

The 84-file static tree is **5,138,412 bytes**. Initial JS is 338,844 bytes; lazy viewer JS 567,301 bytes; lazy chart JS 374,724 bytes. All 103 research inputs, four frozen baseline files, 75 curated content files and both manifest copies remain unchanged. Historical W1-W3 evidence is preserved. No new dependency, scientific experiment or deployment was added.

Screenshot capture timed out, so no pixel review is claimed. Touch policy and reduced motion were tested through loopback browser fixtures; no physical touchscreen gesture or system-preference change is claimed. Native hidden-page delivery remains unverified; source wiring and frame-owner cancellation were checked independently. Broader visual/device coverage remains W6. **Optional O2 is implemented; no core W4 functional exit item remains open.**

## W5 task closure

| Task | Complete output |
|---|---|
| W5.1 primary symmetry | Both first-eight arms for MgO/TiO2; raw valid/unique counts and fractions; same architecture/different conditioning and causal limits |
| W5.2 supplement/energies | Separate four-draw MgO supplement; distinct supplemented-MgO/primary-TiO2 one-per-arm CHGNet panels; scoped anatase/rutile reference ranking |
| W5.3 composition cohorts | All six formulas and 48 attempts; 0/48 exact-cell eligibility, reason counts and all twelve excluded larger-cell diagnostics |
| W5.4 prototypes/novelty | Four separate prototype baselines, all eleven model records, historical composition absence and partial 15/23 MgO and 34/44 TiO2 geometry coverage |
| W5.5 reliability | Five split selectors, Initial/Quality/Full plus three advanced endpoints; empirical/nominal coverage, interval-width/error context and calibration formula |
| W5.6 selective risk | Ten recorded retained-fraction steps with actual row count/fraction, subset/all-row MAE and explicit diagnostic-subset limits |
| W5.7 roles | Expandable all-five-split conservative/optimistic event accounting, query-weighted radii, 140/175 versus 7/75 hits and nonrandomized-role caveat |
| W5.8 DFT ledger | All nineteen QE jobs; role/phase/calculation/evidence filters and counts; separate process, SCF, job-setting stationarity and final finite-check fields |
| W5.9 incomplete evidence | Three accepted geometries versus two source-reference IDs; primary 2/161 and fallback 1/57; overlapping 218 memberships/215 missing; incomplete perturbation and absent full hull |
| W5.10 methods/claims | Ten-row claim matrix, fourteen source-linked narrative findings, methods, frozen date, attribution, glossary and computational accounting; unresolved MgO energy ordering retained |
| W5.11 downloads/links | Full-precision displayed-table CSVs with source/units/null/scope metadata; saved-cell exports through Crystal Lab; figures; honestly unavailable publication destinations |

Independent source/model acceptance passed **3,835 generation, 55,470 uncertainty and 2,136 evidence checks**. The evidence checks exhaust all 630 DFT filter combinations and 36 reference-membership filter combinations. Actual browser analysis-download acceptance passed **420 checks across eighteen files, thirteen table kinds and 480 rows**. Shared-state **606**, runtime-guard **202**, frozen-research **108,571** and tooling/production-copy **124** checks passed. Strict TypeScript and production build passed; [W5 tooling](reports/W5_TOOLING.json), [browser QA](reports/W5_BROWSER_QA.json) and [completion](reports/W5_COMPLETION.md) record final production details, browser coverage and build measurements without replacing historical W1-W4 records.

[Independent requirements review](reports/W5_REQUIREMENTS_REVIEW.md) covers all eleven W5 requirements and finds no unresolved source/data blocker. The [findings/evidence contract](contracts/FINDINGS_EVIDENCE_CONTRACT.md) defines shared versus local display selections, distinct uncertainty populations, acceptance layers and export semantics. Optional O3 saved-decile enrichment is implemented from all 300 recorded rows. O1 scatter remains explicitly deferred; O2 saved-stage enrichment remains implemented.

Final browser acceptance passed **54 checks**, including 360/390px layouts, keyboard risk selection, source/focus handoff, actual saved-stage/CIF links, all endpoint types and scoped HTTP-404/Retry recovery. Three visible-panel screenshots were captured and inspected. The 84-file build is **5,227,006 bytes**, with 413,933-byte initial JS and 44,190-byte initial CSS. Owned QA servers were stopped and the viewport override was cleared.

All 103 frozen research inputs, four numerical baselines, 75 curated content files, both manifest copies and historical W1-W4 evidence remain unchanged. W5 adds no scientific job, new dependency or deployment. Broader whole-page visual/accessibility, physical-device and integrated presentation verification remains W6 work. **No core W5 functional exit item remains open. W6 integrated closure is recorded below.**


## W6 task closure

| Task | Complete output |
|---|---|
| W6.1 source/science | Eleven fresh W6 source/geometry/state/lifecycle regression reports; independently reconstructed aggregates/sample SD, inclusive thresholds, conversions, nulls, metadata joins and every saved stage; [integration gate](reports/W6_INTEGRATION_VALIDATION.json) binds hashes |
| W6.2 integrated interactions | Production browser replay/history/navigation, filters, stage changes, source drawers, downloads, malformed links, loading/failure/retry and tour interaction checks; exact results in [QA report](QA_REPORT.md) |
| W6.3 accessibility/browser | Keyboard and focus paths, labelled controls, equivalent chart tables, reduced motion, intentional horizontal table scroll, viewer fallback and measured text/graphic contrast; actual browser/device limits recorded below |
| W6.4 performance | Lazy chart/viewer, visible-only frame ownership, mobile pixel-ratio cap, system fonts and separate lossless image derivatives; measured cold-entry envelope and full payload in [release verification](reports/W6_RELEASE_VALIDATION.json) |
| W6.5 file gate | Conservative uncompressed budgets, content/MIME/path/secret checks, retained licence notices and exact production/ZIP inventories; original research PNG size exceptions remain explicit |
| W6.6 coherence | Source-bound UI build ID, pinned immutable research-manifest version/hash, versioned file manifest and actual local HTTP predecessor/new-release coexistence check |
| W6.7 tour | Six timed steps over 180 seconds, exact saved presets, start/pause/resume/previous/next/exit, conflicting playback cancellation and normal browsing handoff; [tour contract](contracts/GUIDED_TOUR_CONTRACT.md) and [tour checks](reports/W6_TOUR_VALIDATION.json) |
| W6.8 handoff | [Completion record](reports/W6_COMPLETION.md), [QA record](QA_REPORT.md), representative screenshots, [local ZIP package record](reports/W6_RELEASE_PACKAGE.json) and [HTTP preview/rehearsal instructions](LOCAL_PREVIEW.md) |

Fresh source regressions passed **224,507 assertions** across research exports, HTTP loader, runtime guards, shared state, replay, playback, geometry/CIF, viewer lifecycle, generation, uncertainty and evidence. Counts include repeated contexts and do not represent independent scientific observations. The integration report binds these results, the final tooling report and all unchanged research/historical website evidence. Exact final tour, native browser, downloaded-file, release-gate, bundle-size and cold-transfer counts belong to the linked final W6 reports rather than provisional documentation snapshots.

Only the available in-app browser could be exercised. Desktop and mobile viewport checks are recorded with representative captures; Chrome and Edge access was attempted but unavailable. Physical mobile/touchscreen devices, other browser engines and native hidden-page behavior that the available environment cannot deliver remain untested. Source/timer/frame-owner checks do not convert those limits into native coverage. Publication controls remain disabled because no checked public repository, one-page account or video destination exists.

W6 corrects policy graphic contrast with UI-only colours and adds pixel-identical lossless presentation images. The original theme/figure bytes, all 103 frozen research inputs, four parent numerical/budget files, 75 curated content files and both research manifests remain unchanged. Historical W1-W5 completion/evidence files remain unchanged. No scientific compute, new dependency installation, hosting login, upload or live deployment was performed.

Optional dispositions are final for this local release: O1 scatter deferred because the selected-query table and policy curves provide the core comparison without inventing a full pool; O2 all saved-stage viewing and O3 saved uncertainty deciles implemented; O4 additional camera trajectories/effects intentionally excluded to protect accessibility, performance and the actual saved-stage account; O5 records only actual browser coverage and keeps unavailable publication assets disabled. See the [optional register](PHASED_IMPLEMENTATION_PLAN.md#optional-enrichment-register).

**No core W6 functional exit item remained open at its historical closure. W7 live closure is recorded below.** The website does not itself complete the research write-up, video, public repository or final hackathon submission.


## W7 task closure

All seven deployment tasks are complete. The authenticated target maps to `/htdocs`; original hosting files and editor-derived recovery copy are retained. The unchanged88-file base is live with33opaque image sidecars,230-byte root/156-byte child configs and a separately inventoried host recovery package. The identical entry was republished last after transport/cache repairs. Final inventory has126physical files and88effective release paths.

Final acceptance passed41targeted live browser checks,302actual-download checks,315remote-inventory checks and1,262local-integrity checks. All26saved stages, six views, replay/reveal, WebGL/camera/coordinates, sources, filters, uncertainty, six paused tour scenes, mobile layout and reloadable hash links were exercised. Earlier failed observations remain preserved with their final dispositions. Browser/device limits and non-blanket remote-hash scope are explicit. See [W7 completion](reports/W7_COMPLETION.md), [live QA](reports/W7_LIVE_BROWSER_QA.json), [downloads](reports/W7_LIVE_DOWNLOAD_VALIDATION.json), [final inventory](reports/W7_FINAL_REMOTE_INVENTORY.json), [host files](reports/W7_HOST_FILES.json) and [deployment/rollback record](DEPLOYMENT_RECORD.md). All frozen research and W1-W6 historical evidence remain unchanged. **No core W7 item remains open.**
