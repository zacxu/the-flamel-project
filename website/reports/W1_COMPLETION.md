# W1 completion report

**Completed 22 October 2026. All eight W1 tasks and the W1 exit gate pass.** The result is a verified data/setup foundation for the six-view website. The scientific study remains frozen.

## Delivered foundation

The exporter reads a named, hash-bound allowlist of **103 frozen source files**. The private input-to-source-ID mapping is in [W1_EXPORT.json](W1_EXPORT.json); public provenance exposes safe source IDs, labels and hashes. It joins the 1,250 recorded selections to the local metadata table and exports only the selected 720 material IDs' required fields. Full oracle data, evaluation target IDs, model files, scientific environments, credentials and administrator/session URLs are absent from the public payload.

The stage registry contains **14 candidate/reference entities and 26 actual saved stages**: eleven initial/model pairs, three accepted QE geometries and one excluded generated example. The accepted eight-atom generated MgO has its proven model parent. The two-atom accepted source MgO reference is a separate entity; the eight-atom model reference is not its fictitious parent. The incomplete perturbation has no accepted stage or terminal energy.

Each stage preserves lattice rows in angstroms, saved fractional coordinates, species/occupancies, site indices and PBC. Cartesian conversion is `fractional @ lattice`. No symmetry finder, structural matcher, predictor, generator, optimizer or QE dispatcher is run by the website export. Recorded stage-specific symmetry/energy settings remain explicit, including unknown values. Display wrapping is separate from saved coordinates and physical atom counts.

The content package provides fourteen scoped claims, twelve glossary entries, policy/element colours, methods, attribution and publication-link availability. It includes five actual research figures and **26 stage-specific static fallbacks** rendered from verified saved coordinates. All 73 installed frontend packages' applicable licence/notice files are retained: 89 texts, also combined into a public notice asset. Source-data redistribution conditions and scientific-software credits are documented in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

The website-local toolchain uses Node **24.19.0**, integrity-checked workspace npm **12.2.1**, exact frontend dependency versions and a lockfile. The existing analysis Python performs conversion; no scientific package installation or global runtime change was needed. See [W1_TOOLING.md](W1_TOOLING.md) for runtime details and [DATA_CONTRACT.md](../contracts/DATA_CONTRACT.md) for the typed data boundary.

## Release and size

| Item | Final value |
|---|---|
| Study ID | `flamel-frozen-study-20261022` |
| Numerical freeze | `2026-10-22T02:55:47.255190+00:00` |
| Data release | `data-v1-2a138b7808f0d12c5151` |
| Manifest SHA-256 | `3b55f64687a8dd270482b3a2dfc9395672dbbce836fd90041712d2750e228e3d` |
| JSON datasets / assets | 42 / 33 |
| Content bytes, excluding manifest copies | 3,776,700 |
| Largest JSON shard | 254,392 bytes; below 500 kB |
| Stage-specific PNGs | 26; 782,044 bytes total; largest 35,748 bytes |
| Foundation JS | 219,846 bytes uncompressed; approximately 68.74 kB gzip |

The generated [release.ts](../src/data/release.ts) pins the immutable manifest. [loadRelease.ts](../src/data/loadRelease.ts) verifies that manifest, file hashes/sizes and dataset identities. The fixed-name public manifest is only a discovery pointer. Study freeze time, export time and the future final UI build ID remain separate; W1 does not invent a final UI release ID. Unpublished intermediate local bundles were removed, and the production smoke build contains only the active research release.

## Evidence and checks

| Verification | Result | Record |
|---|---:|---|
| Source export, arithmetic and read-only guards | 3,082 passed | [W1_EXPORT.json](W1_EXPORT.json) |
| Independent saved-source/public-data validation | 108,571/108,571 | [W1_VALIDATION.json](W1_VALIDATION.json) |
| Real loader through local HTTP | 10/10 | [W1_LOADER_VALIDATION.json](W1_LOADER_VALIDATION.json) |
| Tooling, local HTTP and production-copy integrity | 124/124 | [runtime.json](runtime.json) |
| Strict TypeScript and Vite build | Passed, exit 0 | `npm run build`; final closure record |
| Installed dependency notices | 73 packages / 89 texts | [W1_DEPENDENCY_LICENSES.json](W1_DEPENDENCY_LICENSES.json) |
| Content/plan coverage | All eight tasks covered | [W1_CONTENT_REVIEW.md](W1_CONTENT_REVIEW.md) |

Independent validation imports no exporter modules. It reconstructs replay hits, reference-hull hits, cumulative system coverage and sample SD from recorded events and source tables; checks the source joins; and independently checks geometry coordinates, energies, periodic distances, source/parent hashes and acceptance layers. The matrix includes:

- Replay: 1,250 events, 720 distinct selected IDs, 125 measured curve points, 25 endpoints and a separately labelled derived zero-query origin.
- Uncertainty: 130 snapshots, 300 risk/retention rows, 300 decile rows and ten role rows.
- Generation: 88 actual draws, twelve cohorts, 0/48 new-formula exact-cell successes, twelve excluded diagnostics, four prototypes, eleven model finals and two selected energy pairs.
- DFT: nineteen attempts, three fully checked relaxed geometries, two accepted original source-reference IDs, 218 reference memberships and 215 missing memberships; overlapping systems remain explicit.
- Geometry: 26 stages, fourteen nonorthogonal cells, per-stage fallbacks and verified separation of source-reference cells from generated/model cells.

The loader tests exercise the actual TypeScript loader under Node 24, not a rewritten test copy. They load the pinned manifest and actual datasets/assets under a nested static base, reject missing/wrong-media assets and same-length corruption, and confirm that the mutable discovery pointer is never fetched. The tooling gate compares all 75 content assets plus the immutable/discovery manifests to the actual production copy and rejects unrelated research releases.

All four baseline files retain their original SHA-256 values: Phase 6 manifest, numerical freeze, budget ledger and runtime experiment-event ledger. All 103 source bytes are unchanged. **New scientific experiments: zero.** Frozen conclusions, including the negative acquisition result, scoped novelty, known-phase MgO recovery and incomplete competitor/perturbation validation, are preserved.

The exporter emits existing pymatgen deprecation and source-CIF rounding warnings. The independent source/coordinate checks pass; no dependency or source file was changed to suppress them. The recorded npm advisory response reports zero vulnerabilities at its timestamp.

## Handoff

Use the working commands in [README.md](../README.md). Run `build` after export/code changes and before `tooling:verify`, because the latter checks the existing production copy. The final [W1_COMPLETION.json](W1_COMPLETION.json) binds the release, reports, implementation files, parent hashes and final build inventory.

**Next: W2**, following the unchanged six-view scope in the phased implementation plan. W2-W7 still own interactions, 3D controls, accessible fallbacks in the viewer, downloads, integrated browser QA, the guided tour, final upload packaging and live hosting verification. No hosting login/upload or deployment was performed in W1.

Two retained original research PNGs exceed the normal 300 kB image target: overview 487,608 bytes and uncertainty 431,041 bytes. W6 must assess optimization and initial transfer without altering the scientific content. The W1 data assets total 3.78 MB and are already below the overall approximately 10 MB content goal; later UI growth still requires its own measurements. No W1 exit item remains open.
