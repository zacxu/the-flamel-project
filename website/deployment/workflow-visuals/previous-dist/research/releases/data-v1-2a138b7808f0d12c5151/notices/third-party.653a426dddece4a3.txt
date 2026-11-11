# The Flamel Project: source and software notices

Reviewed 22 October 2026 for the frozen-study website export. The public exhibit
contains selected recorded results, source-derived metadata/structures and locally
prepared research figures. Scientific programs, pretrained checkpoints, complete
datasets, pseudopotential files and local runtimes are excluded from the public
payload. The credits below identify their distinct roles; they do not imply
endorsement by the credited people or institutions.

## Historical data and source geometries

**Wang–Botti–Marques (WBM) data.** Credit Hai-Chen Wang, Silvana Botti and Miguel
A. L. Marques. Matbench Discovery's distributed data collection is credited to
Janosh Riebesell and contributors. WBM is listed under **CC BY 4.0** in the
[Matbench Discovery dataset registry](https://raw.githubusercontent.com/janosh/matbench-discovery/main/data/datasets.yml).
The associated [Figshare data collection](https://doi.org/10.6084/m9.figshare.22715158)
also identifies CC BY 4.0. The [original WBM paper](https://doi.org/10.1038/s41524-020-00481-6)
describes the underlying data. The website selects 1,250 recorded query events
involving 720 material IDs, joins selected formula/system metadata and presents
grouped outcomes. These are adaptations of selected records, not new historical
labels or a redistributed complete benchmark.

**Materials Project v2022.10.28 snapshot.** Credit the Materials Project Team.
The same [dataset registry](https://raw.githubusercontent.com/janosh/matbench-discovery/main/data/datasets.yml)
identifies the pinned MP 2022 snapshot as **CC BY 4.0**. The website uses selected
composition/reference memberships and small source-derived structure subsets;
catalog membership and geometry coverage remain tied to the frozen snapshot.
Compatible fresh QE calculations are separately identified as this project's
calculations. They are not Materials Project calculations or replacements for
the historical labels.

Source-derived CC BY 4.0 material retains its upstream attribution and licence.
See the [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/).
Filtering, selected-only joins, summaries, format conversion, prototype
substitution and locally performed relaxation are identified in the methods and
stage/source records. No global/current-catalog completeness is asserted.

## Scientific software used to obtain the recorded study

**CrystalFormer.** Credit Zhendong Cao, Xiaoshan Luo, Jian Lv, Lei Wang and
contributors. The [upstream project](https://github.com/deepmodeling/CrystalFormer)
and the experiment's local checkout provide an
[Apache License 2.0](https://raw.githubusercontent.com/deepmodeling/CrystalFormer/main/LICENSE).
The research used an existing pretrained generator; the exhibit shows saved
outcomes and does not distribute CrystalFormer source code or model weights.

**CHGNet 0.4.2, model 0.3.0.** Credit Bowen Deng, Peichen Zhong, KyuJung Jun,
Janosh Riebesell, Kevin Han, Christopher J. Bartel and Gerbrand Ceder, as identified
in the installed package's citation. See the
[CHGNet paper](https://doi.org/10.1038/s42256-023-00716-3) and
[upstream project](https://github.com/CederGroupHub/chgnet).
The installed package metadata calls its licence **Modified BSD**. Its
[upstream licence text](https://raw.githubusercontent.com/CederGroupHub/chgnet/main/LICENSE)
contains three BSD redistribution conditions and an additional enhancement
grant. The copyright holder is the Regents of the University of California,
through Lawrence Berkeley National Laboratory and the University of California,
Berkeley, subject to the approvals stated in that licence. It must not be
labelled MIT merely because some other dataset or dependency uses MIT.
The exhibit distributes saved relaxation results and model-qualified energies,
not CHGNet code, pretrained weights or the MPtrj training dataset.

**Quantum ESPRESSO 7.5.** Credit the
[Quantum ESPRESSO collaboration](https://www.quantum-espresso.org/).
The experiment's vendored distribution includes the GNU GPL version 2 licence
text. This exhibit displays locally computed PBE outcomes and acceptance
evidence. It distributes no QE executables, MPI/runtime components or
pseudopotential files. The numerical records identify the pseudopotentials by
hash so the calculation settings can be distinguished without shipping those
files.

Pymatgen, NumPy, ASE, Matplotlib and other local analysis tools supported the
study/export. They do not run in a visitor's browser and their Python
environments are excluded from the website payload.

## Locally prepared figures

Research figures were prepared within The Flamel Project from the recorded
study using Matplotlib. They are not copied illustrations from upstream papers.
Their underlying source-derived content retains the attribution above.

| Public logical figure | Frozen-study content |
|---|---|
| `figures/overview.png` | Integrated Phase 6 four-panel research overview |
| `figures/uncertainty.png` | Phase 6 saved reliability and selective-risk analysis |
| `figures/structures.png` | Actual generated MgO, accepted QE MgO, six-atom prototype and excluded twelve-atom draw |
| `figures/generation.png` | Phase 4 primary first-eight generation comparison |
| `figures/model-energies.png` | Phase 5 within-composition CHGNet energy comparisons |

The structure panels use actual saved cells. Ball sizes and display wrapping in
the existing illustration are visual conventions; they do not alter physical
atom counts or scientific validation status. The geometry export preserves the
unwrapped saved coordinates. A fallback image must be identified by its real
panel/stage rather than presented as another candidate's geometry.

The website export also prepares **26 stage-specific fallback figures** under
the logical prefix `figures/structures/`, one per saved public geometry stage.
These local Matplotlib renderings use the verified stage coordinates/lattice,
identify the method/stage and physical atom count, and disclose visual wrapping.
Their source hashes remain attached through the stage registry. They do not
represent new generation, geometry optimization or inferred validation.

## Website dependencies and retained licence texts

The pinned website stack currently includes React/React DOM/React Is 19.3.1,
Recharts 3.10.1 and Three.js 0.186.1 under MIT. Build tooling includes Vite 8.3.5
under MIT and TypeScript 7.0.2 under Apache 2.0. Transitive packages have their
own licences; these top-level labels are not a substitute for their notices.

The source checkout retains exact installed-package licence/notice files under
`licenses/dependencies/`. The machine-readable inventory
`reports/W1_DEPENDENCY_LICENSES.json` records package names, versions, licence
labels, package-lock integrity and copied-text hashes. W1 captured 73 installed
packages and 89 licence/notice files; the pinned lockfile and that inventory
identify the applicable versions.

The content-addressed public release provides these logical notice assets:

- `notices/third-party.txt`: this scoped attribution notice.
- `notices/dependency-licenses.txt`: retained installed-package licence and notice
  texts, including bundled dependency notices supplied by those packages.

Resolve logical asset names through the build's pinned research manifest; do not
assume mutable file URLs. Release packaging must retain the applicable licence
texts for frontend code that is shipped. Local Node/npm distributions and
development environments stay outside the public bundle. These notices do not
assign a blanket new licence to all original project work or to unrelated
upstream assets.
