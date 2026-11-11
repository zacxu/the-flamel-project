# Saved crystal geometry and export contract

W4 displays the immutable W1 structure registry: **14 entities, 26 saved stages, 11 model results, three accepted QE geometries and one excluded twelve-atom draw**. This code does not generate, optimize, infer symmetry, rerun structure matching or dispatch a scientific job. A rendered geometry never changes eligibility or establishes novelty, a convex hull or a new stable material.

## Coordinate convention

`src/crystal/geometry.ts` uses the recorded lattice vectors as **rows** in Angstrom. For a fractional row vector `f`, Cartesian coordinates are `r = f L`; the inverse is `f = r L^-1`. Volume is `abs(det(L))`. All 26 recorded lattices are right-handed. An invalid singular lattice is rejected instead of constructing fictitious positions.

`wrapFractional(f, pbc)` returns a new display vector in `[0, 1)` on periodic axes and preserves nonperiodic axes. Neither the saved coordinates nor the exported fractional coordinates are wrapped. One displayed sphere represents one recorded physical site; wrapping does not add periodic images, bonds, species or atoms. Source site indices retain identity.

`cellCorners(L)` supplies the eight corners, and `cellEdges(L)` supplies the twelve physical cell edges without orthogonalizing the cell. `geometryBounds(L, additionalPoints?)` encloses the cell and supplied Cartesian positions with a bounding box, center and camera radius. These are framing aids with Angstrom coordinates, not rescaled scientific geometry.

`distancePeriodic(a, b, L, pbc)` computes the exact minimum-image site distance using a finite reciprocal-bound integer search. Componentwise fractional rounding is only a trial image: it is insufficient for skew lattices. A trial distance `R` bounds every improving image through `|(r L^-1)_i| <= R ||column_i(L^-1)||`. Only periodic axes admit integer translations. `minimumPeriodicDistance(geometry)` compares distinct recorded sites, with `null` for fewer than two sites; it does not introduce self-image sites.

## Interactive orientation and coordinate readouts

The viewer draws labelled lattice arrows `a`, `b` and `c` from the saved cell origin to the exact recorded row-vector endpoints. They may be nonorthogonal. Quick views place the camera along the positive saved vector relative to the cell centre; these are lattice-vector views, not reciprocal-lattice or Miller-plane normals. The isometric preset restores the starting camera. A separate corner `X/Y/Z` compass projects the Cartesian viewer basis through the camera quaternion in the existing render loop. The axes toggle hides both references; orientation graphics do not add physical sites or affect picking, source geometry or exports.

The atom card rounds only its visible fractional-coordinate summary to six significant figures. Values with magnitude below `0.000005` display `≈0`, with the threshold explicitly labelled. Tooltips and the expandable saved-values panel preserve the original round-trippable number strings, including small negative or unwrapped values. Camera metrics and detailed interaction/provenance notes remain available in the expandable panel. Manual rotation, presets and reset stop auto-rotation. Touch rotation remains opt-in, and reduced-motion preferences disable automatic rotation.

The orientation checks in `scripts/verify-orientation.mjs` cover all 26 saved stages, skew and signed fixtures, projected compass directions, actual arrow endpoints and owned-resource disposal. `scripts/verify-viewer.mjs --phase=CRYSTAL_LAB` writes separate refresh reports without replacing W4/W6 acceptance records.

## Saved stage and evidence identity

The registry, selected candidate ID, saved stage ID, source ID and source SHA-256 remain bound. Recorded parent stages belong to the same entity and exact source chain. The two-atom accepted MgO source reference is separate from the eight-atom generated MgO sequence. The excluded twelve-atom CaMg2O3 draw is separate from the six-atom substitution prototype. An unavailable stage has no interpolated or invented frame.

Saved `symmetry` fields are stage specific. A recorded/requested SG is not a new browser inference. An absent tolerance remains absent. Saved pinned-subset matching results retain their original scope and never become a claim of global novelty.

## Energy comparison

`comparableEnergy(left, right)` returns `{compatible, reason, deltaEVPerAtom}`. A delta is **right minus left**, available only with the same reduced composition, engine, unit, recorded settings scope and complete identical actual settings. It compares species and occupancies, rather than trusting a display formula.

The actual CHGNet settings include model/checkpoint/package, optimizer, step limit, force threshold, cell/filter and imposed-symmetry state. QE settings include functional, both cutoffs, exact k-mesh and spacing target, spin, occupations, per-element pseudopotential hashes and executable hash. Missing, unknown or invalid settings block a comparison, even when both display scopes are identical. Engine mixing and composition mixing also block it. This deliberately declines the accepted MgO QE candidate/reference pair with different actual `5 x 5 x 5` and `8 x 8 x 8` meshes; their separately qualified energies remain available.

Both recorded MgO and TiO2 CHGNet symmetry pairs pass this gate. Their deltas retain **one selected structure per arm**, with MgO's supplementary-pool and TiO2's primary-first-eight selection scopes. Energy difference is neither formation energy nor a hull distance, stability proof or replicated causal estimate.

## Full-precision CIF

`structureCif(stage, dataReleaseId?)` exports the exact saved structure as text. It uses JavaScript's round-trippable full-precision number representation for coordinates, occupancies, cell lengths/angles and source lattice rows. It preserves original unwrapped fractional site coordinates, species and site-index labels. Metadata identifies study, pinned release, candidate, stage, method, exclusion/eligibility, source ID and SHA-256. It contains no absolute local paths or credentials.

The standard CIF representation is **explicit physical sites in P1 with only `x,y,z`**. This representation avoids symmetry expansion and does not assert the generator requested P1. Recorded stage symmetry/tolerances remain separate `_flamel_recorded_*` metadata. Standard lengths and angles preserve the lattice metric and periodic distances; arbitrary Cartesian orientation is not encoded by standard cell parameters. Custom `_flamel_lattice_*` rows additionally retain the exact source basis orientation. All current stages are fully periodic; export rejects a future partial/nonperiodic geometry rather than silently changing its physical boundary conditions.

## Independent acceptance

Run `node scripts/verify-crystal.mjs` under the repository's bundled Node runtime. It imports the actual shipped helpers and invokes the existing analysis Python interpreter for `scripts/verify-crystal.py`; no packages are installed. Output is `reports/W4_GEOMETRY_VALIDATION.json`; intermediate fixtures stay under `.cache/` and are not public release files.

Checks hash-bind every original input before and after testing, compare all 26 stages directly with original saved source bytes, exercise all actual nonorthogonal cells, preserve parent identity, verify row-vector/inverse/volume/bounds/site ordering, and test skew and partial-PBC edge cases. NumPy and pymatgen independently verify Cartesian positions and all periodic pair distances. Pymatgen parses every generated CIF with rational snapping disabled: raw fields preserve unwrapped full-precision fractions, species/occupancies, labels and custom original basis; parsed structures preserve lattice metric/volume and periodic distances. All **676 ordered saved-stage energy comparisons** are independently checked against complete original composition and settings, with additional unknown/missing/changed-setting rejection tests.

The report is numerical/source verification. Browser renderer, accessibility, WebGL/context-loss and actual downloaded-file checks are recorded separately; a successful fallback does not by itself prove successful interactive rendering.
