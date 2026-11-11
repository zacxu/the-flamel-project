# W6 guided presentation contract

The tour is an optional presentation of the frozen study. It starts only when the visitor presses **Start guided tour**. It changes saved selections and camera presentation; it never executes generation, inference, model fitting, acquisition or DFT. The exact script is implemented in [model.ts](../src/tour/model.ts).

## Timing and deterministic presets

The six step durations are **25, 45, 35, 30, 25 and 20 seconds**, totalling **180 seconds**. A single monotonic-clock controller owns at most one 250 ms presentation timer. Paused time is excluded from the script. Advancing manually starts the requested step at its zero-second preset; it does not silently run the skipped scenes.

| Global time | Presentation selection | Recorded scope |
|---|---|---|
| 0:00 | Overview | Research question and separate scientific tracks |
| 0:08, 0:14, 0:20 | Workflow Propose, Generate, Screen | Six proposals, same trained generator architecture, empty exact-cell new-formula shortlist |
| 0:25 | Replay split 20261022, Quality and Full visible, Quality inspected, zero queries | Derived origin; precision unavailable |
| 0:30, 0:36, 0:42, 0:48, 0:54 | 10, 20, 30, 40 and 50 completed queries; corresponding revealed batch | The five actual ten-query decisions and saved outcomes; no individual-query refits |
| 1:00 | Same split/budget, Full inspected; chemical-systems chart | Broader coverage versus retrieval yield |
| 1:04 | Aggregate, both policies, 50 queries | Five overlapping splits; saved means and sample SD |
| 1:10 | Known MgO, accepted DFT stage, eight physical atoms | Finite-checked known-phase recovery; camera rotation only while running and motion allowed |
| 1:22 | CaMg2O3 prototype, CHGNet model-relaxed stage, six atoms | Prepared baseline; model convergence does not establish DFT stability |
| 1:34 | CaMg2O3 transformer draw, generated-excluded stage, twelve atoms | Matching reduced ratio does not pass frozen six-atom gate |
| 1:45 | Primary first-eight MgO yields | Valid 7/8 versus 0/8; unique 1/8 versus 0/8 |
| 1:55 | Primary first-eight TiO2 yields | Valid 6/8 versus 1/8; unique 1/8 in both arms |
| 2:05 | Selected MgO CHGNet pair; primary yield scope preserved | One selected structure per arm from supplementary primary-plus-top-up pool |
| 2:15 | Full, split 20261023, all rows | Empirical interval coverage below nominal 90% |
| 2:23 | Full, split 20261024, all rows | Empirical coverage above nominal 90%; split-dependent calibration |
| 2:31 | Same endpoint/split, 10% requested retention | 342/3,418 actual rows; saved subset-error diagnostic |
| 2:36 | Restore 100% retention | Complete-population error comparison; no new policy outcome |
| 2:40 | Evidence: all nineteen QE jobs | Independent completion, SCF, stationarity and finite-check fields |
| 2:48 | QE role filter: perturbation | One incomplete 900-second run; terminal measurements unavailable |
| 2:54 | Reset QE filters; methods and reproducibility section | Incomplete reference inventory, public source buttons, known recovery and no new stable-material claim |
| 3:00 | Complete | No further presentation timer; Exit or Restart remains available |

The crystal example and stage identifiers are joined to the actual exported structure registry. A nonexistent synthetic geometry is never created as a preset. Workflow, chart metric, conditioning-control and QE filter presets consume the tour context after their asynchronous dataset/component mounts. Route selections use the existing normalization and content-pinned datasets. Tour transitions replace the current browser-history entry, keeping the URL reloadable without flooding browser history with automatic scenes.

## Presenter controls and interruption

- **Pause tour** freezes the current scene; **Resume tour** continues its remaining duration.
- **Next tour step** and **Previous tour step** set that step's exact initial preset. A paused rehearsal remains paused; a running presentation remains running.
- **Finish tour** ends the last step. **Restart tour** returns to the overview and clears the former timer.
- **Exit tour** cancels timers and returns focus to the Start button. It retains the currently displayed saved selection so the presenter can explore it normally.
- Using a page control, normal navigation, reset, Sources, Glossary, Copy link, or browser Back/Forward exits the tour. Ordinary page-control focus is not redirected to the tour launcher.
- Hiding the tab pauses the tour. Returning to it requires explicit Resume. Presentation changes always stop conflicting replay autoplay; ordinary replay autoplay remains available outside the tour.
- Reduced-motion preferences suppress automatic crystal rotation and presentation animation. Scrolling to each scene uses an immediate position change; there are no interpolated structures or scientific trajectories. Camera rotation also stops on pause, completion, exit or scene departure.

The tour toolbar stays in the page's ordinary focus order and is not a modal. It provides textual status/captions, native buttons and a labelled progress indicator. The caption announces scene changes; its time readout does not repeatedly announce every timer tick. On narrow screens the toolbar remains in normal document flow, avoiding a persistent overlay over the scientific controls. Source drawers are opened explicitly using the normal source buttons; opening one ends the presentation and retains the existing drawer focus/escape behaviour.

## Acceptance evidence

[verify-tour.mjs](../scripts/verify-tour.mjs) executes the actual controller with a deterministic monotonic scheduler and joins every crystal/DFT preset to frozen exports. Its [W6 result](../reports/W6_TOUR_VALIDATION.json) records 123 passing checks covering exact boundaries, all 25 scenes, no implicit start, pause/resume, manual navigation, completion, restart, disposal and stale-timer suppression. This controller test does not substitute for the production-browser rehearsal and visual/accessibility verification recorded in the W6 QA report.
