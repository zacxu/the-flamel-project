# Shared application and component patterns

These conventions were established in W2. Reuse them in W3–W5 so the scientific meaning, routes, accessibility and failure handling stay consistent.

W4 adds the shared `CrystalDisplay`/lazy `CrystalViewer`, with a stage-keyed error boundary and source-specific scientific fallback. Metadata, original coordinates and saved export remain outside the renderer. Only the active route mounts the hero or Lab viewer; static comparison figures do not create a second renderer. See the [geometry/export contract](CRYSTAL_CONTRACT.md) for row-vector, PBC, CIF and strict energy-comparison rules.

## Route state and temporary state

`src/state/route.ts` owns persistent selections and pure normalization. `useRoute.ts` connects that controller to the browser. Use its `update`, `navigate` and `reset` methods; do not write an independent fragment parser or mutate `window.location.hash` inside a view.

Persistent selections include the active view; aggregate/seed mode; seed; visible policies; inspected policy; completed budget; inspected batch/reveal; actual candidate/stage IDs; generation scope; uncertainty endpoint and retained fraction. A visible policy set cannot be empty, the inspected policy must be visible, and a selected stage must belong to its actual recorded candidate.

Keep drawers, local workflow-node choice and transient animation state local. Playback status is not serialized into a shared link. Register replay timer/transition cleanup through `registerCancellation`; route, mode, seed and inspected-policy changes, history restoration, reset and teardown must leave playback paused. Register cleanup on unmount as well. W3 implements these rules in the [replay controller and hook](REPLAY_CONTRACT.md).

Use native links with canonical hash URLs for the six views, preserving modified-click/open-in-new-tab behaviour. Use buttons for local actions that do not create a route. Local Findings section navigation focuses its destination heading and respects reduced motion.

## Loading recorded data

`ResearchProvider` loads the core typed datasets through the immutable W1 `ResearchRelease`. `useResearchDataset(logicalName)` loads additional JSON only when needed; `useResearchAsset(logicalName)` verifies assets before creating their Blob URLs. Never fetch a mutable raw-data URL directly from a view, coerce invalid input into a valid record or silently replace a failed measurement with zero.

`DataNotice` supports loading, unavailable and error/retry presentation. A failed geometry or figure should leave its surrounding text, navigation and scope usable. `ViewBoundary` contains unexpected render failures at the view level. Scoped errors must not fabricate a record or promote another candidate to a successful experiment.

On dataset/asset replacement, stale asynchronous results are ignored. Owned Blob URLs are revoked on cleanup. Additional hooks must maintain those cancellation/resource rules, including React StrictMode remounts.

## Shared drawers and focus

`SourceDrawer` and `GlossaryDrawer` use a native modal `dialog` with a labelled title. Modal opening captures the previous focus; closing or unmounting restores it when the element still exists. The browser supplies modal focus containment; native Escape routes through the same close handler as the close button. Keep a visible close control. Do not layer a second custom focus trap or an extra global Escape listener over the native modal.

Changing route/mode/seed/inspected policy closes incompatible drawers. Route changes focus the main content and scroll to the page start. The skip link focuses that same main landmark. Future query drawers must use the shared modal behaviour or preserve its equivalent semantics.

## Sources are identity evidence

Open `SourceDrawer` with the relevant exported source IDs. Its search/filter operates on that scoped set. Unknown requested IDs produce an explicit unavailable message; they must not resolve by matching a formula, filename guess or unrelated candidate.

A SHA-256 hash establishes the identity of a saved file. It does not establish terminal SCF acceptance, stationarity, finite sensitivity validation, novelty or stability. Retain that distinction beside source evidence.

Publication links remain unavailable until checked public destinations exist. The nullable `Attribution.licenceUrl` represents a real unavailable link: show the licence text, not a fake anchor.

## Status, number and policy presentation

Use `StatusBadge` with a text label. Colour supplements meaning; a green or blue mark alone is not a scientific acceptance label. Keep method, saved stage, experimental eligibility and DFT validation separate.

`formatNumber` renders finite numbers and makes missing values unavailable. Choose the displayed precision for the question while preserving full precision in the dataset. Include units with energy, lattice, force, stress and time values. Name the energy engine and do not compare absolute energies across chemical compositions or engines.

Policy colours and labels come from the exported `ThemeDataset`. Keep those assignments consistent in toggles, tables and future charts. Every policy also has visible text. Do not invent another label/colour map in chart components.

Historical near-stable retrieval uses the signed saved target ≤0.05 eV/atom; historical reference-hull hits use ≤0. At zero completed queries precision is unavailable. Split aggregates describe overlapping splits, using sample SD across split outcomes, never across query events.

## Tables, charts and saved structures

Wrap wide data tables in a labelled `role="region"`, `tabIndex={0}` scroll container. Keep native table semantics, a caption, column headers and row headers. Tables remain available alongside future charts so keyboard/screen-reader users can inspect the same numbers. Label any derived zero-query origin separately from measured curve points.

`SavedFigure` handles a verified figure and meaningful alt text/caption, with a scoped asset failure. Pick structure figures from the actual candidate/stage registry. The fallback image may wrap coordinates for display; the coordinate table retains original fractional values and the stated physical atom count.

Only expose stages that exist for the selected candidate. A missing DFT state remains unavailable. A prototype is not an intermediate state of a generated candidate, and a two-atom source reference is not an eight-atom model cell’s later frame. Preserve excluded status even while a valid diagnostic geometry is visible.

## Responsive and reduced-motion behaviour

Use the shared page/control/table/workspace classes in `src/styles.css`. Controls stack on narrow screens, long IDs/hashes wrap, and table overflow remains deliberate rather than widening the entire page. Keep keyboard focus visible and buttons labelled.

Respect `prefers-reduced-motion` in CSS and JavaScript scrolling/animation. Auto-rotation will remain opt-in when the W4 viewer exists. Camera animation, autoplay and chart transitions must never change the scientific record or prevent a visitor from pausing/leaving a view.
