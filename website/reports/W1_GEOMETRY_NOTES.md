# W1 saved-geometry export

The exporter is `scripts/export_structures.py`. It reads the frozen study through
`ExportContext`; it does not run a model, relaxation, symmetry finder, structure
matcher or scientific finalizer. Geometry arithmetic checks the saved basis and
coordinate convention without optimizing or reclassifying a structure.

## Coverage

The public logical dataset `structures/index.json` identifies **14 entities and
26 saved geometry stages**:

| Entity group | Entities | Saved stages |
|---|---:|---:|
| Symmetry comparison selections | 4 | 9: four generated inputs, four CHGNet finals, one accepted MgO QE final |
| Prepared prototype baselines | 4 | 8: four prepared inputs and four CHGNet finals |
| Same-composition CHGNet references | 3 | 6: three catalog inputs and three CHGNet finals |
| Excluded twelve-atom CaMg2O3 draw | 1 | 1 generated/excluded stage |
| Separately executed source-QE references | 2 | 2 accepted QE finals |
| **Total** | **14** | **26** |

All eleven selected CHGNet results are present. The two symmetry pairs retain
their primary/supplementary scopes and one-per-arm selection. The excluded
twelve-atom transformer draw remains distinct from the six-atom CaMg2O3
prototype and remains ineligible in its exported stage.

The eight-atom known MgO sequence has a proven generated → CHGNet → accepted-QE
parent chain. The accepted QE result names the CHGNet geometry and its hash as
its input. The two-atom accepted MgO source reference is a separate entity from
the eight-atom CHGNet rocksalt reference. CaO's accepted source reference is also
separate. Their unexported intermediate QE input geometries are referenced by
public source ID rather than fabricated as model frames.

The incomplete Phase 5 MgO perturbation is an evidence-only item. It has no
accepted terminal geometry stage or accepted energy. No new stable material or
complete competing-phase hull is asserted.

## Contract and provenance

Each stage carries candidate/stage IDs, its recorded public parent when present,
the recorded parent source ID, source hash, evidence references, method, stage,
eligibility, DFT validation and novelty fields. These are separate fields: an
available geometry is not evidence of stability or authorization for a new job.
`queueSelected` means the recorded historical frozen queue at that stage;
`newPhase5DFTDispatchAuthorized` is false throughout this export.

Every stage and registry row also identifies a stage-specific static fallback
through `fallbackFigureLogicalName`. The 26 PNGs are rendered from the verified
geometry using Matplotlib; none require WebGL. Their display metadata explicitly
discloses fractional wrapping into the unit cell, no added periodic images and
the same physical atom count. Source geometry remains unwrapped in JSON.

The geometry preserves lattice **row vectors in angstroms**, saved fractional
coordinates, saved site order, element/occupancy records and PBC flags. Cartesian
coordinates follow `fractional @ lattice`. No display wrapping, added periodic
images, primitive-cell reduction or atom duplication is applied. Every exported
site is ordered with occupancy one, so the number of saved sites is the physical
atom count for these selected records.

Generated and CHGNet-final SG values use existing frozen measurements at 0.01 Å
and 5°. The accepted MgO SG measurements also come from the frozen study. Initial
prototype/reference cells and the accepted CaO final have null SG settings where
this exporter lacks a saved stage-specific measurement. It does not infer a
measurement from a catalog phase name or run a new symmetry analysis.

Energy is absent at initial/excluded stages. CHGNet model energies have model and
checkpoint identity plus relaxation settings; accepted QE energies have PBE,
cutoffs, actual mesh, target spacing, spin/occupation settings and pseudopotential
hashes. Energy units are eV/atom. A UI must require matching composition, engine
and compatible settings before comparing values; matching a display unit alone
is insufficient.

Every discovered input is bound to the final Phase 6 manifest or an already
verified planning-inventory hash before use. Original CIF inputs are checked
against their saved model-input JSON conversions. Only opaque public source IDs,
safe labels and hashes enter provenance payloads; raw Windows paths do not.

## Verification performed

The final isolated export using the existing analysis environment passed
**873 checks**, including the context's complete before/after source and baseline
checks. Repeated exports add cache-hit verification checks. It registered 88
sources including the initial planning inventory and produced 27 logical JSON
datasets containing 107,969 bytes before release filenames are assigned. Those
counts are for the isolated geometry export; the integrated W1 export adds other
datasets and checks.

All 26 fallback PNGs passed Pillow's image verification, totalled 782,044 bytes
and were individually below 35,749 bytes. The CaMg2O3 prototype and TiO2 P1 final
figures were visually inspected for correct labels, actual unit-cell geometry,
species colours and wrapping/count disclosures. Cache publication uses atomic
file replacement so another export cannot consume a partially written PNG.

All 26 stages passed saved Cartesian-coordinate agreement, fractional/Cartesian
roundtrip, right-handed determinant/volume, periodic-distance roundtrip,
site/occupancy and actual-atom checks. **14 stages have actual non-orthogonal
cells**, so the row-vector convention was exercised beyond cubic MgO. All model
and accepted-QE energies passed normalization by their actual atom count. Both
separate QE source-reference material IDs resolve to recorded accepted inventory
memberships. All source and numerical-study baseline hashes remained unchanged.

Pymatgen emits its existing CIF-parser notice about rounding eight fractional
coordinates in one input; the exported saved JSON is preserved, and the original
CIF-to-saved-JSON lattice/site checks pass. This is file conversion verification,
not a new geometry calculation.
