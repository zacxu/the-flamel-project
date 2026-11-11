# W4 independent requirements and scientific-scope review

Reviewed 22 October 2026 against `WEBSITE_PLAN.md` sections 2, 3 and 4C and `PHASED_IMPLEMENTATION_PLAN.md` W4.1-W4.7. The data review reads the existing immutable `data-v1-2a138b7808f0d12c5151` registry and all 26 saved-stage JSON records. It does not infer space groups, run a matcher, evaluate a model, relax a structure or submit DFT.

**Result: all seven core W4 requirements are implemented in the inspected integrated source; no unresolved scientific-scope blocker was found.** Browser interactions, actual rendering/downloads and injected runtime failures are separate acceptance evidence owned by the implementation lead. This source review does not replace those checks. W5-W7 remain outside this review.

## Saved entities and stage identity

The catalog contains **14 distinct entities and 26 saved stages**. Eleven entities have a selected CHGNet result. The other three are the excluded twelve-atom transformer example and two separate accepted source-reference QE cells. All eleven model-result records must remain discoverable even if some richer reference/prototype interactions are treated as optional.

| Entity | Physical atoms | Recorded stages | Core role |
|---|---:|---|---|
| `phase1_mgo_attempt_000` | 8 | Generated → CHGNet → accepted QE | Known MgO sequence and MgO nontrivial arm |
| `phase4_supplementary_mgo_rocksalt_p1_attempt_010` | 8 | Generated → CHGNet | Supplementary MgO P1 partner |
| `phase4_tio2_rutile_nontrivial_attempt_000` | 6 | Generated → CHGNet | Primary TiO2 nontrivial arm |
| `phase4_tio2_rutile_p1_attempt_000` | 6 | Generated → CHGNet | Primary TiO2 P1 arm |
| `prototype_SnSrO2` | 4 | Prepared prototype → CHGNet | SrSnO2 prototype baseline |
| `prototype_BaSnO2` | 4 | Prepared prototype → CHGNet | BaSnO2 prototype baseline |
| `prototype_CaMg2O3` | 6 | Prepared prototype → CHGNet | Core CaMg2O3 baseline |
| `prototype_Mg2SrO3` | 6 | Prepared prototype → CHGNet | SrMg2O3 prototype baseline |
| `reference_rocksalt` | 8 | Catalog input → CHGNet | Separate model MgO reference |
| `reference_rutile` | 6 | Catalog input → CHGNet | Model TiO2 reference |
| `reference_anatase` | 12 | Catalog input → CHGNet | Model TiO2 reference |
| `phase3_early_CaMg2O3_attempt_005` | 12 | Generated / excluded only | Core six-atom gate failure example |
| `qe_source_reference_mgo_mp1265` | 2 | Accepted QE only | Separate accepted source MgO reference |
| `qe_source_reference_cao_mp2605` | 2 | Accepted QE only | Separate accepted source CaO reference |

The source MgO QE reference is not a later stage of the eight-atom model reference or generated cell. Its two-atom source identity remains distinct. Likewise, the six-atom CaMg2O3 prototype has no stage edge to the twelve-atom excluded CrystalFormer draw. Failed/incomplete QE evidence creates no terminal geometry stage: the recorded 900-second MgO perturbation has no accepted final geometry, forces, stress or comparable energy.

The excluded draw has the correct reduced composition and requested/measured SG 2, but twelve physical atoms versus the frozen six-atom request. Displaying it does not make it workload eligible or physically unstable. No new stable material, complete hull or global novelty is established by any catalog view.

## Geometry and metadata boundaries

- Lattice vectors are rows in angstroms. Cartesian coordinates are `fractional @ lattice`, preserving cell shape, basis and zero-based saved site indices. All 26 saved records are right-handed, fully periodic, ordered cells with one species at occupancy one per site. There are 172 site instances across the saved stages; this is not a count of unique materials.
- Fourteen registry stages are non-orthogonal. Tests must include their actual matrices rather than only cubic MgO. Eleven saved stages contain at least one fractional coordinate outside `[0,1)`, so display wrapping has a real effect. Wrapped display positions may be used with disclosure; coordinate tables and exported scientific geometry retain the raw saved values. Physical atom counts exclude display images.
- SG and tolerance are unavailable for all seven initial prototype/catalog stages and the accepted CaO QE stage. These eight values remain unknown; phase names cannot fill them. The other 18 stages retain the recorded 0.01 Å symmetry precision and 5° angle tolerance. Requested and measured groups are separate fields.
- Existing prepared fallback figures are specific to the selected stage. Their wrapped display coordinates, illustrative atom sizes and lack of added periodic images are disclosed. An unrelated montage cannot stand in for the selected geometry.
- Current data have no partial occupancies or nonperiodic axes. Unsupported future geometry must fail or fall back explicitly; it must not silently acquire occupancy one or periodic axes in a display/export path.

## Energy comparison boundaries

The selected CHGNet symmetry pairs use the same checkpoint and full optimizer/settings record, with no imposed relaxation symmetry. Each arm contributes one selected structure. Recomputed P1-minus-nontrivial differences are:

| Pair | Scope | Difference (meV/atom) |
|---|---|---:|
| MgO | Supplementary primary-plus-top-up pool | 356.87923431396484 |
| TiO2 | Primary first-eight per arm | 55.80647786458215 |

These are model electronic-energy estimates, not new DFT results, population-wide energy effects, stability labels or an architectural ablation. Both generation arms use the same symmetry-aware architecture with different conditioning. The comparison must preserve that explanation.

The CHGNet anatase-minus-rutile reference difference is -19.908905029296875 meV/atom under equal settings. A per-atom comparison can be valid despite 12 versus 6 physical atoms, provided composition/engine/settings are compatible and the reference-only model scope is explicit. Cross-composition and cross-engine ranking is unavailable.

The accepted eight-atom generated MgO and two-atom source MgO share a coarse `settingsScope` string but have different saved k meshes (5³ versus 8³). A generic exact-settings comparison must inspect the complete settings record, not that string alone. Their separately reported raw QE difference of approximately -0.005533 meV/atom is numerically unresolved and is not evidence of an energy advantage. CaO and MgO QE energies must not be ranked against each other.

## Integrated acceptance review

Inspected `views/CrystalLab.tsx`, `views/Overview.tsx`, `components/CrystalDisplay.tsx`, `components/CrystalViewer.tsx`, `components/CrystalCoordinates.tsx`, `crystal/geometry.ts`, `crystal/lifecycle.ts`, `crystal/useStructureDownload.ts`, their CSS and the saved-data hook/route conventions.

| Requirement | Inspected implementation and acceptance boundary |
|---|---|
| W4.1: catalog and selection | The catalog retains all eleven model-result entities, the excluded example and both separate source-reference entities. All 26 stages are selectable by entity; six core shortcut examples expose the complete required scope. Origin/role, atoms, model-result availability, eligibility scope and recorded stages stay visible. Rich viewing of the additional saved references/prototypes is implemented through the same viewer, completing optional O2 within the existing registry. |
| W4.2: shared interactive viewer | `CrystalDisplay` lazy-loads one Three.js viewer component for both Overview's actual accepted MgO cell and the selected Crystal Lab stage. It draws species-coloured saved physical sites and twelve non-orthogonal unit-cell edges. Mouse/button/keyboard rotate, zoom and reset, site inspection and a labelled element legend are implemented. Comparison panels deliberately use two identified saved figures, avoiding extra active WebGL viewers. The frame owner renders on demand while idle, can run opt-in rotation, and cancels scheduled work when hidden, off screen or disposed. |
| W4.3: faithful geometry | Shipped pure helpers preserve row-vector fractional/Cartesian conversion, determinant/volume, source site indices, exact cell edges and physical units. Display wrapping returns fresh vectors and is disclosed beside the viewer and raw coordinate table. No bonds, images or fictitious geometry are added. Viewport resize recomputes fit while preserving relative user zoom. The geometry verifier independently checks all actual non-orthogonal cells and every saved source. |
| W4.4: actual stage identity | Stage choices come from the selected entity's registry entries, with disabled unavailable-DFT status. Existing route normalization constrains candidate/stage combinations. The component and error boundary are keyed by stage ID, and dataset hooks suppress old data while a new stage loads. Recorded parent/source IDs are inspectable. Comparisons are two labelled snapshots with separate IDs and atom counts; no morph or interpolated relaxation is offered. |
| W4.5: metadata and scientific comparison | The selected stage shows formula, actual atoms, origin, stage method, measured/requested SG, recorded tolerance or explicit unavailability, engine-qualified per-atom energy, volume, periodic minimum distance, actual exact-cell/workload flags, frozen queue selection and separate DFT validation. Source actions include the geometry, evidence, recorded symmetry source and parent source. Full actual settings gate the energy delta. Both selected symmetry-pair buttons retain primary/supplementary and one-per-arm caveats. Exclusion remains visible in the main workspace and comparison. |
| W4.6: accessibility and failure handling | The canvas is focusable and labelled, with instructions, arrow/plus/minus/Home handling, separate labelled buttons and a keyboard site selector. Auto-rotation starts off; reduced-motion preference disables it and responds to preference changes. Default touch uses vertical page pan; rotation requires an explicit checkbox. Stage-specific saved figures, source metadata and original coordinate tables remain independent of WebGL. Missing contexts, construction/render exceptions, chunk boundary errors and context loss lead to a scoped fallback/retry. Resource cleanup removes listeners/observers/controls, cancels frames, disposes geometry/materials/render lists/renderer and releases the owned context, including partial construction. |
| W4.7: full-precision structure export | The current-stage Blob download is regenerated/revoked on stage changes and unmount. CIF carries study/release, candidate/stage/source identity, source hash, eligibility and recorded symmetry; physical sites are explicit P1 without wrapping or inferred symmetry. Standard cell parameters preserve metric/volume/distances, while custom rows retain the exact original source basis. The independent NumPy/pymatgen roundtrip checks every exported saved stage. Actual browser-downloaded files must additionally be checked by the lead's download acceptance. |

## Independent numerical/export evidence

`reports/W4_GEOMETRY_VALIDATION.json` records a passed run of the shipped helper acceptance and independent NumPy/pymatgen verifier. It covers all **26 source-bound stages**, their CIF roundtrips, **676 ordered energy comparisons**, actual non-orthogonal geometries, a highly skew closest-image counterexample, partial-PBC helper behaviour and unsupported-PBC export rejection. Raw full-precision coordinates, custom source basis, species/occupancies, parser site labels and stage/source/release/eligibility metadata are checked. All allowed original input hashes agree before and after testing. The [geometry/export contract](../contracts/CRYSTAL_CONTRACT.md) records the conventions and limits.

Source review identified two small completeness improvements that are now implemented: exposing actual stage eligibility/queue flags instead of only a generic scope sentence, and including the recorded symmetry/parent source IDs in the selected-stage source action. A responsive camera-fit issue was also addressed by recomputing the limiting-FOV fit on resize. Neither fix changes scientific data.

The interactive viewer is implemented, rather than being a fallback-only release. The final W4 closure must still distinguish successful actual WebGL rendering from successful fallback recovery, and record real browser/device or screenshot limits honestly. W6 retains the broader integrated visual/device pass. No new experiment, scientific result, material discovery, website deployment or W5 analysis completion is implied by this review.
