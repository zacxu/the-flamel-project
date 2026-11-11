# W2 — Narrative, design and shared application shell

Completed 22 October 2026. **All eight W2 tasks and the functional W2 exit gate pass.** The six-view application, shared contracts and real-data previews are implemented and verified. Screenshot capture is unavailable in the current browser tooling; the exact verification limit is recorded below.

W2 replaces the W1 tooling smoke screen with six navigable research views, a shared visual language, validated hash routes, source and glossary drawers, responsive layouts and scoped data failures. The site remains a local static application. No hosting login, upload, new scientific experiment or deployment is part of W2.

## Task closure

| W2 task | Implemented result | Verification status |
|---|---|---|
| W2.1 application skeleton | Overview, Workflow, Replay, Crystal Lab, Findings and Evidence, using React/TypeScript/Vite and same-origin immutable exports | Passed build and actual browser navigation |
| W2.2 design system | Warm paper/graphite/copper/blue styling; serif headings, system UI text and numeric formatting; policy colours from the frozen theme; labelled status badges; diagram, comparison, crystal workspace and evidence table patterns | Passed source review and desktop/mobile computed-layout checks; pixel-review limitation below |
| W2.3 overview | Exact planned headline/supporting copy and both entry actions; accepted eight-atom known-MgO saved figure; explicit recorded research, negative acquisition result and no new stable material | Both actions and final production data/image load passed |
| W2.4 workflow | Seven clickable stages with actual inputs, outputs, examples, status and source actions; historical track separate from fresh generation; explicit 0/48 stop, predetermined known-MgO branch and four prototype baselines | All seven nodes and scientific branch distinctions passed |
| W2.5 route/state | Six hash routes and typed mode, seed, policy comparison, inspected policy, budget/batch/reveal, candidate/stage, generation scope and uncertainty selections; invalid values/combinations normalized; meaningful state survives reload | 606 state checks; native reload/history/invalid-link checks passed |
| W2.6 defaults/reset | Aggregate Quality versus Full at 50 completed queries, paused; complete reset; browser history restoration; cancellation contract for future playback; invalid drawers close on route/mode/seed/inspected-policy changes | State/timer suite and real-browser default/reset/Back/Forward passed |
| W2.7 interpretation | Searchable glossary and scoped source/method drawer; source IDs/hashes, units, historical thresholds, uncertainty-radius formula, attributions and genuinely unavailable publication links | 202 guards; actual modal/search/empty/Escape/focus checks passed |
| W2.8 responsive/failure states | Six-view navigation, skip link, route focus, native modal Escape/focus return, reduced motion, keyboard-scrollable labelled tables, verified lazy assets, loading/unavailable/error/retry and view error boundary | Browser DOM/layout/keyboard and production fault tests passed; no screenshot review claimed |

## What each view currently does

- **Overview:** explains the integrated pretrained-generator prototype. Its primary action restores aggregate Quality-versus-Full at 50 queries; its secondary action selects the actual accepted generated MgO stage. The acquisition comparison derives from exported statistics, with descriptive sample SD and explicit overlap limits.
- **Workflow:** exposes Propose → Generate → Screen → Select → Relax → Validate → Compare. The six new-formula proposals terminate at zero exact-cell eligible candidates. Known MgO validation and prototype relaxation remain separately named branches. Historical signed hull labels never become interchangeable with fresh QE energies.
- **Replay:** provides working aggregate/five-split, visible-policy, inspected-policy and recorded-budget controls. The cumulative table computes actual means/sample SD from frozen curves. At zero queries precision is unavailable; aggregate mode invents no individual history.
- **Crystal Lab:** selects actual catalog entities and their recorded stages only. It loads the chosen geometry on demand, shows the matching verified saved figure and retains physical atoms, method, stage, eligibility, DFT status, recorded symmetry tolerance and engine-qualified energy. Expandable lattice/fractional-coordinate tables provide accessible scientific detail. Missing DFT stages remain unavailable.
- **Findings:** displays all 14 frozen narrative claims in four source-linked groups. Local section navigation respects reduced motion and moves keyboard focus to the selected heading.
- **Evidence:** loads actual DFT coverage, separates three accepted geometries from two original source-reference IDs, exposes the incomplete 900-second perturbation and presents the complete frozen claim/scope/limitation matrix.

## Data and route safeguards

The application bootstraps eight compact datasets through the W1 immutable-release loader. Geometry, structure figures and DFT details load when needed. Runtime guards validate all 42 exported datasets without coercion or mutation. Corrupted schema/version/identity, invalid values or inconsistent structures produce a scoped error instead of invented research values.

The W1 `Attribution.licenceUrl` TypeScript contract now permits the actual exported `null` value. The UI renders plain licence text for that case. The frozen public bundle, content hashes and manifest were not regenerated for this correction.

The shared state controller validates candidates against their actual recorded stage lists, preserves useful selections in hash links and restores them through back/forward navigation. Temporary drawers and playback status remain local. Route/mode/seed/inspected-policy transitions and history restoration call registered cancellations; the W3 controller can use that existing contract when playback is implemented.

## Validation record

| Check | Current recorded result | Final integration status |
|---|---|---|
| State/route/registry/history/cancellation checks | **606/606 passed**, including 14 actual entities and 26 saved stages | Passed |
| Runtime data guards | **202/202 passed**, covering 42 actual datasets and deliberately invalid inputs | Passed |
| Strict TypeScript | `npm run build` includes `tsc --noEmit`; exit 0 | Passed |
| Vite production build | JS **298,636 bytes**, CSS **21,581 bytes**, HTML **866 bytes**; entire tree **4,142,993 bytes / 80 files** | Passed |
| Actual browser interactions | **42/42 checks passed**, including all six views, both actions, all workflow nodes, shared selections and real scientific identities | Passed |
| Back/Forward, reload, malformed routes and reset | Native browser events, repaired-link explanation and full canonical reset verified | Passed |
| Keyboard and responsive layout | Modal focus/Escape/opener return; Back closes modal then focuses restored view; 360/390px and default desktop layout measurements; wide tables scroll within regions | Passed; CSS/JS reduced-motion support also reviewed |
| Loading and failure recovery | Actual built app with delayed/missing/corrupt manifest, missing stage and missing image; scoped errors, preserved text/navigation and retry verified | Passed |
| Tooling and production copy | **124/124 checks passed**; all immutable data/assets match production hashes | Passed |
| Independent research validation | **108,571/108,571 passed**, all 103 source inputs and four frozen baselines unchanged | Passed |
| Screenshot/render capture | Repeated `Page.captureScreenshot` timeouts in the available in-app browser | Unavailable; no pixel/screenshot review claimed |

Machine evidence: [state validation](W2_STATE_VALIDATION.json), [runtime guards](W2_DATA_GUARDS.json), [actual browser QA](W2_BROWSER_QA.json), [tooling/build copy](W2_TOOLING.json), [research revalidation](W2_RESEARCH_VALIDATION.json) and [final closure](W2_COMPLETION.json). The public data release remains `data-v1-2a138b7808f0d12c5151`, manifest SHA-256 `3b55f64687a8dd270482b3a2dfc9395672dbbce836fd90041712d2750e228e3d`.

Browser QA used the ChatGPT in-app browser at its default 1101×828 viewport and temporary 390×844 / 360×800 overrides, restored afterward. This is desktop-browser responsive testing, not physical-phone or cross-browser certification. Measured page bounds, loaded actual image dimensions, accessibility state, table scrolling and interactions are verified; screenshot composition and pixel-level review are not. W6 retains broader visual/device QA. Reduced-motion handling was reviewed in CSS and the section-scroll implementation; no emulated reduced-motion preference is claimed.

Checks found and resolved an uncertainty-search vocabulary gap, a focus race during modal/history changes and duplicate native `popstate`/`hashchange` events clearing repaired-link explanations. The state suite contains regressions for the latter. Asynchronous data/viewport checks were assessed after the relevant loading/layout update completed. The final normal production navigation recorded no browser console errors; deliberately injected HTTP/integrity failures are expected test conditions.

The loopback-only `scripts/qa-server.mjs` serves existing `dist/` bytes with local fault modes. It is excluded from the public payload; all owned development/fault servers were stopped after verification. The PowerShell npm wrapper now preserves package-script arguments after `--`. W2 validation writes its own reports and retains historical W1 closure records. No dependency installation or data regeneration was needed.

## Explicit later-phase scope

W2 completes the narrative and shared shell. It does not mark W3, W4 or W5 complete:

- **W3:** curve charts, play/pause/next-batch state machine, ten-record query drawer, consistent teaching reveal and displayed-data downloads.
- **W4:** interactive Three.js rendering, camera/atom controls, WebGL/context-loss handling and checked structure downloads. W2’s actual scientific fallback and metadata are useful previews; they are not completion of the interactive viewer.
- **W5:** complete generation and uncertainty explorers, filterable all-19-QE-job table and remaining evidence/download interactions.
- **W6/W7:** integrated presentation QA, guided tour, final release optimization, InfinityFree upload and live verification.

No dependencies were added for W2. The research dataset, model weights, frozen numerical outputs, experiment budgets and public data release remain under their existing freeze. All new work belongs to website application source, contracts, local tests and documentation.
