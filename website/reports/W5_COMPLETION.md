# W5 complete: scientific findings and evidence

Completed 22 October 2026. All eleven W5 tasks and their functional exit conditions are complete. Optional O3 saved uncertainty deciles are also implemented. W6 integrated QA/presentation and W7 InfinityFree deployment remain planned. No hosting login or upload occurred.

Findings now makes the recorded generation and uncertainty experiments interactive. Evidence exposes the complete QE ledger, missing reference competition, claims, methods and computational accounting. The website preserves the negative acquisition result, failed and excluded generation attempts, incomplete perturbation and absence of a newly established stable material.

## Completed work

| Task | Implemented behaviour |
|---|---|
| W5.1 primary symmetry | Select MgO or TiO2 with both first-eight conditioning arms. Raw valid/unique counts, emitted-draw denominators, fractions and percentages stay visible. The same pretrained architecture with different conditioning is explicit. |
| W5.2 supplement and energies | Separate four-additional-draw MgO cohort; separate supplemented-MgO and primary-TiO2 selected CHGNet energy pairs, one structure per arm. Anatase/rutile remains a within-TiO2 model ranking. No distribution, architecture causality or DFT stability is inferred. |
| W5.3 new compositions | All six formulas and their eight attempts each; exact atom/element counts, eligibility flags, reason counts and geometry. The 0/48 exact-cell shortlist and all twelve excluded larger-cell diagnostics remain inspectable and exportable. Those twelve are within the 48 attempts. |
| W5.4 prototypes and novelty | Four separate substitution baselines, all eleven selected model results and six snapshot-specific catalog searches. Partial 15/23 MgO and 34/44 TiO2 geometry coverage stays explicit. Absence or an unmatched structure is not global novelty, pretraining absence or stability. |
| W5.5 reliability | Five split choices and six saved endpoints: Initial, Quality, Full, Quality plus diversity, Random and Uncertainty only. Observed/nominal coverage, MAE/RMSE, full interval width, calibration scale and disagreement/error association retain units and context. Initial is the single shared zero-query model per split; the other endpoints follow 50 queries. |
| W5.6 selective risk | Keyboard-selectable plot, slider and numeric table for ten saved 10%-100% steps. Actual retained counts/fractions, subset/all-row MAE and ratio are shown. Shared URL state restores the chosen split, endpoint and fraction. This is diagnostic subset selection, with no retraining, new threshold optimization or full-population improvement claim. |
| W5.7 roles | Expandable Full-policy panel with all ten split/role rows, pooled 140/175 conservative versus 7/75 optimistic hits and query-event-weighted radii. Five-split pooling, overlapping populations and nonrandomized allocation remain explicit. |
| W5.8 QE ledger | All nineteen jobs, filtered by role, research phase, calculation and evidence level; result count always against nineteen, including explicit empty states/reset. Exit code, JOB DONE, terminal SCF, stationarity at that job's setting and final finite-check acceptance are separate. Missing terminal measurements remain unavailable. |
| W5.9 incomplete validation | Three accepted relaxed geometries link to their exact saved Crystal Lab stages and CIFs; two source references remain two original material IDs. Primary 2/161 and fallback 1/57 account for overlapping inventory memberships, with 218 memberships and 215 missing. The 900-second perturbation, elemental/O2/spin gaps, absent candidate reaction energy and absent full hull remain visible. |
| W5.10 research account | Ten-row original claim matrix, fourteen source-linked narrative findings, methods, frozen date, glossary, attribution and budget accounting. The tiny raw MgO reference difference remains numerically unresolved; finite checks are not a rigorous total error bound. |
| W5.11 exports and links | Full-precision current-table CSVs with source/release identity, units, null and population/filter semantics. Saved cells use W4's stage-specific CIF path. Relevant original figures are expandable. Repository, one-page account and video controls remain disabled until real public destinations exist. |

Main implementation: [Findings](../src/views/Findings.tsx), [generation explorer](../src/findings/GenerationFindings.tsx), [uncertainty explorer](../src/findings/UncertaintyFindings.tsx), [Evidence](../src/views/Evidence.tsx), [evidence selection/export model](../src/evidence/model.ts) and [table download component](../src/components/TableDownload.tsx). The [findings/evidence contract](../contracts/FINDINGS_EVIDENCE_CONTRACT.md), [generation contract](../contracts/GENERATION_FINDINGS_CONTRACT.md) and [independent requirements review](W5_REQUIREMENTS_REVIEW.md) define and check the scientific scope.

## Verification

| Evidence | Passed checks | Scope |
|---|---:|---|
| [Generation acceptance](W5_GENERATION_VALIDATION.json) | 3,835 | Independent frozen-source comparisons over twelve cohorts, all 88 draws, 48 new-formula attempts, twelve exclusions, four prototypes, eleven model results, two selected energy pairs and six composition searches. |
| [Uncertainty acceptance](W5_UNCERTAINTY_VALIDATION.json) | 55,470 | Independent original records, 130 evaluation snapshots, thirty split/endpoint contexts, 300 retention selections, 300 decile rows, ten role rows and 361 CSV projections. These projections are distinct from actual browser downloads. |
| [Evidence acceptance](W5_EVIDENCE_VALIDATION.json) | 2,136 | Original QE/reference/claim records; all 630 QE filter combinations and 36 reference-filter combinations, field precision, ordering, nulls and sources. |
| [Actual analysis downloads](W5_DOWNLOAD_VALIDATION.json) | 420 | Eighteen browser-saved UTF-8 CSV files, thirteen table kinds and 480 data rows. Exact bytes after BOM removal agree with current selected projections, chained to the three independent source validators. This is end-to-end export verification, not another independent numerical reconstruction. |
| [Browser QA](W5_BROWSER_QA.json) | 54 | Real controls, source handoff/Escape/focus, primary/supplementary counts, all formula selectors, endpoint types and split choices, risk keyboard input, reload, accepted-stage/CIF handoff, QE/reference filters, unavailable publication links, 360/390px layouts and scoped 404/Retry recovery. |
| [Shared state](W5_STATE_VALIDATION.json) | 606 | Existing normalization, navigation and cancellation contracts. |
| [Runtime guards](W5_DATA_GUARDS.json) | 202 | Dataset and invalid/corrupt boundary cases. |
| [Frozen research](W5_RESEARCH_VALIDATION.json) | 108,571 | Original saved-source arithmetic and complete public export remain valid. |
| [Tooling/build copy](W5_TOOLING.json) | 124 | Pinned runtime/dependencies, final production files and all copied research assets. Strict TypeScript and the production build also passed. |

The browser checks are representative interaction acceptance, not an exhaustive browser Cartesian product. Independent source/model checks exhaust all split/endpoint and filter combinations. Actual CSV coverage includes primary MgO/TiO2, supplementary MgO, selected energies, failed attempts, all exclusions, prototypes, catalog matches, reliability, retention, deciles, roles, full/filtered QE, full/filtered references, claims and accounting. Downloaded bytes and exact selections are retained under [analysis-downloads](analysis-downloads/) and [the selection manifest](W5_DOWNLOAD_EXPECTATIONS.json).

The review corrected the ledger header to **Stationary at this setting**. Preliminary 50-Ry stationarity is not presented as final 90-Ry finite-check acceptance. Process exit zero and JOB DONE remain compatible with the perturbation's incomplete terminal SCF and unavailable final energy/forces/stress.

The production tree contains **84 files and 5,227,006 bytes** uncompressed. Initial JavaScript is **413,933 bytes**, initial CSS **44,190 bytes**, lazy viewer JavaScript **567,301 bytes** and lazy replay chart JavaScript **374,724 bytes**. Each JS chunk remains below 900 kB and the full tree below 10 MB. Transfer optimization and integrated performance acceptance remain W6. No dependency was added, and fault-fixture controls are absent from the production bundle.

The [baseline](W5_BASELINE.json) and [machine closure](W5_COMPLETION.json) bind all **103 original research inputs**, four numerical/budget/event baselines, **75 curated content files**, both manifest copies, historical W1-W4 evidence, the current implementation and build. All frozen research/public hashes remain unchanged. The active release remains `data-v1-2a138b7808f0d12c5151`, manifest SHA-256 `3b55f64687a8dd270482b3a2dfc9395672dbbce836fd90041712d2750e228e3d`.

## Browser and visual evidence

Three screenshots were captured and inspected: [desktop findings](W5_FINDINGS_DESKTOP.jpg), [desktop evidence](W5_EVIDENCE_DESKTOP.jpg) and [390px selected-risk panel](W5_FINDINGS_MOBILE.jpg). The desktop headings/navigation and accounting are legible; the mobile plot, selected-row highlight and actual retained fraction agree with the UI state. Wide scientific tables scroll inside labelled regions without widening the page. This is a scoped review of the visible panels, not complete visual acceptance of every screen.

Generation, uncertainty and DFT HTTP-404 fixtures were served only from the loopback QA server. The unaffected sections remained available, and Retry restored the original dataset without changing public or production bytes. Clean production Findings-to-Evidence navigation logged no browser warning or error. The [teardown record](W5_SERVER_TEARDOWN.json) confirms owned servers stopped, port 4175 has no listener, mode reset to `ok`, test tabs closed and viewport override cleared.

One long browser sweep reset the automation session; only previously observed passing checks were recovered, and unreported partial work was excluded. A whitespace-sensitive assertion and a retry assertion made after the page changed were corrected and rechecked against actual row counts in a fresh tab; their history is retained in browser QA. These were test-observation issues, not changes to research data or claimed product fixes.

## Limits and next work

No predictor fit, crystal generation, structure-matching run, CHGNet relaxation or QE job was performed for W5. Historical retrieval, model energies, genuine fresh QE results, catalog absence and material stability remain separate. The study establishes no newly discovered DFT-confirmed stable material or symmetry-free architecture benefit.

Verification used the native in-app browser on this Windows host. Cross-browser checks, physical touch gestures, full accessibility/contrast review, whole-page visual review, transfer optimization and the guided three-minute tour remain W6. Earlier W3/W4 native hidden-page-delivery limitations remain tracked independently. W5's successful screenshots do not retrospectively change those historical records.

**No core W5 functional exit item remains open.** O3 is implemented from saved deciles; O1 scatter remains explicitly deferred, O2 saved-stage enrichment remains implemented and O4 extra effects remain optional. Next is **W6: integrated QA and presentation**, followed by W7 deployment/live verification. W5 completion does not claim final local-release readiness or a deployed website.

## Reproduce

From `website/` in PowerShell:

```powershell
.\scripts\npm.ps1 run test:generation
.\scripts\npm.ps1 run test:uncertainty
.\scripts\npm.ps1 run test:evidence
.\scripts\npm.ps1 run w5:downloads
.\scripts\npm.ps1 run w5:state
.\scripts\npm.ps1 run w5:data-guards
.\scripts\npm.ps1 run w5:research
.\scripts\npm.ps1 run build
.\scripts\npm.ps1 run w5:tooling
.\scripts\npm.ps1 run preview -- --port 4173
```

Open `http://127.0.0.1:4173/#/findings` or `#/evidence`. The download verifier checks the retained actual artifacts; collecting new browser files is a separate interaction step. W5 commands retain phase-specific reports without overwriting dated W1-W4 evidence.
