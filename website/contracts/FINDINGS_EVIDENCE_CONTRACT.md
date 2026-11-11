# Findings and evidence display contract

W5 completes the recorded generation, uncertainty and DFT analysis interfaces. The implementation reads the pinned `generation.json`, `uncertainty.json` and `dft.json` datasets and the existing core summary, methods, claims, provenance and stage registry. It does not generate crystals, fit or calibrate a model, infer new properties, relax structures or dispatch Quantum ESPRESSO.

The authoritative original records remain frozen. Public data retains release `data-v1-2a138b7808f0d12c5151` and manifest SHA-256 `3b55f64687a8dd270482b3a2dfc9395672dbbce836fd90041712d2750e228e3d`. A public source ID resolves to the existing provenance registry; hashes establish file identity, not acceptance or discovery.

## Selection and shared state

| Interface | Selection and population |
|---|---|
| Generation | Shared `scope` is primary or supplementary. Primary control composition, selected energy pair and proposal formula are local display selectors. Supplementary always selects the separately recorded MgO top-up cohort. |
| Reliability | Shared `seed` chooses one of five recorded splits. Shared `endpoint` chooses Initial/Quality/Full or advanced Quality+diversity/Random/Uncertainty. Initial means `initial_shared` at zero queries once per split; all other exposed endpoints are at 50 queries. |
| Selective risk | Shared `retainedFraction` is one recorded tenth from 0.1 to 1.0. It selects a saved row from the selected split/endpoint and never interpolates a new experiment. |
| Deciles | Ten saved bins for that same selected split/endpoint, sorted by disagreement and material ID. The 3,418-row evaluation population gives approximately equal bins of 342 or 341 rows. |
| Role diagnostics | Always the separately labelled Full-policy population: all ten split/role rows pooled across five histories. The selected split is highlighted, not used to silently filter the pooled totals. |
| DFT ledger | Local role, research-phase (1/3/4/5), calculation (`scf`/`vc-relax`) and evidence-level selectors filter the nineteen original jobs, with a result count against nineteen. |
| Reference inventory | Local system, accepted/missing, elemental-endpoint and spin-review selectors filter original system memberships, preserving overlaps and showing a count against 218. |

Existing hash routes serialize the shared fields above, as specified in [ROUTE_STATE.md](ROUTE_STATE.md). Local table filters and generation subselectors are temporary presentation state and are not serialized. Source/glossary drawers use the shared modal conventions. Saved-structure buttons resolve an actual candidate and recorded stage in the existing registry, then open the W4 Crystal Lab export flow. No formula-only lineage or nonexistent stage is invented.

## Generation and model comparisons

[GENERATION_FINDINGS_CONTRACT.md](GENERATION_FINDINGS_CONTRACT.md) defines the detailed generation projection. Both primary arms retain first-eight denominators and raw valid/unique counts. The supplementary MgO tab displays its four additional draws per arm separately. Exact-cell validity and unique yield are distinct results under the same trained architecture and different sampling conditioning.

The MgO model pair uses the supplemented selection pool; TiO2 uses its primary pool. Each pair is one selected structure per arm. The anatase/rutile comparison is within TiO2 and CHGNet only. Model energy is eV per physical atom; no cross-composition formation energy, hull, DFT ranking or causal architecture claim is computed.

All six proposals expose eight attempts apiece. The 0/48 exact-cell outcome, twelve excluded larger-cell diagnostics, four separate substitution prototypes and all eleven model-result records remain accessible. Historical composition absence and partial geometry matching (15/23 MgO, 34/44 TiO2) retain their snapshot/subset limits. Rejection is not physical instability; an unmatched subset result is not global novelty or generator-pretraining OOD.

## Uncertainty, risk and roles

`src/findings/uncertainty.ts` selects the saved single-split endpoint context. Nominal 90% is compared with observed empirical coverage and interpreted alongside MAE, RMSE, full interval width, disagreement/error association and calibration scale. Radius is `q × max(disagreement, 0.01 eV/atom)` and full width is twice the radius. These intervals apply to the historical signed hull-distance target, not fresh generated structures, CHGNet or QE energies.

Selective risk sorts untouched evaluation rows by saved disagreement ascending with material-ID tie breaking, then retains `ceil(n × requested fraction)` at the ten recorded fractions. Display requested fraction, actual fraction and row count separately, together with retained-subset MAE and complete-row MAE. A lower retained-subset error does not improve the complete population, validate a new acquisition policy or remove discarded-row error.

The five split populations overlap. No independent-dataset significance or arbitrary-chemistry coverage guarantee is offered. Deciles are descriptive error/disagreement bins, not probability bins or new calibration. Full-policy conservative and optimistic roles retain pooled 140/175 versus 7/75 historical hits. Mean radii are query-event-weighted; roles were not randomized and their allocations, criteria and evolving candidate pool confound causal comparisons.

## DFT acceptance and reference accounting

`src/evidence/model.ts` preserves job order, identity and original measurements. Process exit code, JOB DONE, accepted terminal SCF, stationarity at that job's setting and accepted final-geometry finite sensitivity checks are independent displayed/exported fields. Setting-level stationarity in a preliminary 50-Ry calculation is not final 90-Ry validation. A stationary fixed-geometry SCF sensitivity probe is not another accepted relaxed geometry.

Pilot force/stress are unavailable. The 900-second perturbation has JOB DONE but no accepted terminal SCF energy, force or stress. Its missing values remain null/empty, not zero. That incomplete probe neither establishes instability nor removes the prior accepted unperturbed result.

Three distinct relaxed geometries have final finite checks: generated known MgO, source MgO and source CaO. The two references are two original source material IDs. Across overlapping inventories they occupy three accepted memberships, not three unique source references. Coverage remains primary 2/161 and fallback 1/57, with 218 total and 215 missing system memberships. Metal, O2 and spin branches remain incomplete.

The MgO control-minus-reference difference is roughly -0.005533 meV/atom and numerically unresolved. Cutoff/k changes are measured finite sensitivity, not a rigorous total DFT error bound. CaO+2MgO provides only a reference anchor: compatible CaMg2O3 candidate energy, reaction energy, complete competing-phase hull and newly established stable material remain unavailable.

## Sources, CSVs and publication states

Every displayed analysis table has a corresponding browser-generated CSV. The table projection and CSV use the same current selection. Helpers preserve complete numeric precision, recorded booleans/zeros, RFC 4180 quoting and empty unavailable/not-applicable fields. Coverage/retained fractions use 0-1 in CSV; UI percentages are display formatting. Energy, force, stress, distance, cutoff, wall-time and unitless fields are identified by headers or explicit unit columns. Study/data-release/source identity and scientific population scope accompany the scientific exports; the frozen accounting export retains its release/source IDs, explicit unit and interpretation columns.

DFT CSV contains all 29 headers even when no job matches; reference CSV retains all 21 headers with overlapping membership identities intact. Claims retain their original status, measured scope and limitation. Query results or measurement nulls are never invented to fill a filter. `useCsvDownload` revokes superseded Blob URLs and suppresses stale download links when their text projection changes.

Source actions resolve public provenance IDs. The ten-row claim matrix links to the original `claim_matrix`; fourteen narrative findings have their own recorded source sets. Public methods, frozen date, glossary, attribution and computational accounting remain distinct from unpublished full archives. Repository, write-up and video controls stay unavailable until their separate public destinations exist. Administration URLs and local research paths are not publication links.

## Acceptance and remaining phases

Run from `website/` with the documented Node 24/workspace npm wrapper:

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
```

The generation, uncertainty and evidence verifiers independently compare the shipped helpers with hash-bound original records. Actual browser downloads are separately checked by `w5:downloads` against those validated projections. W5 reports have distinct filenames so historical W1-W4 reports remain unchanged. [W5_REQUIREMENTS_REVIEW.md](../reports/W5_REQUIREMENTS_REVIEW.md) reviews all eleven source/data requirements. Final browser coverage, build measurements and closure are recorded in [W5_COMPLETION.md](../reports/W5_COMPLETION.md) and its linked machine evidence.

Optional O3 saved-decile enrichment is implemented. Integrated guided tour, broader accessibility/visual/device QA and local release closure remain W6; InfinityFree deployment and live verification remain W7. No hosting upload or new scientific experiment is part of W5.
