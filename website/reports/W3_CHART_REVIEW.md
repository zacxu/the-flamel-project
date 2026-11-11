# W3 chart acceptance and independent code review

Status: passed for source review and strict TypeScript validation. Browser interaction and visual acceptance are recorded separately by the main W3 review; this report does not claim screenshot inspection.

Reviewed on 22 October 2026: `src/components/ReplayChart.tsx`, `src/replay/chart.css`, the integrated `src/views/Replay.tsx`, the pure `src/replay/model.ts`, and the W3 model/playback validation reports. Research release: `data-v1-2a138b7808f0d12c5151`.

## Scientific fidelity

| Requirement | Review result |
| --- | --- |
| Three acquisition outcomes | The metric selector supplies near-stable hits, cumulative precision and distinct chemical systems to the same chart component. Hits use the signed reference-hull-distance threshold of ≤0.05 eV/atom. |
| Five policies and all splits | Series are created for every selected policy from the saved curve rows. Aggregate mode uses the five recorded splits; individual mode uses the selected saved split. The independent W3 replay validation reconstructs all 25 histories, 125 batches and 1,250 query events. |
| Recorded boundaries only | Model, chart and table use 0/10/20/30/40/50. Both the caller and component filter outcomes beyond the completed budget. The x-axis retains the common 0–50 budget range. |
| Derived zero origin | Zero hits and zero systems are derived display origins, rather than additional measured curve rows. A zero-query tooltip explicitly says “Derived zero-query display origin; no labels acquired.” The chart help and surrounding scope note explain this state. |
| Zero-query precision | Its model value is null; it is never substituted with zero. The chart/table describe the value as unavailable. No precision point is drawn at zero. |
| Precision units | Model values and CSV are fractions; plotted labels, tooltips and displayed tables convert once to percentages. Sample SD is converted to percentage points in the table. |
| Descriptive spread | Aggregate values use sample SD with denominator n−1. The ranged `Area` receives the calculated low/high endpoints directly. The y-domain includes their full extent rather than clipping to physical metric bounds. Individual split series have no spread band. |
| Interpretation | Chart help identifies the bands as variability across overlapping historical splits, distinct from predictor calibration and independent-dataset confidence intervals. |
| Lines and tooltips | Linear segments connect supplied points; all chart animations are disabled. The tooltip validates its boundary and looks up only that supplied point. It performs no interpolation, fitting or target-label display. |
| Known negative result | The integrated header retains the finding that Quality retrieved more near-stable records than Full in all five splits. The chart does not reframe that result as a newly stable material discovery. |

The final `W3_REPLAY_VALIDATION.json` reports 45,871 passing checks, including original frozen CSV reconstruction, all 31 nonempty policy subsets, six displayed budgets and 125 pre-reveal batches. This review uses that report as supporting evidence; it does not count those checks as new chart tests.

## Presentation and interaction

| Requirement | Review result |
| --- | --- |
| Policy identity | Lines, dots, range bands and HTML legend consume the same W1 `colour` and `label` fields. Distinct dash patterns supplement the colours for all five policies. |
| Accessible context | A labelled figure, caption, chart description and linked help text explain the metric, units and scope. Recharts' accessibility layer remains enabled. The root view supplies a scrollable equivalent data table. |
| Keyboard operation | The primary budget range and metric radio controls use native keyboard semantics. Optional chart-point buttons accept Enter and Space, select exact boundaries and have visible focus styles. Labels describe a budget change, without implying a policy change. |
| Pointer selection | Only actual recorded circles invoke the optional budget callback. Clicking arbitrary line positions cannot generate intermediate budgets or fabricated values. |
| Narrow layouts | The chart container has `min-width: 0`, a 320 px mobile canvas, wrapping captions/legend and constrained tooltips. The table remains independently scrollable. Actual browser layout checks remain the main review's responsibility. |
| Motion | Lines, areas and tooltips have animation disabled. Existing application reduced-motion CSS also applies. |
| Failure isolation | The chart is lazy-loaded behind Suspense and a chart error boundary. The saved data table and CSV remain present if the plotting chunk fails. |
| Static deployment | The chart requires no server, scientific Python, external API, GPU or live model. |
| Chunk budget | The inspected production build contained a separate `ReplayChart-ORhelPGL.js` chunk of 374,489 bytes, below the planned 900 KB uncompressed chart ceiling. Subsequent source changes require the final build to record its current name/size. |

## Verification and limits

- `scripts/npm.ps1 run typecheck` passed after the derived-zero copy change.
- The chart review changed only its component, scoped CSS and this report. No dataset, source hash, research label, model coefficient or scientific budget was modified.
- Source inspection found no outstanding chart defect. This report does not replace browser interaction, mobile layout, download, timer-cancellation or screenshot evidence recorded by the main W3 acceptance process.
