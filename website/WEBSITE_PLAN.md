# The Flamel Project: interactive research website plan

Prepared 22 October 2026. Working project name: **The Flamel Project**, inferred from the supplied domain. Target: [https://theflamelproject.42web.io/](https://theflamelproject.42web.io/).

This is the website's experience and scope plan. W1-W6 are complete: verified data/setup, six-view narrative/shared shell, recorded acquisition replay, interactive Crystal Lab, complete findings/evidence, integrated QA, the three-minute guided presentation and a checked local release. W7 deployment is complete; the site is live deployed and verified. [Deployment/rollback record](DEPLOYMENT_RECORD.md) and [W7 completion](reports/W7_COMPLETION.md) retain actual evidence. The scientific source of truth is the [Phase 6 integrated report](../reports/phase6_report.md), [readiness record](../artifacts/phase6/readiness.json) and [frozen evidence](../artifacts/phase6/numerical_freeze.json).

Reviewed before implementation on 22 October 2026. The [phased implementation plan](PHASED_IMPLEMENTATION_PLAN.md) turns every section below into W1-W7 tasks, deliverables and acceptance gates. [Implementation status](IMPLEMENTATION_STATUS.md) records W1-W7 completion and live verification. The coverage matrix also tracks optional enrichment so it cannot disappear silently. Replay scatter O1 is deferred; rich saved-stage coverage O2 is implemented for all current registry entities/stages, and uncertainty-decile enrichment O3 is implemented for all 300 saved rows across thirty split/endpoint contexts. O4 extra camera trajectories/effects are intentionally excluded for accessibility/performance and faithful saved-stage presentation. O5 records only available in-app-browser desktop/mobile viewport coverage; Chrome/Edge access was attempted but unavailable, physical devices remain untested and publication controls remain disabled. See [W6 completion](reports/W6_COMPLETION.md), [QA](QA_REPORT.md), [local rehearsal](LOCAL_PREVIEW.md) and the [findings/evidence contract](contracts/FINDINGS_EVIDENCE_CONTRACT.md).

## 1. Purpose and central experience

Build an interactive research exhibit that lets a hackathon judge understand the idea in one minute, explore the experiments in three minutes, and inspect the supporting evidence afterward.

The invention being demonstrated is the integrated prototype: symmetry-conditioned crystal generation, uncertainty-aware acquisition, model relaxation, genuine DFT validation and an auditable evidence trail. It combines pretrained CrystalFormer and separate predictive/selection components. It is not presented as a newly trained transformer architecture.

Suggested headline: **Explore the search for new crystals.**

Suggested supporting copy: **An interactive research prototype connecting symmetry, predictive uncertainty and first-principles validation. Explore what worked, what failed, and what the evidence supports.**

Primary action: **Explore the experiment**. Secondary action: **Inspect the crystals**.

The main experience uses recorded experiment replay, real structures and interactive analysis. The site runs on exported frozen data. A visitor changes the displayed seed, policy, batch or structure; these controls do not launch CrystalFormer, train predictors, execute CHGNet or submit QE jobs. Replay controls must be labelled accordingly.

## 2. Visitor journey and navigation

Use a clear narrative landing page with linked interactive views. A persistent navigation bar has **Overview**, **Workflow**, **Replay**, **Crystal Lab**, **Findings**, and **Evidence**. Add a compact **Guided tour** control for the live presentation.

| View | What the visitor learns | Main interaction | Priority |
|---|---|---|---|
| Overview | What we built and why uncertainty/symmetry matter | Rotate the actual known-MgO example; enter tour | Core |
| Workflow | How proposal, generation, screening and validation connect | Click each stage to inspect its inputs, outputs and status | Core |
| Replay | How five acquisition policies performed under equal historical label budgets | Select split/policy and step through five batches | Core |
| Crystal Lab | What the structures look like and which stages they actually reached | Select material, method and available saved stage in a 3D viewer | Core |
| Findings | What symmetry, uncertainty and composition experiments established | Switch controls, compare policies, explore retained-fraction diagnostics | Core, with deeper diagnostics after primary views |
| Evidence | How claims trace to records and where validation is incomplete | Filter the DFT table, open source details, download displayed data | Core |

Keep an explanatory sentence beside each visualization. Details such as exact hashes and raw IDs belong in an expandable evidence panel rather than every visitor's main reading path.

Provide a short glossary for historical hull distance, near-stable retrieval, calibration radius, exact-cell validity, unique structures, reference coverage and model versus DFT energies. The replay's near-stable definition is the signed historical WBM/MP hull target **<=0.05 eV/atom**; historical on/below-reference-hull hits use **<=0**. Neither is a fresh website-generated DFT result.

## 3. Visual direction

Use a research-notebook aesthetic: warm off-white backgrounds, dark graphite text, copper accents and a deep blue for selected controls. Dark panels can frame the crystal viewer. Charts keep consistent policy colours across views, matching existing figures where practical.

Use a distinctive editorial introduction, a workflow diagram, charts, a large crystal workspace and an evidence table. Avoid repeating identical feature-card grids. Suggested typography: a restrained serif headline, system sans-serif UI and monospace numerals for coordinates/energies. Start with system fonts so the presentation does not depend on a font service.

The visual centrepiece should be an actual saved crystal. Use camera movement and highlighted atoms, not invented molecular artwork or graphics suggesting a newly discovered material. Retain generated, model-relaxed, DFT and excluded status labels beside the visual.

Design for desktop presentation and mobile browsing. On narrow screens, stack chart and explanation, replace dense side panels with accessible drawers, and retain readable data tables through deliberate horizontal scrolling.

## 4. Interactive features

### A. Clickable discovery workflow

Display **Propose → Generate → Screen → Select → Relax → Validate → Compare**. Clicking a node opens a short explanation and a real output example.

Show two connected scientific tracks: the historical acquisition benchmark and the fresh crystal/validation workflow. Historical WBM hull labels and fresh QE energies have different targets; they must not appear to be interchangeable feedback labels.

The new-formula path visibly ends with zero eligible transformer candidates. A separately labelled branch shows the predetermined known-MgO validation control. Prototype substitution is another clearly named baseline branch, not a replacement generator outcome.

### B. Acquisition replay

- Choose one of the five frozen seeds, or the aggregate view.
- Toggle Random, Quality, Quality + Diversity, Uncertainty and Full.
- Use **0, 10, 20, 30, 40, 50 queries** as the slider steps, matching recorded batches. Provide play, pause, next batch and reset.
- Update historical near-stable hits, precision and chemical-system coverage together. Aggregate plots show means and sample SD, labelled as five overlapping splits rather than independent experiments.
- At zero queries, hits and queried-system coverage are zero; precision is unavailable until a query exists, rather than a measured zero percent.
- For a single seed/policy, open the ten recorded selections in a batch. Show saved predicted mean, calibrated radius, role, diversity and subsequently revealed historical target when available.
- A pool scatter plot is optional. The core only needs selected-query records; do not label a selected-only scatter as the complete candidate pool.
- The replay timeline distinguishes pre-selection prediction from subsequent historical-label reveal. It does not imply a refit after every individual query.
- The aggregate view disables individual-candidate playback, because no single aggregate query history exists.

The default should compare Quality and Full across all seeds, exposing the actual negative result immediately. Do not choose a favourable seed to imply an improvement.

Use separate state for multi-policy chart comparison and the single policy whose recorded batch is inspected. Cancel autoplay and pending reveal transitions when seed, mode, inspected policy or route changes. Reset restores aggregate Quality-versus-Full at 50 queries with playback paused. Batch teaching mode can show predictions before revealing its recorded outcomes, but hiding labels is a presentation device: these historical labels are shipped as public static data, not protected secrets.

### C. Crystal Lab

Use a Three.js viewer with rotate, zoom, reset camera, unit-cell edges, species legend and atom details. Load actual saved lattice matrices, species and fractional coordinates. Convert to Cartesian positions without changing the scientific geometry; identify any coordinate wrapping used solely for display.

Core examples:

1. Generated eight-atom MgO and its available CHGNet/accepted QE states: known-phase recovery.
2. The MgO and TiO2 symmetry/P1 pairs: one selected structure per arm, model energies only for the comparison.
3. The six-atom CaMg2O3 prototype after CHGNet: model-relaxed baseline, no fresh candidate DFT.
4. The twelve-atom CaMg2O3 transformer draw: correct reduced composition but excluded by the frozen six-atom gate.

Allow additional prototype/reference structures from the eleven verified model results after these examples work. Stage selectors expose only stages that exist for that specific candidate; unavailable DFT states are disabled and explained. Do not create fictitious intermediate states or interpolate a scientific relaxation trajectory that was not saved/exported.

Show formula, actual atom count, method/stage, space group, and appropriate energy units. An excluded example remains marked excluded even while its valid geometry is displayed. Avoid raw energy comparisons across chemical compositions or engines.

Build a candidate/stage registry before the viewer. Link a stage through its recorded source/parent IDs, never merely a matching formula. In particular, the eight-atom CHGNet rocksalt reference and the two-atom accepted source-reference QE geometry must not become fictitious successive states of one cell. Keep method, saved stage, experimental eligibility and DFT validation status as separate fields.

The geometry contract specifies lattice row vectors in angstroms, fractional coordinates, species/occupancy, site indices and periodic boundary flags; Cartesian positions are fractional coordinates multiplied by the lattice matrix. Preserve stage-specific symmetry tolerances. The saved CHGNet final-space-group values use symprec 0.01 angstrom and angle tolerance 5 degrees; other stages retain their own recorded settings or an explicit unknown. Verify non-orthogonal cells as well as cubic MgO. Display wrapping, optional images/supercells and any visual-only bonds must not change reported physical atom counts or scientific status. The full catalog includes all eleven model results even if optional richer viewing of every additional reference/prototype is deferred.

If WebGL is unavailable, show a prepared scientific figure, the same structure metadata and an accessible coordinate table. Auto-rotation is opt-in; camera reset and viewer controls remain keyboard accessible.

Handle WebGL context loss as well as initial unavailability. Dispose the viewer when it leaves the page and avoid maintaining separate active hero/lab canvases unnecessarily. A planned fallback makes the site usable on an unsupported device; shipping only the static fallback because the interactive viewer was not completed is a reduced-scope release, not full completion of the 3D feature.

### D. Symmetry and composition explorer

- Toggle MgO/TiO2 and view the two primary first-eight arms with valid and unique counts.
- Put supplementary MgO draws in a separate tab. Never merge their denominator into the primary comparison.
- A separate energy panel shows the selected CHGNet pairs: P1 minus nontrivial +356.879234 meV/atom for MgO and +55.806478 for TiO2, one pair each.
- Explain that both arms use the same symmetry-aware architecture with different conditioning. This does not isolate the effect of training an architecture without symmetry.
- Display all six new-formula cohorts. Clicking a formula exposes exact-cell failures and separately labelled larger-cell diagnostics.
- Show four prepared prototype baselines as a distinct method. Their convergence does not increase the transformer's 0/48 success count.

### E. Uncertainty explorer

- Select split and Initial/Quality/Full endpoint for the core view; other saved policies can be exposed through an advanced control.
- Compare nominal 90% interval coverage with its empirical value. Show both over-coverage and under-coverage across splits.
- Step retained fraction through the saved 10%-100% risk/coverage points, updating MAE and the actual retained row count.
- Explain that filtering an evaluation subset is a selective-risk diagnostic, not a newly trained predictor or an improved acquisition policy.
- Add an expandable role breakdown: Full conservative selections found 140/175 historical hits, optimistic selections 7/75. Roles were not randomized.
- Keep the recorded formula explicit in the methods drawer: radius = q × max(disagreement, 0.01 eV/atom). Do not let visitors change q or the nominal interval level and present that as an executed result.

### F. Evidence and reproducibility

Show a compact claim/evidence matrix and filterable table of all nineteen QE jobs. Distinguish terminal SCF acceptance, final stationarity and complete finite sensitivity validation. A green process exit or `JOB DONE` is not the validation label.

Group the three fully checked relaxed geometries separately: generated known MgO, source MgO reference and source CaO reference. The last two are two distinct source reference IDs. Reference coverage is 2/161 for Ca-Mg-O and 1/57 for Mg-O; the generated MgO does not add a third reference entry.

Make the incomplete 900-second perturbation visible. Display missing-reference coverage and the fact that no full hull or new stable material was established. Add source attribution, methods, frozen-study date and links to the final report/repository when public destinations exist.

Offer small displayed-data CSV downloads and selected structure exports, with source IDs/units included. Keep full archives, large PDFs and video on an appropriate public repository/video platform. Links to an eventual write-up, repository and video remain unavailable until those assets actually exist and are verified.

## 5. Facts and claim rules

| Item | Website must preserve |
|---|---|
| Acquisition | Quality 41.2 ± 2.17 versus Full 29.4 ± 3.65 historical near-stable hits per 50 queries; Full loses in all five paired splits |
| Diversity | Full covers 42.2 chemical systems on average versus Quality 32.8; this is distinct from near-stable yield |
| Calibration | Full endpoint coverage mean 88.88%, range 84.84%-92.10%, nominal 90%; no arbitrary-OOD guarantee |
| Primary symmetry | MgO exact-cell valid 7/8 versus 0/8; TiO2 6/8 versus 1/8; unique yields also shown |
| New compositions | Six absent from the pinned historical MP/WBM composition snapshots; no global novelty or generator-training exclusion claim |
| Fresh generation | 0/48 exact-cell eligible new-formula draws; twelve larger-cell diagnostics remain excluded |
| Model relaxation | Eleven selected CHGNet calculations converged, using ten new launches and one verified cached reuse |
| Structural catalog coverage | Saved geometry check covers 15/23 MgO and 34/44 TiO2 entries; an unmatched output is not globally novel |
| Fresh DFT | Known MgO recovery; tiny -0.005533 meV/atom control/reference difference is numerically unresolved |
| Unfinished validation | Perturbation incomplete; primary references 2/161; fallback 1/57; no full hull |
| Discovery outcome | No newly established DFT-confirmed stable novel material |
| Computational accounting | 88 actual CrystalFormer draws; 96 conservatively charged structure slots; 19 charged CHGNet launches; 19 QE jobs including checks/failures |

Use explicit stage badges such as **Generated**, **CHGNet relaxed**, **DFT validated: known control**, **Excluded**, and **Validation incomplete**. A missing value is **not evaluated** or unavailable, not zero. Prediction, model energy, fresh DFT energy, catalog absence and stability must remain separate concepts.

## 6. Architecture and hosting decision

Recommended stack: **React + TypeScript + Vite**, CSS, **Recharts** for interactive SVG charts and **Three.js** for the crystal viewer. Shared state across the replay, charts and detail panels justifies a small component application. Keep the deployment entirely static.

Vite builds the browser application locally into `dist/`; its preview server is for local checks. InfinityFree's staff explicitly describe hosting a locally built React frontend by uploading its generated files. This does not require Node.js on the host. See [Vite static deployment](https://vite.dev/guide/static-deploy.html) and [InfinityFree's React guidance](https://forum.infinityfree.com/t/can-i-upload-a-full-front-end-react-appliacation/69858).

Node and npm were not found on the current shell PATH during planning. W1 must provide a supported local Node runtime and pin the chosen dependencies/lockfile before implementation; no runtime or package installation has happened yet. Verify the chosen runtime against [Vite's current requirements](https://vite.dev/guide/).

| Layer | Responsibility | Runs where |
|---|---|---|
| Exporter | Read allowed frozen CSV/JSON/geometry files, produce compact website data and provenance | Local existing analysis Python environment |
| UI | Navigation, chart state, batch replay and evidence details | Visitor browser |
| 3D rendering | Saved coordinates, camera and species display | Visitor browser/WebGL |
| Build | Bundle/minify frontend code, split chart/viewer chunks and emit assets | Local Node environment |
| Hosting | Serve the final HTML/CSS/JS/data/images over HTTPS | Supplied InfinityFree account |

Use hash-based client routes, such as `/#/replay?seed=20261022&policy=full&budget=50`, so direct links and reloads do not depend on server rewrite configuration. Load public data from the same website origin. Bundle the libraries locally rather than making the demo depend on runtime CDN access. No database, hosting-side Python, Node server, scientific API or script installer is required for this design.

The supplied installer is an administration facility, not a required application component. Its session-specific URL must not be copied into source, the website, deployment metadata or public documentation. Launch administration tools through a fresh authenticated hosting dashboard when needed.

## 7. InfinityFree constraints checked during planning

The current [official file-limit article](https://forum.infinityfree.com/t/file-size-and-upload-limits/49308) lists 1 MB for HTML/PHP/JS files, 10 kB for `.htaccess`, and 10 MB for other files. Use smaller operational budgets: each generated JS chunk under 900 kB, each data shard under 500 kB, and images normally under 300 kB. Check uncompressed file sizes as well as transfer sizes.

The [browser security documentation](https://forum.infinityfree.com/t/browser-security-system-features-and-limitations/49353) says same-origin browser requests work, while automated/external access may be challenged. Consequently, load local data in the browser and validate the live site in a normal browser. A failed text fetch is not sufficient to classify the website as down. Skip service-worker/PWA features in this prototype.

At planning time, the web reader could not retrieve the public target. W7 subsequently verified authenticated access, the domain's `/htdocs` mapping, existing contents and public HTTPS deployment. The [deployment record](DEPLOYMENT_RECORD.md) retains that evidence. Future releases should recheck the account's actual domain mapping; see [InfinityFree document-root guidance](https://forum.infinityfree.com/t/how-to-locate-root-directory/88595).

Video and large downloads use an external public destination, consistent with the hosting provider's file guidance. Do not upload model checkpoints, virtual environments, QE scratch files or the complete research archive as website assets.

## 8. Data preparation and provenance

The companion [source inventory](research_sources.json) records verified inputs and hashes. W1 implemented `scripts/export_research.py` inside this folder; it reads only a hash-bound allowlist and writes only website exports. Existing research files, reports, ledgers and Phase 6 manifests remain untouched.

The inventory is a verified starting point, not a finished public export or a complete candidate/stage registry. W1 must resolve initial, model and accepted-QE source records through the frozen selection plans, verify each discovered hash, and add only the required geometry/evidence to its explicit allowlist. Source attribution and applicable dependency/data notices are checked before public redistribution.

| Website export | Frozen source | What to extract |
|---|---|---|
| `summary.json` | Phase 6 lane summaries, readiness and numerical freeze | Headline facts, methods, limits and final accounting |
| `replay/curves.json` | Phase 6 uncertainty `learning_curves.csv` and `policy_endpoints.csv` | 125 recorded curve points and 25 endpoints; plot the zero-query origin separately |
| `replay/seed-*.json` | Phase 4 `query_journal_all_seeds.csv` joined to selected-only Phase 2 `features/row_metadata.csv` | Selected-query records grouped by seed, policy and batch; 1,250 total events; formula/system metadata for the 720 distinct queried IDs |
| `uncertainty.json` | Phase 6 evaluation metrics, risk coverage, deciles and role diagnostics | Endpoint reliability and saved diagnostic points |
| `generation.json` | Phase 6 generation cohorts/draws/diagnostics | Primary and supplementary cohorts, six proposal results and exclusion reasons |
| `structures/*.json` | Verified initial/final geometry paths in Phase 6 structure records and figure provenance | Small per-structure geometry plus original source hash and stage |
| `dft.json` | Phase 6 DFT evidence table and inventory completeness | All 19 jobs, three accepted geometries, missing coverage and scope |
| `provenance.json` | Curated source inventory and export process | Source IDs, exact hashes, study timestamp, units, supported claims and export schema |

Export only what the UI needs. The 1,250 query records and small structure set do not require sending the full training set, 7,301 evaluated target IDs, model snapshots or oracle file to the browser. Serialize unavailable measurements as null. Convert non-finite CSV values deliberately rather than producing invalid JSON.

Suggested geometry contract: stable structure/candidate ID, formula, actual atom count, method, stage, lattice matrix, species, fractional coordinates, source hash, optional energy with engine/unit, symmetry with tolerance, and exclusion/validation status. IDs link the stages; every available stage has its own source record.

Define schema versions, public source IDs, strict numeric/boolean/null parsing and canonical units before UI work. Empty random-policy scores stay null, the CSV string `False` becomes false, and unavailable final-SCF measurements are not assigned zero. Preserve full precision in exports and round only displayed values. Serialize study date, export date and UI build ID separately. Shared `initial_shared` evaluation is one initial model per seed, not five independent initial measurements.

Version all data, images and source-index assets with the release, not just JavaScript. A build must load one pinned export manifest; an old cached page cannot silently fetch fixed-name JSON from a newer build. The filenames in the export table are logical names; production resolves them through the versioned/content-hashed release manifest.

Source hashes identify exact files, while validation checks establish scientific status. Do not describe a hash by itself as proof of a valid calculation. Publish a compact traceable evidence index, not a dump of local machine paths or credentials.

## 9. Implementation folder structure

The W1-W7 implementation has the following layout. `dist/` is the unchanged local production base; W7 deployed its effective URLs with a separately inventoried static host adapter. Recovery packages and backups remain under `deployment/` outside the public payload.

```text
website/
  README.md
  WEBSITE_PLAN.md
  PHASED_IMPLEMENTATION_PLAN.md
  research_sources.json
  package.json                 # pinned dependency/build definitions (W1)
  package-lock.json
  index.html
  src/
    App.tsx
    components/                # navigation, badges, controls, source drawer
    views/                     # overview, workflow, replay, lab, findings, evidence
    replay/                    # policy charts, batch playback and query exports
    crystal/                   # shared 3D renderer, geometry and CIF exports
    findings/                  # generation, reliability, risk, roles and deciles
    evidence/                  # DFT/reference filters and CSV projection
    data/                      # typed schemas and local loading helpers
    state/                     # normalized shared hash routes and cancellation
    styles.css
  public/
    research/                  # immutable release manifest, JSON and figures
  contracts/                   # data, route, replay, crystal and findings rules
  reports/                     # dated W1-W7 acceptance and actual downloads
  scripts/
    export_research.py
    validate_export.py
    verify-*.mjs               # source, interaction and production checks
  dist/                        # generated hosting files only
  deployment/                  # W7 host adapter, direct-upload files and local recovery copies
```

Development tooling, login material and backups are excluded from the public bundle. Keep website work in this folder so the frozen research sources do not change.

## 10. Website implementation phases

Use W1-W7 to distinguish these steps from research Phases 1-8. The detailed execution sequence and complete coverage are in the [phased implementation plan](PHASED_IMPLEMENTATION_PLAN.md). Budget **roughly 7-10 hours** for the full core, validation, hosting verification and contingency. A compressed demonstration can target about five hours, but any missing core interaction is recorded as reduced scope. Estimates assume working account access/downloads and are not promised completion times; retain time for the separate hackathon write-up and video.

| Phase | Estimate | Work | Completion condition |
|---|---:|---|---|
| W1: data and setup | 60-80 min | Provide local Node, pin dependencies, define contracts/allowlist and stage registry, export curated data | Counts, joins and source hashes match; no parent research files change |
| W2: narrative and layout | 60-75 min | Build six-view responsive shell, workflow, shared route/state and evidence language | Visitor understands the prototype; defaults, navigation and failure states work |
| W3: replay | 60-75 min | Policy/seed controls, batch/reveal state, charts and selected-query drawer | All 25 histories reproduce recorded metrics and do not invent aggregate events |
| W4: crystal lab | 60-90 min | Real stage registry, geometries, viewer controls, catalog and accessible fallback | Core examples/pairs render correctly; stage/engine/eligibility identities stay separate |
| W5: findings and evidence | 60-90 min | Symmetry/compositions, uncertainty/retention/roles, all QE jobs, claims and downloads | Every required result and limitation traces to a public-safe source ID |
| W6: validation and tour | 45-75 min | Data/science assertions, browser/accessibility/performance checks, tour and local release | Complete core passes locally; any optional deferral is explicit |
| W7: release and host check | 30-60 min | Versioned package, target-directory/HTTPS inspection, backup, upload and live verification | Verified live build identity, interaction results and rollback record |

If time becomes tight, keep one high-quality replay, the core crystal examples, symmetry results and the DFT evidence table. Track richer decile plots, extra viewer detail and extra animation in the optional register. If a core feature must be removed, publish a clearly described reduced-scope demo rather than marking the complete plan done. If 3D compatibility stalls, the real static structure figure/metadata can preserve a useful presentation. Avoid spending the presentation buffer on optional effects.

W1-W6 are complete, including all core interactive views, the six-step guided presentation, integrated source/browser QA, lossless presentation images and a versioned local release package. W7 completed deployment and live verification with a separately recorded static image adapter and recoverable prior content. The [implementation status](IMPLEMENTATION_STATUS.md), [W6 completion report](reports/W6_COMPLETION.md), [QA report](QA_REPORT.md) and [release gate](reports/W6_RELEASE_VALIDATION.json) record actual acceptance and verification limits; the table above retains the original scope and estimates.

This website demonstrates the frozen study and can support the Phase 7 presentation. It does not by itself complete the one-page write-up, recorded video, public repository or final submission.

## 11. A three-minute guided demonstration

1. **0:00-0:25 — Idea:** Show the research question and click through the workflow.
2. **0:25-1:10 — Acquisition:** Replay five batches, compare Quality and Full, and show the broader-coverage/lower-hit outcome.
3. **1:10-1:45 — Structures:** Rotate known MgO, inspect the CaMg2O3 prototype, then reveal why the twelve-atom transformer output was excluded.
4. **1:45-2:15 — Symmetry:** Compare primary control yields; show the one-pair model-energy result with its sampling scope.
5. **2:15-2:40 — Uncertainty:** Demonstrate split-dependent interval coverage and the retained-fraction diagnostic.
6. **2:40-3:00 — Validation:** Open the real QE table, distinguish known-phase recovery from discovery, and end on the evidence/reproducibility links.

The guided presentation implements all six timed sections over 180 seconds with exact recorded view/filter/stage presets, start/pause/resume/previous/next/exit and return to ordinary browsing. Normal page controls and navigation exit the tour; conflicting acquisition autoplay is stopped. Reduced motion suppresses automatic rotation and presentation animation. The [tour contract](contracts/GUIDED_TOUR_CONTRACT.md) and [local thirteen-step rehearsal](LOCAL_PREVIEW.md#thirteen-step-fallback-rehearsal) record the implemented behavior. Tour navigation changes presentation state only; it does not perform a scientific experiment.

## 12. Validation and release criteria

### Scientific fidelity

- Compare website summaries/rounded displays with the exact source values and unit conversions.
- Check five seeds × five policies, five nonzero curve points each, 25 endpoints and 1,250 query events.
- Reproduce selected-batch cumulative hits from existing query records without performing new model inference or acquisition.
- Verify structure atom counts, species, lattice and coordinate roundtrips; stage controls cannot silently point to another candidate.
- Keep primary/supplementary labels, 0/48 eligibility, 12 excluded diagnostics, 11 model results, 19 QE attempts and reference membership counts intact.
- Distinguish three accepted relaxed geometries from two accepted primary source-reference IDs.
- Use measured values and explicit missing-data states. Unmatched catalog geometry, a converged model and a green process exit cannot become a stable/novel-material label.
- Hash the frozen budget/event/manifest files before and after export to confirm read-only use.

### Interaction and accessibility

- Test seed/policy changes, batch boundaries, aggregate mode, reset, stage availability, table filters and downloads.
- Test a complete guided tour and direct/reloaded hash links.
- Check Chrome/Edge and a mobile viewport where available, and record access/coverage limits. W6 exercised the available in-app browser on desktop/mobile viewports; Chrome and Edge access was attempted but unavailable. No physical-device or other untested-browser coverage is inferred.
- Check keyboard focus, labelled controls, text alternatives for charts, tables for important values, contrast and reduced-motion behaviour.
- Test missing/invalid data and unavailable WebGL. A failed panel should show an explanation/fallback without blanking the site.

### Performance and packaging

- Lazy-load the viewer/chart modules; render 3D only while visible and cap mobile device-pixel ratio.
- Target a small initial transfer, ideally below 1 MB, and a complete curated site below roughly 10 MB excluding external media. Measure actual build sizes; these are engineering goals.
- Enforce the per-file budgets above, retain dependency notices, and verify all runtime assets are same-origin HTTPS.
- Ship a release manifest with hashes and a build/source version. Omit credentials, admin-session URLs, research environments/checkpoints and server executables.
- Keep local release-ready and live deployed/verified as distinct statuses. Retain a rehearsed local HTTP-server presentation option if hosting is temporarily unavailable; do not assume `file://` can load application modules/data.

## 13. InfinityFree deployment sequence

1. Complete and review the local build and its validation results.
2. Open the account's current authenticated dashboard and confirm the assigned document root for `theflamelproject.42web.io` and its HTTPS state.
3. Inspect and save the existing website files needed for rollback before replacing anything. Do not remove account/control-panel directories.
4. Reuse the frozen curated research export. Run the documented W6 source validations, `build` (automatic UI-identity preparation, strict TypeScript and production compilation), `w6:tooling`, `release:package` and `w6:release`; see [local instructions](LOCAL_PREVIEW.md). Do not rerun research/export finalizers merely to deploy the website. The checked public payload is the **contents of `dist/`**, or the document-root-relative ZIP recorded in the local package record.
5. Use authenticated File Manager or the account's configured FTP access to upload to the verified document root. Do not upload `dist` as an extra nested directory, `node_modules`, source environments or the whole workspace. Upload new versioned assets/data first and the entry HTML last. Preserve the prior release assets so rollback and visitors with an older cached page can still resolve their pinned data; do not delete unknown hosting files.
6. Verify the exact public HTTPS URL in a real browser. Check a fresh session, chart/data loads, viewer fallback, hash deep links, mobile view, downloads and the absence of mixed-content/JavaScript errors. Check that no file was discarded for size.
7. Retain the deployed build ID/file list and local rollback copy. If validation fails, restore the saved site payload rather than changing the research data to conceal a problem.

The public address and management links do not establish an authenticated deployment session. Implementation can produce the full local release independently; actual upload depends on working account access. No hosting password or session token is needed for the planning task.

## 14. Definition of done for the website

The website is complete when a visitor can understand the idea, replay the actual comparison, inspect real crystals and their available stages, explore the principal findings, and trace claims to evidence; the site works on the supplied InfinityFree domain with explicit validation limits and a reproducible static release.

Live arbitrary crystal generation, fresh DFT submission, accounts, a database and a general conversational assistant are outside the proposed core. They would require additional product/backend work and are not needed to demonstrate this hackathon invention.

## 15. Primary implementation references

- [InfinityFree React/frontend hosting](https://forum.infinityfree.com/t/can-i-upload-a-full-front-end-react-appliacation/69858)
- [InfinityFree file limits](https://forum.infinityfree.com/t/file-size-and-upload-limits/49308)
- [InfinityFree browser verification and same-domain requests](https://forum.infinityfree.com/t/browser-security-system-features-and-limitations/49353)
- [InfinityFree domain document roots](https://forum.infinityfree.com/t/how-to-locate-root-directory/88595)
- [React with a local build tool](https://react.dev/learn/build-a-react-app-from-scratch)
- [Vite static deployment](https://vite.dev/guide/static-deploy.html)
- [Recharts](https://recharts.github.io/en-US/)
- [Three.js installation and controls](https://threejs.org/manual/pages/installation.html)
