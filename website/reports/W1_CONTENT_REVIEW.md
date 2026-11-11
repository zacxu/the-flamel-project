# W1 independent content and plan-coverage review

Reviewed 22 October 2026 against W1.1–W1.8 in
`PHASED_IMPLEMENTATION_PLAN.md` and the website plan's scientific, geometry,
provenance and publication rules. This review checks the data/content foundation;
it does not claim that the W2–W7 user interface or deployment exists.

| W1 task | Evidence reviewed | Coverage finding |
|---|---|---|
| W1.1 Tooling | Exact pins/lockfile, `reports/W1_TOOLING.md`, `reports/runtime.json` | Supported Node/npm with Vite engine verification; initial 46 checks expanded to 124 in final build-copy verification; local analysis environment reused |
| W1.2 Baseline and allowlist | `scripts/export_common.py`, `scripts/export_research.py`, `reports/W1_EXPORT.json` | Before/after numerical-freeze, manifest, budget and event hashes; explicitly hash-bound discovered inputs; parent sources unchanged |
| W1.3 Selected metadata join | `scripts/export_tables.py`, replay public records and validation counts | 1,250 events, 720 selected IDs, exact metadata resolution; selected-only formula/system fields; histories reconstruct hit and chemical-system counts |
| W1.4 Saved-stage registry | `scripts/export_structures.py`, registry/stage records | All eleven model selections plus excluded and separate source-QE entities; 14 entities/26 stages; actual recorded parent/source relations |
| W1.5 Contracts and parsing | `src/data/contracts.ts`, strict exporter helpers, `src/data/loadRelease.ts` | Typed stable enums, units/nulls/booleans; SHA-verified same-origin release loading; JSON disallows non-finite numbers |
| W1.6 Curated export/versioning | `scripts/export_research.py`, pinned release module and immutable manifest | 42 logical JSON datasets and 33 assets; content-addressed filenames/release; separate study/export/UI-build identities; no scientific job launch |
| W1.7 Geometry fidelity | Geometry roundtrip checks and `reports/W1_GEOMETRY_NOTES.md` | Saved row-vector lattice/fractional coordinates/species/occupancy/PBC/site IDs; 14 non-orthogonal stages; unknown stage SG settings stay null |
| W1.8 Content and notices | `scripts/export_content.py`, `THIRD_PARTY_NOTICES.md`, retained dependency licences, per-stage PNGs | Claims/glossary/colours/methods/source summaries; actual fallback image for all 26 stages; scoped attribution; unpublished destinations remain null |

The public package preserves the planned negative and incomplete outcomes:
Full underperforms Quality in every recorded split; new-formula transformer
eligibility remains 0/48; all twelve larger-cell diagnostics remain excluded;
the four prototypes remain a separate baseline method. All nineteen QE jobs and
218 reference memberships/215 missing memberships are retained, including the
incomplete perturbation. Three accepted relaxed geometries correspond to two
accepted source-reference IDs, not three newly discovered materials.

## Corrections completed during review

- Replaced the generic structure fallback gap with **26 actual stage-specific
  Matplotlib PNGs**. The source geometry stays unwrapped; each illustration
  discloses visual wrapping and physical atom count. Total image bytes are
  782,044 and the largest is 35,748 bytes. Pillow verified every PNG; the
  CaMg2O3 prototype and TiO2 P1 final were visually inspected.
- Preserved source-reference identity: eight-atom CHGNet rocksalt and two-atom
  accepted source-QE MgO are separate entities. Only the generated MgO chain has
  a proven public model → QE parent. The failed perturbation adds evidence, not
  an accepted terminal stage.
- Corrected CHGNet's licence attribution. Installed 0.4.2 metadata and its
  retained licence agree with the current upstream licence: **Modified BSD**
  with three redistribution conditions and an enhancement grant. It is not MIT.
  The installed citation verifies the seven credited authors.
- Verified WBM/MP 2022 CC BY 4.0 and the WBM creator names against the primary
  Matbench Discovery dataset registry. Figshare also identifies its collection
  licence and credits Janosh Riebesell. The notice identifies selected-only
  joins, summaries, conversion, substitution and fresh local calculations.
- Kept scientific software credits distinct from code redistribution. The public
  bundle contains no generator/model weights, QE executable, scientific Python
  environment or pseudopotential file.
- Retained exact installed frontend licence/notice files rather than relying
  only on top-level MIT labels. `W1_DEPENDENCY_LICENSES.json` records 73 installed
  packages and 89 copied files; the public release includes the combined texts.

## Integration and later-phase boundaries

No remaining W1 content implementation gap was identified after the corrections.
Final root integration also added the excluded-stage label to the shared theme
and validates that every actual stage/policy enum has its required display label.
The [completion report](W1_COMPLETION.md) records the final matching release,
independent-validation, loader and type/build checks. This content review does
not substitute an older report for a new release's verification.

The overview and uncertainty research PNGs exceed the *normal* 300 kB image
target. Their sizes are declared in the export report; they are below the
provider's other-file cap. W6 owns optimization and measured initial-transfer
acceptance. This is not a reason to alter a scientific figure's numbers or omit
the evidence.

W2/W4 must map stage enums to the explicit method/status labels, use each
stage's actual fallback mapping and preserve the unknown/absent states.
Interactive controls, WebGL context-loss handling, chart accessibility,
displayed-data downloads, browser validation, final release packaging and live
hosting remain assigned to their later phases. A static stage image or data
contract alone is not completion of the interactive viewer.

The reviewed public source summaries and notice assets contain no Windows
absolute paths, hosting administrator links or session/login material. Source
checkout references in the notice are plain explanatory paths, not public
navigation links. The report/repository/video destinations remain unavailable
until separate checked public assets exist.
