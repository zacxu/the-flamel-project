# The Flamel Project: phased website implementation plan

Prepared 22 October 2026 after reviewing the [website plan](WEBSITE_PLAN.md), [source inventory](research_sources.json) and [frozen research conclusions](../reports/phase6_report.md).

**Status: W1-W7 complete on 22 October 2026; live deployed and verified.** See [implementation status](IMPLEMENTATION_STATUS.md) and the [W1](reports/W1_COMPLETION.md), [W2](reports/W2_COMPLETION.md), [W3](reports/W3_COMPLETION.md), [W4](reports/W4_COMPLETION.md), [W5](reports/W5_COMPLETION.md) and [W6](reports/W6_COMPLETION.md) completion reports for actual artifacts and validation. Website implementation uses the recorded study; no new scientific experiment was performed. [W7 completion](reports/W7_COMPLETION.md) and the [deployment record](DEPLOYMENT_RECORD.md) record the verified hosting release.

The website plan defines the experience and scientific scope. This document defines execution order, dependencies, deliverables and checks. If a conflict appears during implementation, resolve it explicitly in these website documents while preserving the frozen research evidence. Do not rerun or rewrite earlier research finalizers to incorporate website work.

## Execution rules and milestones

- Work inside `website/`. The parent research reports, model/data files, experiment event ledger and numerical freeze remain unchanged.
- Deliver all six views: Overview, Workflow, Replay, Crystal Lab, Findings and Evidence. Preserve every core interaction in website-plan sections 4A-4F.
- Keep W1-W7 distinct from research Phases 1-8. Phase completion requires its outputs and exit checks, not just a first draft of its screen.
- Complete source contracts before UI widgets. W3-W5 may be implemented independently after the shared W1/W2 foundations, but final integration must use the same data and state conventions.
- Record each phase's actual completion and verification in `IMPLEMENTATION_STATUS.md`, with evidence paths and any unresolved item. Unperformed work stays planned.
- **Local release ready:** W1-W6 pass and the production build is available for review/presentation through a local HTTP server.
- **Live deployed and verified:** W7 also passes on the supplied InfinityFree domain. A local build or successful upload alone is not a verified live deployment.
- A reduced-scope demonstration is a separate milestone. Missing core replay, viewer, findings or evidence functionality cannot be relabelled full completion. Optional items have a visible register below.

### Schedule and dependency overview

Estimates assume one implementation stream and working downloads/account access. The seven phases total approximately **6 hours 15 minutes to 9 hours 5 minutes**; reserve another **45 minutes** for integration or hosting issues. Plan roughly **7-10 hours** for the complete core. A five-hour compressed demonstration must declare any reduced scope. Protect the separate hackathon write-up/video buffer.

| Phase | Dependencies | Estimate | Main deliverable | Current state |
|---|---|---:|---|---|
| W1 — Sources, contracts and setup | Existing frozen study | 60-80 min | Verified exports, source/stage registry, pinned local tooling | Complete |
| W2 — Experience and shared shell | W1 schemas and source IDs | 60-75 min | Six-view shell, workflow, design and shared route/state | Complete |
| W3 — Recorded acquisition replay | W1 exports + W2 shell/state | 60-75 min | All seeds/policies, batch playback and query inspection | Complete |
| W4 — Crystal Lab | W1 stage registry + W2 shell/state | 60-90 min | Core 3D examples, valid stage navigation and accessible fallback | Complete |
| W5 — Findings and evidence | W1 exports + W2 shell; integrate W3/W4 links | 60-90 min | Symmetry, compositions, uncertainty and complete DFT evidence views | Complete |
| W6 — Integrated QA and presentation | W3-W5 complete | 45-75 min | Tested production build, tour and local release | Complete; local release ready |
| W7 — InfinityFree deployment | W6 passed + authenticated account access | 30-60 min | Verified live build, deployment record and rollback payload | Complete; live verified |

## W1 — Sources, contracts and local setup

**Goal:** make it possible to build every interaction from small, accurate, versioned public exports without modifying or rerunning the study.

**Inputs:** [research source inventory](research_sources.json), frozen Phase 6 summaries/tables, Phase 5 selection plan, Phase 3/4 accepted-QE summaries and the associated verified geometries. The starting inventory is not yet the finished exporter allowlist or complete stage registry.

### Work

1. **W1.1 — Tooling:** provide a supported local Node/npm runtime, verify it against the chosen Vite requirements, and pin React, TypeScript, Vite, Recharts and Three.js with a lockfile. Reuse the existing analysis Python environment for data conversion. Keep runtime/download/build state outside the public payload; do not alter the frozen analysis environment merely to build the frontend.
2. **W1.2 — Integrity baseline:** record the source inventory, numerical-freeze, budget and experiment-event hashes before reading data. Expand only a named allowlist. No model fitting, predictor inference, generation, relaxation or QE dispatch is part of export.
3. **W1.3 — Metadata join:** join the 1,250 recorded query events to `artifacts/phase2/features/row_metadata.csv` using material ID. Export only the needed formula/chemical-system fields for the 720 distinct queried IDs. The query journal itself lacks these fields. Do not ship the full 8,294-row metadata table, oracle labels or evaluation target-ID set merely to display selected queries.
4. **W1.4 — Stage registry:** resolve each required candidate's initial/model/accepted-QE source through frozen selection/result records. Store candidate ID, stage ID, recorded parent/source relation, method, available stages, source/evidence hashes, actual atoms, eligibility and validation status. Add separately identified catalog/reference entities. Matching formulas alone do not establish a stage lineage: the eight-atom model rocksalt reference and two-atom accepted source QE reference are distinct execution cells.
5. **W1.5 — Typed contracts:** define schemas for study summary, replay, uncertainty, generation, structures, evidence, public sources and release metadata. Use stable enums, numeric units, explicit boolean parsing and nulls. The CSV string `False` is false; empty random-policy scores are null. Reject unexpected/non-finite values or mark them unavailable according to the contract. Retain full numerical precision; rounding belongs to presentation.
6. **W1.6 — Export:** implement the exporter, source-to-public-ID mapping and validators. Group replay data by seed/policy/batch; export stage geometry only for verified sources. Logical filenames map to versioned/content-hashed files through one release-pinned data manifest. Study date, export date and UI build ID are distinct.
7. **W1.7 — Geometry contract:** specify lattice row vectors in angstroms, fractional coordinates, species/occupancy, site indices and PBC flags. Cartesian coordinates follow `fractional @ lattice`. Retain stage-specific SG/symmetry settings, energy engine/unit/settings scope and eligibility reason. Unknown settings stay unknown; do not perform new symmetry inference to invent missing provenance. Separate physical atom count from display wrapping or optional periodic images.
8. **W1.8 — Content package:** prepare a claim list, glossary, policy/element colours, actual structure fallback images, public-safe methods/source summaries and relevant attribution/dependency notices. Confirm redistribution conditions for selected source-derived content. Public navigation must not expose local absolute paths, admin links or login/session material. Report/repository/video URLs become active only when their destinations exist and have been checked.

### Source checks to carry into export validation

These are counts in the source files. If an export intentionally uses a documented subset, validate both the full source and the selection rule instead of pretending the subset has the full count.

| Input | Expected source count / invariant |
|---|---|
| Frozen experiment grid | 5 seeds × 5 policies × 5 batches × 10 queries |
| Learning curves | 125 nonzero batch points; add a labelled zero-query origin |
| Policy endpoints | 25 rows |
| Selected-query journal | 1,250 events; 720 distinct material IDs |
| Selected metadata join | Every queried ID resolves exactly once; export only needed fields |
| Evaluation metrics | 130 prediction snapshots; `initial_shared` occurs once per seed, not once per policy |
| Risk/retention | 300 source rows; preserve actual retained row counts/fractions |
| Uncertainty deciles | 300 source rows; optional O3 visualization and table/CSV implemented in W5 |
| Full-policy roles | 10 rows: 5 seeds × conservative/optimistic |
| Generation | 88 actual draws; 12 cohorts = 4 primary control + 2 supplementary + 6 new formula |
| New-formula diagnostics | 0/48 eligible; 12 excluded larger-cell outputs across six formulas |
| Prototype/model records | 4 prototypes; 11 selected model finals; 2 balanced model-energy pairs |
| Fresh QE table | 19 attempted jobs; 3 fully checked relaxed geometries |
| Reference memberships | 218 total = 161 primary + 57 fallback; 215 missing = 159 + 56; systems overlap |

### W1 deliverables (completed)

- `package.json`, lockfile, TypeScript/Vite configuration and documented local runtime.
- `scripts/export_research.py`, `scripts/validate_export.py` and a typed data-contract specification.
- Public data manifest, curated JSON files, candidate/stage registry and source attribution index.
- An export-validation result recording row counts, joins, unit checks and unchanged parent hashes.

**Exit gate:** every required record/source/stage resolves; the selected histories reproduce both cumulative hit counts and chemical-system coverage; geometry conversion/roundtrip checks include a non-orthogonal cell; exports contain no unsupported claims, missing required data or non-finite JSON; frozen parent hashes are unchanged. UI work must not fill contract gaps with fabricated values.

## W2 — Narrative, design and shared application shell

**Goal:** make the first minute understandable and establish the conventions every interactive view will share.

### Work

1. **W2.1 — Application skeleton:** create Overview, Workflow, Replay, Crystal Lab, Findings and Evidence in the planned folder layout. Use React/TypeScript with a static Vite build, same-origin data loading and hash routes. No scientific backend, database, CMS installer or hosting-side Node process is required.
2. **W2.2 — Design system:** implement warm off-white/graphite/copper/blue styling, system typography, numeric formatting, consistent policy colours and text-labelled status badges. Use an editorial introduction, diagram, charts, viewer workspace and table rather than repeated generic cards.
3. **W2.3 — Overview:** implement the proposed headline/supporting text, research question and primary/secondary actions. Explain that this is recorded research replay. The hero uses the saved known-MgO example with a truthful stage label, static fallback initially and the shared viewer when W4 is available.
4. **W2.4 — Workflow:** build clickable Propose → Generate → Screen → Select → Relax → Validate → Compare nodes, each with actual input/output/status. Separate historical acquisition from fresh generation/validation. Show the empty new-formula path, predetermined MgO control and prototype baseline without implying substitutions or compatible feedback labels.
5. **W2.5 — Shared route/state:** define active view, aggregate/seed mode, visible policy set, inspected policy, completed query budget, inspected batch, reveal state, playback status, candidate/stage, primary/supplementary scope, uncertainty endpoint and retained fraction. Serialize meaningful selections in hash links; keep temporary animation/drawer state local. Validate unknown values and normalize invalid combinations rather than silently displaying mismatched records.
6. **W2.6 — Defaults and reset:** start with aggregate Quality-versus-Full at 50 queries and playback paused. Candidate detail requires a single recorded seed/policy. Route/mode/seed/inspected-policy changes cancel timers and close invalid drawers. Define browser back/forward behaviour and full reset once for all views.
7. **W2.7 — Interpretation:** add explanations/glossary and a reusable source drawer. Historical near-stable means the fixed signed target <=0.05 eV/atom; reference-hull hits use <=0. Prediction/model energy/fresh DFT energy/catalog absence/stability are separate. A source hash establishes file identity, not scientific acceptance.
8. **W2.8 — Responsive and failure states:** implement navigation, loading, empty, unavailable and error states. Keep core text usable while a plot/viewer loads. Establish focus handling, labelled controls, chart data-table patterns, reduced-motion support and mobile drawers/table scrolling.

**Deliverables:** shared components/styles, six navigable views, workflow, state/route contract, source drawer, glossary and responsive shell. No fake research values should be needed because W1 exports already exist.

**Exit gate:** all six views, both headline actions, workflow branches, default/reset and reloadable hash routes work; the first screen explains the invention and validation status; unsupported/failing data produces a scoped message rather than an invented result or a blank app.

## W3 — Recorded acquisition replay

**Goal:** let a visitor explore all five policies and splits at the exact recorded batch boundaries.

### Work

1. **W3.1 — Comparison controls:** implement aggregate plus five seed choices, all five policy toggles and a separate inspected-policy selector for details. Default to Quality versus Full. Use documented names for the underlying policy enums.
2. **W3.2 — Curves and metrics:** show historical near-stable hits, precision and chemical-system coverage at 0/10/20/30/40/50 queries. Mean/sample SD is computed across five split outcomes, not across query events. Distinguish the shaded acquisition variability from a predictor's calibrated radius. Show descriptive split dependence.
3. **W3.3 — Batch state machine:** implement play, pause, next batch and reset. A teaching step can first inspect the recorded pre-selection predictions, then reveal that batch's recorded labels and advance completed budget. Do not interpolate unmeasured budgets or imply per-query refitting. Cancel timers during incompatible state changes or unmounts.
4. **W3.4 — Query drawer:** display the ten records for one seed/policy/batch with formula/system, recorded mean/radius, role, diversity, optional score, and revealed target. Clearly identify selections only; this is not the complete candidate pool. Preserve empty random scores and unavailable fields.
5. **W3.5 — Aggregate and zero states:** aggregate mode has no individual event history, so its candidate playback/drawer is disabled with an explanation. At zero queries, hits/system coverage are zero and precision is unavailable. The selected split can inspect the first batch's saved predictions without claiming that those labels have already been revealed in the replay UI.
6. **W3.6 — Truthful reveal:** pre-reveal hiding affects labels, tooltip text, tables and accessible descriptions consistently. It is a pedagogical display state, not access control: historical outcomes exist in the public static data. No replay control changes the frozen model, calibration, policy coefficients or scientific dataset.
7. **W3.7 — Share/export:** preserve view/seed/policy/budget in permalinks, integrate source details and offer the small displayed-data CSV. Define columns, units, source IDs and null meanings; test downloads against the current filtered selection.

**Deliverables (completed):** replay view, chart components, batch controller, query drawer, state transitions and replay/download acceptance results. See the [replay contract](contracts/REPLAY_CONTRACT.md) and [W3 closure](reports/W3_COMPLETION.md).

**Exit gate:** all 25 seed/policy histories reconstruct 50 queries in five batches; counts/precision/coverage match source endpoints and intermediate curves; no extra timer advances occur after switching/resetting; aggregate mode invents no history; pre-reveal UI and zero-query behaviour remain correct.

**W3 acceptance:** 45,871 independent replay checks, 458 playback checks, 687 checks of five actual CSV downloads and 43 browser checks passed. Existing shared-state, runtime-guard, frozen-research and production-copy checks also passed. The data release and all 103 source files remain unchanged. Screenshot capture and native hidden-page event delivery could not be exercised by the available browser; source/controller verification and responsive DOM checks are recorded separately, with broader device/visual checks retained for W6. Optional O1 is deferred explicitly; no core W3 exit item remains open.

## W4 — Crystal Lab and saved-stage navigation

**Goal:** display real structures accurately and make their distinct methods and evidence levels understandable.

### Work

1. **W4.1 — Catalog and selection:** list all eleven model-result records and the core excluded example with method/eligibility/stage metadata. Fully implement the known MgO sequence, both MgO/TiO2 control pairs, CHGNet CaMg2O3 prototype and excluded twelve-atom transformer example. Additional rich reference/prototype viewing is tracked as optional enrichment; their results remain in the catalog/evidence regardless.
2. **W4.2 — Three.js integration:** lazy-load a shared viewer, unit-cell edges and species-coloured atoms. Implement rotate, zoom, reset, atom inspection and a legend. Avoid duplicate continuously running hero/lab renderers; pause when hidden and dispose controls/resources when unloaded.
3. **W4.3 — Geometry fidelity:** preserve lattice shape, physical units, source atom count and site identity. Validate fractional-to-Cartesian conversion, cell determinant/volume, periodic distances and roundtrip behaviour on actual non-cubic examples as well as MgO. Display wrapping is disclosed. Core need not draw bonds; any later heuristic bonds/images are labelled visual aids.
4. **W4.4 — Stage identity:** select only recorded stages from the W1 registry. A prototype does not become a later state of an excluded CrystalFormer structure. A two-atom reference is not an eight-atom model cell's fictitious later frame. Side-by-side comparison is explicit; no invented morph or unsupported relaxation trajectory is animated.
5. **W4.5 — Metadata and comparison:** display formula, physical atoms, method, stage, eligibility, SG with stage-specific tolerance, and optional engine-qualified energy. Enable energy comparisons only for scientifically comparable records of the same composition/engine/settings scope. The two saved symmetry energy pairs keep their one-per-arm scope; unavailable DFT stages remain unavailable.
6. **W4.6 — Accessible fallback:** provide the actual figure, metadata and coordinate table for missing WebGL, renderer errors or context loss. Implement keyboard camera controls/reset, mobile touch behaviour that does not trap page navigation, opt-in auto-rotation and reduced-motion behaviour. Record whether full interactive viewing was implemented, independently of runtime fallback working.
7. **W4.7 — Structure export:** download the selected saved structure in the chosen supported text/CIF form, with stage/source identity. Validate exported species/lattice/coordinates by roundtrip; do not imply newly optimized geometry. A browser-generated download may avoid relying on an unverified hosting file extension, but must represent the same checked data.

**Deliverables (completed):** crystal catalog, shared viewer, stage selector, camera/atom controls, metadata/coordinate view, fallback and checked structure export. See the [geometry/export contract](contracts/CRYSTAL_CONTRACT.md) and [W4 completion report](reports/W4_COMPLETION.md).

**Exit gate:** every core example and both control pairs can be inspected; actual cells and stage identities match the registry; ineligibility never disappears when an excluded geometry is drawn; unavailable stages cannot be selected; non-orthogonal geometry, keyboard/touch and context-loss checks pass.

**W4 acceptance:** 7,060 geometry/export checks, 288 renderer lifecycle/camera checks, 524 checks of six actual downloaded CIFs and 69 browser checks passed. All 26 saved stages rendered in real WebGL2. Actual context loss, draw failure, missing WebGL/chunk/data and retry paths passed. Responsive layouts, keyboard camera/site selection, simulated reduced motion and touch-pointer page-pan behaviour were checked. Screenshot capture, physical touchscreen testing and native hidden-page delivery remain explicit verification limits for W6's broader pass. All 103 research inputs and the frozen release remain unchanged. Optional O2 is implemented for every current registry stage. No core W4 functional exit item remains open.

## W5 — Scientific findings, evidence and reproducibility

**Goal:** implement every remaining scientific view and expose the limitations as part of the demonstration.

### Work

1. **W5.1 — Primary symmetry:** toggle MgO/TiO2 and show both first-eight arms with raw valid/unique counts and percentages. Keep the same-architecture/different-conditioning explanation visible. Nontrivial validity is not automatically a unique-yield or architecture-causal improvement.
2. **W5.2 — Supplement and energies:** show supplementary MgO in its own tab and the two selected model-energy pairs in a distinct panel. Label supplemented MgO versus primary TiO2, one structure per arm, CHGNet units and known-phase matches. Include the anatase/rutile reference ranking as a within-TiO2 model result, without a DFT ground-state claim.
3. **W5.3 — Six composition cohorts:** make every formula selectable with attempts, exact-cell failure counts, eligibility reasons and larger-cell diagnostics. Preserve 0/48 and all twelve exclusions. Explain exact-cell workload/representation filtering without calling the rejected structures physically unstable.
4. **W5.4 — Prototypes and novelty:** present all four prepared prototypes separately from transformer outputs. Show historical composition absence and the partial 15/23 MgO, 34/44 TiO2 geometry coverage. Do not infer global novelty, generator-pretraining OOD or DFT stability from those results.
5. **W5.5 — Reliability:** implement split and endpoint controls, empirical versus nominal 90% coverage, interval width/error context and explanations. Core endpoints are Initial, Quality and Full; expose other saved policies through the planned advanced selector. Initial uses `initial_shared` once per seed.
6. **W5.6 — Selective risk:** implement recorded 10%-100% retained-fraction steps, actual row count/fraction, MAE and all-row comparison. Tie these to the selected endpoint and seed; aggregate only comparable records. Identify the diagnostic subset rather than claiming improved complete-population predictions or a newly tested acquisition policy.
7. **W5.7 — Role diagnostics:** add the expandable conservative/optimistic breakdown, counts/radii and nonrandomized-role caveat. Preserve 140/175 versus 7/75 without offering an untested live mixing-ratio/calibration control.
8. **W5.8 — Complete DFT ledger:** render all nineteen jobs with filters for role/stage/status. Keep process completion, SCF acceptance, final stationarity and full finite sensitivity validation separate. Filters show their result count against the nineteen-job total. Missing terminal measurements remain null/unavailable.
9. **W5.9 — Accepted versus incomplete evidence:** identify three fully checked relaxed geometries but two accepted primary source IDs. Show primary 2/161 and fallback 1/57 coverage, incomplete 900-second perturbation, missing metal/O2/spin cases and no complete hull or newly established stable material. Reference tables count system memberships, not incorrectly deduplicated materials.
10. **W5.10 — Claims, methods and sources:** implement the claim/evidence matrix, glossary links, frozen-study date, source drawer, public-safe methods/report content and attribution. The raw MgO/reference difference is numerically unresolved; no cross-engine/cross-composition energy ranking is offered. Include failed/excluded outcomes rather than only accepted examples.
11. **W5.11 — Downloads and publication links:** provide displayed-table CSV and selected structure exports, source/units/null descriptions, and small relevant research figures. Use external verified destinations for full archives, large PDFs and video. Repository/write-up/video buttons stay honestly unavailable until those separate assets exist; all internal evidence paths resolve through public source IDs rather than local machine URLs.

**Deliverables:** symmetry/composition, reliability/risk/role, DFT, claim/method/source and download components, all connected to the shared route/state and crystal/replay views.

**Exit gate:** every headline fact and table row traces to a verified source; all six proposals/four prototypes/nineteen QE jobs remain accessible; primary/supplementary, model/DFT, geometry/reference-ID and historical/global-novelty distinctions survive filtering and export; no claim exceeds the evidence.

**W5 closure:** all eleven tasks are implemented. See the [findings/evidence contract](contracts/FINDINGS_EVIDENCE_CONTRACT.md), [independent requirements review](reports/W5_REQUIREMENTS_REVIEW.md) and [completion evidence](reports/W5_COMPLETION.md). Independent checks passed: generation 3,835; uncertainty 55,470; evidence 2,136. Eighteen actual analysis CSVs across thirteen table kinds and 480 rows passed 420 download checks. Final browser/build measurements are recorded in the linked completion evidence. Optional O3 uses all 300 saved decile rows; no new calibration, model fitting or scientific run was introduced. W6 integrated presentation/QA is complete; W7 hosting remains planned.

## W6 — Integrated validation, guided tour and local release

**Goal:** establish a complete, reviewable local production build with recorded verification before any upload.

### Work

1. **W6.1 — Data/science assertions:** run W1 checks against the final exports and UI selections. Independently reproduce source aggregates, sample SD, inclusive thresholds, eV/meV conversions, joins and stage availability. Test real boundary cases: zero queries, null scores, failed terminal SCF, excluded geometry and overlapping inventories. Do not refit/re-run experiments to test the site.
2. **W6.2 — Integrated interaction checks:** exercise all seed/policy/batch controls, aggregate detail disabling, reset, timers, route changes, browser back/forward, filters, stage selectors, downloads and source drawers. Test deep-link reloads and invalid URLs/data. Ensure current displayed values and downloads agree.
3. **W6.3 — Accessibility and browser QA:** check Chrome/Edge, desktop and a mobile viewport; expand browser coverage where available. Verify keyboard focus after navigation/drawer close, labelled controls, readable contrast, non-colour status cues, chart tables/descriptions, reduced motion, intentional table scrolling and usable viewer fallback/context loss. Record any untested browser/device explicitly.
4. **W6.4 — Performance:** lazy-load heavy charts/viewer, render only while visible, cap mobile pixel ratio, use relevant compressed images and system fonts. Measure an initial transfer goal below 1 MB and a complete curated payload around/below 10 MB excluding external media. Scientific/runtime data is same-origin HTTPS. Do not add a service worker/PWA or runtime CDN dependency to solve packaging.
5. **W6.5 — File/release gate:** validate uncompressed per-file sizes. Retain conservative limits from the website plan: JS chunks <900 kB, data shards <500 kB, images normally <300 kB; enforce the provider's HTML/PHP/JS, other-file and `.htaccess` caps when applicable. Verify no missing chunks, credentials, admin-session URLs, absolute local paths, model checkpoints or scientific environments enter the payload. Keep licence/attribution notices.
6. **W6.6 — Release coherence:** assign one UI build ID and export-manifest version, with immutable/content-hashed data and images. A release manifest records all public files/hashes and the source-study identity. Test that an older cached entry continues to resolve its own assets/data when a new release is prepared; a fixed-name JSON path must not mix versions.
7. **W6.7 — Guided tour:** implement start/pause/next/previous/exit for the six-step three-minute script below, including exact view/filter/stage presets and return to ordinary browsing. Tour transitions change presentation state only, stop conflicting autoplay and respect reduced motion. Rehearse against the production build, not only the development server.
8. **W6.8 — Handoff:** save the source/data/science and browser-check results, representative screenshots, measured bundle sizes, final optional/deferred-item register and local release package. Document how to run an HTTP preview and rehearse it as a fallback if hosting is unavailable. The website supports but does not itself complete the one-page write-up, recorded video, repository publication or hackathon submission.

### Required tour sequence

| Time | View and interaction | Scientific point |
|---|---|---|
| 0:00-0:25 | Overview and clickable workflow | Integrated prototype and separate historical/fresh tracks |
| 0:25-1:10 | Five-batch Quality/Full replay | Broader coverage, fewer historical near-stable hits |
| 1:10-1:45 | MgO, CaMg2O3 prototype and excluded twelve-atom draw | Actual structures and distinct validation/eligibility stages |
| 1:45-2:15 | Primary symmetry yields and selected energy pair | Conditioning contrast; one-pair energy scope |
| 2:15-2:40 | Coverage and retained-fraction controls | Empirical uncertainty and selective-risk limits |
| 2:40-3:00 | Real QE table and sources | Known recovery, incomplete inventory/perturbation, reproducibility |

**Deliverables (completed):** [QA report](QA_REPORT.md), [integration/source validation](reports/W6_INTEGRATION_VALIDATION.json), production `dist/`, [local package/file inventory](reports/W6_RELEASE_PACKAGE.json), [release gate](reports/W6_RELEASE_VALIDATION.json), [guided-tour contract](contracts/GUIDED_TOUR_CONTRACT.md) and [local preview/rehearsal instructions](LOCAL_PREVIEW.md).

**Exit gate:** all core requirements below pass with linked verification; no required control remains a decorative placeholder; production navigation/data/viewer/fallback/downloads/tour work; parent research hashes remain unchanged. Status may become **local release ready**, never automatically **live deployed**.

**W6 closure:** all eight tasks are complete for the local release. [Completion evidence](reports/W6_COMPLETION.md), [QA](QA_REPORT.md), [independent review](reports/W6_REQUIREMENTS_REVIEW.md), [source integration](reports/W6_INTEGRATION_VALIDATION.json), [tour checks](reports/W6_TOUR_VALIDATION.json) and [release verification](reports/W6_RELEASE_VALIDATION.json) record final results. Eleven fresh source/science/state/geometry/lifecycle lanes passed 224,507 assertions; exact final browser/download/tour/gate counts, build identity, transfer measurements and screenshots belong to the linked reports. Counts describe verification contexts, not independent scientific observations. All frozen research and historical W1-W5 evidence remain unchanged.

The available in-app browser was exercised at desktop and mobile viewports. Chrome and Edge access was attempted but unavailable; physical touchscreen devices and other unexercised native/browser behavior remain explicitly untested. This is the documented coverage disposition, not a cross-browser certification. W7 must repeat the required checks against the actual HTTPS deployment. Optional O1 stays deferred, O2/O3 are implemented, O4 extra camera trajectories/effects are excluded, and O5 records only actual available browser coverage and disabled unavailable publication destinations. No deployment was performed.

## W7 — InfinityFree release and verified live deployment

**Goal:** serve the checked release at [theflamelproject.42web.io](https://theflamelproject.42web.io/) and retain a safe, reproducible rollback path.

### Work

1. **W7.1 — Account inspection:** use the current authenticated account dashboard/File Manager or configured FTP access. Confirm the exact domain mapping, assigned document root, current HTTPS state and existing website contents. Management URLs alone do not prove working authentication. Do not reuse or publish the supplied session-specific installer URL; no installer is needed for the static app.
2. **W7.2 — Backup:** save the existing entry point and files being replaced, plus any necessary prior release inventory. Preserve unknown account/control-panel files. Keep rollback material locally and out of the public bundle.
3. **W7.3 — Final packaging:** reproduce the checked export/build/release gate using pinned tooling. Confirm the target payload is the contents of `dist/`, with the entry file at the verified document root rather than a nested `dist` folder. No source environment, `node_modules`, complete study archive or scientific executable is uploaded.
4. **W7.4 — Upload order:** upload the new immutable assets, data, images and manifest first; verify their presence/size, then replace entry HTML last. Preserve prior versioned files for cached-page clients and rollback. Avoid broad cleanup/deletion during the event. If the host requires a specific upload method, adapt the release procedure without changing research data or claim rules.
5. **W7.5 — Browser verification:** check the exact public HTTPS URL in a fresh normal browser session, allowing the provider's standard browser verification. Verify release ID, same-origin data/chunks, all six views, core interactions, viewer/fallback, mobile view, hash deep links, downloads and source links. Check console/network/mixed-content errors and files that may have been discarded by size limits. A failed automated text fetch is not sufficient evidence that the site is down.
6. **W7.6 — Rollback/retest:** if the live release fails, restore the saved entry/payload and verify the restored public state. Diagnose the website/build/host issue; do not alter a scientific result to hide it. Retest only changes that address the observed issue.
7. **W7.7 — Completion record:** retain deployed build ID, release/data manifest hashes, timestamp, verified URL, public-directory mapping, actual upload method, live check results and rollback instructions. If account/network/HTTPS access is unavailable, keep the tested local release ready and record W7 as awaiting the missing access or external condition; do not report deployment success.

**Deliverables (completed):** deployed static files, [deployment record](DEPLOYMENT_RECORD.md), [completion](reports/W7_COMPLETION.md), [live QA](reports/W7_LIVE_BROWSER_QA.json), [effective/physical inventory](reports/W7_FINAL_REMOTE_INVENTORY.json), exact base/host manifests and local rollback copies.

**Exit gate:** a fresh browser loads the declared build and complete core on the supplied HTTPS domain, with verified data/structure identity, working links/downloads and a recoverable prior payload. Only now is **live deployed and verified** accurate.

**W7 closure:** all seven tasks complete. Final public HTTPS acceptance passed41targeted browser checks,302actual-download checks and315final inventory checks;1,262local integrity checks preserve all frozen research and historical W1-W6 evidence. All26saved stages and three Findings figures passed runtime image integrity after33opaque sidecars and two steady host configs repaired image transport. The identical entry was republished last. Raw initial failures and verification limits remain explicit. [Completion](reports/W7_COMPLETION.md), [live QA](reports/W7_LIVE_BROWSER_QA.json) and [deployment/rollback](DEPLOYMENT_RECORD.md) bind the final outcome.

## Acceptance and coverage matrix

This matrix maps every section of the website plan to execution and verification. It complements, rather than replaces, the detailed tasks above.

| Website-plan requirement | Implementation owner | Acceptance evidence |
|---|---|---|
| §1 purpose, headline/actions, recorded prototype and correct invention framing | W2; W6 review | First-minute narrative and action/navigation check |
| §2 all six views, explanations and persistent navigation | W2-W5; W6 | Six-view and responsive-navigation checks |
| §3 visual direction, real imagery, typography, colours, desktop/mobile layout | W2/W4; W6 | Desktop/mobile screenshots and contrast/legibility review |
| §4A seven-stage workflow, historical/fresh split, empty path, MgO control and prototypes | W2 | Each node/branch opens correct real input/output/status |
| §4B five seeds/policies, aggregate mode, batch controls and three metrics | W3 | All 25 histories, zero state, aggregate sample SD and endpoint checks |
| §4B ten-selection details, reveal ordering, selected-only scope and no aggregate history | W1/W3 | Joined records, drawer fields and reveal/timer tests |
| §4B optional scatter | O1, W3 enrichment; W6 disposition | Explicitly implemented/tested or recorded deferred |
| §4C real viewer, camera/atom/cell controls, core examples and both pairs | W1/W4 | Registry, geometry conversion and core viewer checks |
| §4C stage availability, eligibility labels, engine/units and no fictitious trajectories | W1/W4 | Stage identity and comparison eligibility checks |
| §4C accessible figure/metadata/coordinate fallback and reduced motion | W4/W6 | Missing-WebGL/context-loss and keyboard/mobile checks |
| §4C additional rich model/reference examples | O2, W4 enrichment; W6 disposition | All11 results remain in catalog; extra viewer scope documented |
| §4D primary versus supplementary yields, unique counts and model energies | W5 | Raw counts/percentages, pair scopes and source comparison |
| §4D six formula cohorts, all exclusions and four separate prototypes | W5 | Formula/method filters preserve 0/48 and twelve diagnostics |
| §4E coverage, endpoints, retained fractions/row counts and methods formula | W1/W5 | Saved reliability/retention and enum/units checks |
| §4E advanced saved policies and nonrandomized role breakdown | W5 | All available policy endpoints; 140/175 vs7/75 with scope |
| §4E richer decile visualization | O3 implemented in W5; W6 integrated review | All 300 saved rows available by selected split/endpoint with numeric table and CSV; no new calibration |
| §4F all19 QE jobs, acceptance layers, three geometries/two source IDs and missing coverage | W1/W5 | Complete ledger and source/reference membership checks |
| §4F claim matrix, attribution, sources, downloads and eventual publication links | W1/W5-W7 | Claim traceability, export contents and verified/unavailable link states |
| §5 every fact and claim rule | W1-W6 | Frozen fact/source comparison and scientific review |
| §6 local static architecture, tooling, routes and hosting/runtime boundary | W1/W2/W6/W7 | Pinned local build, reloadable hash routes, static-only release |
| §7 provider limits, same-origin data, browser verification, document root and external media | W1/W6/W7 | Size/release check and live normal-browser check |
| §8 curated sources, strict schemas, selected metadata, registry, units, nulls and provenance | W1; W3-W6 enforcement | Export validator, source IDs and unchanged-parent hash record |
| §8 release-pinned data/images and study/export/build identities | W1/W6/W7 | Manifest coherence, cache-version and build identity checks |
| §9 folder boundaries and excluded tooling/credentials/backups | W1/W6/W7 | Package file inventory and parent integrity check |
| §10 W1-W7 dependencies, estimates, core/optional/fallback distinction | This plan; W6/W7 status | Phase completion record, scope register and honest milestone names |
| §11 exact three-minute guided tour with normal browsing exit | W6 | Timed six-step tour rehearsal and exit/reset check |
| §12 scientific fidelity, interaction, accessibility, failure handling and performance | W1 onward; W6 gate | QA report, actual test results and documented verification limits |
| §13 account/root/HTTPS, rollback, upload order and live deployment checks | W7 | Deployment record, browser result and rollback payload |
| §14 full definition of done, local/live distinction and excluded backend work | W6/W7 | Local release-ready versus live-verified status; no unsupported capability claim |
| §15 primary references and dependency/hosting verification | W1; W7 recheck | Toolchain/source notes and provider checks for actual deployment |

### Optional enrichment register

Every original optional feature remains assigned. Optional status does not permit omitting a core feature or its scientific limitations.

| ID | Feature | Assigned work | Conditions and disposition |
|---|---|---|---|
| O1 | Scatter view of selected queries, or a genuine saved pre-reveal pool | Deferred at W6 closure | The selected-query table and policy curves satisfy the core comparison. A full-pool plot would require archived pool inputs/allowlist and added payload; no selected-only scatter is relabelled as a complete pool. |
| O2 | Rich viewer coverage of every additional prototype/reference | Implemented in W4 | All 14 entities and 26 saved stages have working stage selection, 3D, metadata, coordinate view and export, including all 11 model-result records. Actual browser stage coverage and independent roundtrips are recorded in W4 evidence. |
| O3 | Rich uncertainty-decile comparison | Implemented in W5 | All 300 saved decile rows across thirty split/endpoint contexts have a disagreement/error plot, width/coverage table and checked CSV; no new fitting or arbitrary nominal-level slider. |
| O4 | Extra visual polish/camera effects | Extra trajectories/effects intentionally excluded at W6 closure | Core camera controls, orientation readout and opt-in rotation are implemented. Extra trajectories/effects are excluded to preserve accessibility, performance and the distinction between saved snapshots and measured scientific evolution. |
| O5 | Additional browser/device coverage and publication embeds | W6 and W7 actual available-browser coverage recorded | In-app browser desktop/mobile viewports verified; Chrome/Edge access attempted but unavailable; physical devices and other untested environments remain explicit limits. Repository/write-up/video controls remain disabled until public assets exist and are checked. |

W6 has recorded each optional item as implemented with evidence, deferred with reason, or intentionally excluded with explanation. Core completeness and optional-enrichment status are reported separately.

## Commands and records

W1 provides working scripts for data export/validation, strict TypeScript checks, loader integrity checks, Vite build/preview and build-copy verification. Actual commands are documented in the [implementation README](README.md). W6 commands provide fresh source/interaction validation, guided-tour checks and final local packaging; W7 deployment and live verification are complete; the deployment record preserves actual coverage and recovery details.

The W1 implementation status, export schema/registry, source mapping and validation records now accompany these planning documents. W2-W6 now add their interaction QA and final local UI release records; W7 adds the verified deployment record and host-adapter recovery package. Each phase report states what changed, what was actually checked and what remains unavailable. Public credentials and session URLs never become part of those records.

The [website plan's primary references](WEBSITE_PLAN.md#15-primary-implementation-references) remain the implementation/hosting sources. The scientific facts continue to come from the frozen study and [verified source inventory](research_sources.json). The website is a demonstration and analysis interface for that evidence, not an additional experimental result.
