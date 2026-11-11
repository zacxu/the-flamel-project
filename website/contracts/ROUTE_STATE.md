# Shared route and state contract

W2 establishes the state used by all six views. The pure controller in `src/state/route.ts` is the same implementation used by `useRoute()` and the independent Node verification script. It does not generate materials or run scientific calculations.

`useRoute()` returns `{state, update(patch, replace?), navigate(view, patch?), reset(), routeNotice, playing, setPlaying, registerCancellation(callback), bindStructureIndex(index)}`. `routeNotice` is `string | null`. Playback begins paused. W3's replay controller registers timer cleanup through `registerCancellation`; temporary drawer state stays in the consuming React component. See [the replay contract](REPLAY_CONTRACT.md) for preview/reveal phases and automatic versus manual history updates.

| Field | Valid values and meaning |
|---|---|
| `view` | `overview`, `workflow`, `replay`, `crystals`, `findings`, `evidence` |
| `mode` | `aggregate` or one recorded `seed` |
| `seed` | 20261022 through 20261026; retained while aggregate mode is active |
| `policies` | Nonempty, unique visible policy set; canonical order Quality, Full, Quality + Diversity, Random, Uncertainty |
| `policy` | Inspected policy; must belong to the visible set |
| `budget` | Completed historical query count: 0, 10, 20, 30, 40, 50 |
| `batch` | Inspected saved batch 1–5; seed mode permits completed batches or the next pre-reveal batch |
| `revealed` | Derived from mode, budget and inspected batch; true only in seed mode when that batch is complete |
| `candidateId`, `stageId` | Safe source identifiers; after registry binding the stage must be recorded for this candidate |
| `scope` | `primary` or `supplementary`; the scope never changes a saved record's scientific identity |
| `endpoint` | A saved uncertainty endpoint: any policy or `initial_shared`; independent of replay budget |
| `retainedFraction` | Exactly a saved tenth from 0.1 through 1.0; unsupported intermediate values are reset |
| `playing` | Temporary local status, omitted from the URL; allowed only in seed mode below the final budget |

Default selections are aggregate Quality versus Full, Full inspected, 50 completed queries, seed 20261022 retained, primary scope, Full uncertainty endpoint and retained fraction 1. The known eight-atom MgO candidate `phase1_mgo_attempt_000` starts at its real `phase1_mgo_attempt_000--accepted_dft` stage. Aggregate mode has no event history: reveal is false and inspected batch follows the budget, using batch 1 at zero. Reset restores every persistent default and pauses playback.

The default overview uses the bare website address with no hash or query. Other default views use `#/workflow`, `#/replay`, `#/crystals`, `#/findings` or `#/evidence`. URLs add `?key=value` only for selections that differ from `DEFAULT_ROUTE`; the parser restores omitted defaults. Derived reveal state and aggregate batch are omitted and recomputed from mode, budget and inspected seed-mode batch. Every meaningful selection still round trips, including selections retained across views. URLs may therefore grow when controls change; a default page never needs the original full settings suffix. URL encoding is handled by `URLSearchParams`. Existing full-settings links remain accepted and normalize to the shorter equivalent.

Both path and enum values are validated. Unknown parameters, ambiguous duplicate parameters, invalid identifiers, unsupported budgets and nonstored retained fractions are removed or reset with a plain explanation. A normalized URL replaces the current history entry so malformed links do not create repeated Back stops. Empty initial hashes are already canonical and produce no history write or warning. No credential, raw file path, drawer state, loaded data or animation state belongs in the hash.

Ordinary selection changes push one history entry; `update(patch, true)` intentionally replaces the current entry. `navigate(view, patch)` uses the same normalization rules. Browser Back/Forward and direct hash navigation restore the entire recorded state, then pause and cancel registered timers. View, mode, seed or inspected-policy changes also cancel and pause; reaching the final query boundary pauses. A reset and unmount always attempt every registered cleanup, including when one cleanup throws. The root component closes temporary drawers on `[state.view, state.mode, state.seed, state.policy]` changes.

Native hash navigation may dispatch both `popstate` and `hashchange`. A duplicate notification for the already-canonical current state retains any explanation from the original malformed link. Asynchronous catalog binding also preserves earlier scalar-repair explanations while adding candidate/stage corrections. A meaningfully different valid browser navigation or ordinary valid local update clears the previous notice; duplicate notifications still pause playback and cancel registered timers.

At 0 queries, seed mode may inspect batch 1 predictions with labels hidden. At 20 queries it may inspect revealed batch 1 or 2, or unrevealed batch 3. It cannot jump to unrevealed batch 5. Revealing a batch requires advancing the completed budget to its recorded boundary; a `revealed=true` hash alone cannot disclose future labels. The rendering consumer must enforce this derived field before displaying event targets. Aggregate mode does not have query drawers.

Once `structures/index.json` loads, call `bindStructureIndex(index)`; normalization then applies to the current state, all subsequent updates and browser history restoration. The standalone `normalizeCandidateSelection(state, index)` helper returns `{state, notices}` for other consumers. Unknown candidates select the real MgO example, or the first saved candidate if that example is unavailable. A stage from a different candidate selects the requested candidate's saved default stage and explains the change. In particular the two-atom catalog reference cannot become a fictitious later stage of the eight-atom generated MgO cell. An empty registry produces an unavailable notice; the consumer keeps its structure controls disabled.

Run `node scripts/verify-state.mjs --phase=W3` with the documented Node 24 runtime, or `npm run w3:state` through the workspace wrapper. It imports the shipped TypeScript directly, reads the real frozen public registry and checks malformed links, every saved candidate/stage pair, all seed/policy/budget identities, actual history-stack transitions, reloads, reset, stable external-store snapshots and real timer cancellation. Its current report is `reports/W3_STATE_VALIDATION.json`; the W2 report remains historical evidence. Full replay/data/CSV and playback verification are recorded separately in `W3_REPLAY_VALIDATION.json` and `W3_PLAYBACK_VALIDATION.json`.
