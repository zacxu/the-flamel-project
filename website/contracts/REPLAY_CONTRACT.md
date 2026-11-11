# Recorded acquisition replay contract

Phase W3 operates only on the immutable W1 data release. It neither runs a model nor changes the numerical study, the selection policies, calibration or budget ledger.

`src/replay/model.ts` supplies pure transformations shared by charts, tables and CSV downloads. `scripts/verify-replay.mjs` compares all 1,250 selected events, 125 batch points and 25 endpoints with the original hash-bound frozen CSV sources. It also checks the selected metadata join without publishing the full metadata table.

## Comparison values

- `buildReplaySeries(curves, theme, {mode, seed, policies}, metric)` returns exactly six saved boundaries: 0, 10, 20, 30, 40 and 50 queries. The interface filters these to the completed budget before rendering; hidden future batches must not leak outcomes through chart paths, tooltips, accessible descriptions or data tables.
- `hits` counts selected historical targets <=0.05 eV/atom. `precision` is hits divided by completed queries, expressed as a **fraction** in the model and CSV; the interface may format it as a percentage. `systems` counts distinct selected chemical systems cumulatively. This is neither model error nor the coverage of a predictive interval.
- Aggregate values use all five split outcomes with equal weight. Sample SD uses the n-1 denominator (4). The band stores the raw mean minus/plus this SD without clipping. This is descriptive variability across these overlapping split populations, not a confidence interval or a calibrated predictor radius.
- Single-split values have no sample SD or band (`null`). At zero queries, hits and systems are zero; aggregate SD for these deterministic origins is zero. Precision and its SD/bounds are `null` at zero queries.
- Missing or duplicate source curve points fail explicitly. No interpolation, imputed future points, per-query refits or synthetic history are permitted.

## Batch and reveal values

`batchFor(history, policy, round)` returns one saved ten-query batch or `null` if that identity is unavailable. The source has 5 seeds x 5 policies x 5 batches x 10 records; batch boundaries are the only acquisition steps represented.

`displayQueries(batch, revealed)` explicitly copies only the selected-query display fields. Before reveal, `revealedLabelEVPerAtom`, `nearStableHit` and `referenceHullHit` are all `null`; cumulative outcomes and raw batch objects are absent. After reveal, all three retain the exact saved number or boolean, including `false`. Random-policy acquisition scores stay `null` independently of reveal. Prediction mean, calibrated radius and diversity retain source precision and cannot be relabelled as observed outcomes.

This is pedagogical display hiding. The recorded outcomes are present in public static data; it does not provide access control. Aggregate mode has no individual candidate history. In selected-split mode, the first batch's predictions can be inspected at zero completed queries while its labels remain hidden. Previously completed batches remain revealed.

## CSV downloads

`comparisonCsv(curves, theme, state, dataReleaseId?)` exports the comparison table's visible policies at boundaries 0 through the completed budget. Each row includes mode, split identity (blank in aggregate), internal policy and display name, completed queries, `point_origin` (`derived_zero_state` at zero; `recorded_batch_boundary` otherwise), all three metrics with sample SD columns, aggregate split count, inclusive target thresholds, study/release/source identity and scope/null explanations. Precision columns are explicitly labelled `fraction`; threshold columns are labelled `eV_per_atom`. An aggregate CSV contains no individual selected-material identities.

`queryCsv(history, policy, round, revealed, dataReleaseId?)` exports only the inspected batch's ten selected records. Columns identify seed/policy/batch/query, material/formula/system/atoms, selection role/score, predicted mean and calibrated radius in eV/atom, diversity, gated historical target/hit flags, label visibility and study/release/source identity. Hidden target/hit cells are empty. A missing random score is also empty, and the null-explanation column distinguishes these cases. The scope column states that these are selections, not the full candidate pool, and that reveal is a teaching display state.

Both downloads use CRLF records, RFC 4180 quotes/doubled quotes and full JavaScript numeric precision. Null/undefined values become empty cells; boolean `false` remains `false`. Non-finite numbers fail. String cells beginning with a spreadsheet formula marker (=, +, -, @), including after whitespace/control characters, receive a leading apostrophe. Numeric negative energies remain signed numbers. Download filenames and route identity are chosen by the interface; metadata never invents a publication URL or local file path.

## Acceptance coverage

The automated check independently reconstructs cumulative near-stable/reference-hull hits and system coverage for every batch, verifies all selected source identities/predictions/labels/metadata, computes aggregate sample SD from original split outcomes, checks all 31 nonempty policy visibility sets at every completed budget in both modes, exercises CSV quoting/formula protection and proves that changing raw outcomes cannot change the pre-reveal projection. Browser acceptance additionally checks the actual rendered controls, chart, drawer, downloads and timer cancellation.
