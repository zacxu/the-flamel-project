# Third-party notices for The Flamel Project repository and research artifacts

This repository combines original project code and recorded research with third-party components. Each upstream component retains its own terms. These notices do not choose a licence for the original project, relicense upstream content, or imply endorsement. The separately frozen website notice remains scoped to its original deployed exhibit; this record covers the wider source/evidence publication selection.

## CrystalFormer source and pretrained checkpoint

Credit Zhendong Cao, Xiaoshan Luo, Jian Lv, Lei Wang and contributors. The source at revision `31bb734a3fd006af49a021921839061e6184cbf1` is distributed under Apache License 2.0: [pinned CrystalFormer source licence](https://github.com/deepmodeling/CrystalFormer/blob/31bb734a3fd006af49a021921839061e6184cbf1/LICENSE) . Retain the original `vendor/CrystalFormer/LICENSE`, upstream notices/copyright and model card. The Phase 2 source comparison recorded all 87 original upstream files as identical; 86 non-environment originals were selected for Git and the upstream local `.env` was kept private. Generated build copies and project-created outputs are separate from the unchanged upstream originals. This audit did not rerun that source comparison.

The exact pretrained weights used were `alex20s/multi/epoch_044000.pkl` from the Hugging Face repository `zdcao/CrystalFormer`, revision `b203f4273158d95b49b60a13433bf1dcc4ccf5d9`. The README at that exact model-repository revision explicitly declares `license: apache-2.0`, independently of the source-code licence: [pinned CrystalFormer model-repository declaration](https://huggingface.co/zdcao/CrystalFormer/blob/b203f4273158d95b49b60a13433bf1dcc4ccf5d9/README.md) . The API card metadata agrees. Retain this model-repository declaration and a complete Apache 2.0 licence copy alongside any redistributed checkpoint archive. Retain source identity and upstream attribution; flag any later changed files as changed. The recorded checkpoint SHA-256 is `847e8f3962226d0539722c851bd615479d9c7fc2d5be9112898c1cdd2b7b700a`; this audit did not rehash or download the checkpoint. Code and checkpoint Apache 2.0 declarations are separate observations. No inference is made about redistribution rights to the original Alexandria training dataset.

## WBM and historical Materials Project data

Credit Hai-Chen Wang, Silvana Botti and Miguel A. L. Marques for WBM ([WBM primary paper](https://doi.org/10.1038/s41524-020-00481-6)), the Materials Project for its historical snapshot, and Janosh Riebesell and Matbench Discovery contributors for the hosted collection and registry. The exact hosted collection is Riebesell, Janosh (2023), *Matbench Discovery - Data Files*, Figshare, version 39: [Matbench Discovery data, Figshare v39](https://doi.org/10.6084/m9.figshare.22715158.v39) . Its version-specific public API identifies CC BY 4.0: [version-specific Figshare metadata](https://api.figshare.com/v2/articles/22715158/versions/39) . Licence: [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/) .

The retrieved raw files are:

- `data/mp/2023-02-07-mp-computed-structure-entries.json.gz` (Figshare file 40344436).
- `data/wbm/2022-10-19-wbm-init-structs.jsonl.gz` (file 53161835).
- `data/wbm/2023-12-13-wbm-summary.csv.gz` (file 64706751).

The file registry is pinned at [pinned dataset file registry](https://github.com/janosh/matbench-discovery/blob/2b7bff925a6aff10240cf6ef0f59149f51adff7b/matbench_discovery/data-files.yml) . The historical MP release label is v2022.10.28; filenames include their upstream export dates. These are historical frozen records, not a complete current Materials Project catalogue.

The derived catalogues `data/catalogs/mp_full_compositions.jsonl` and `data/catalogs/wbm_full_compositions.jsonl`, experimental subsets, replay labels, summary tables and research figures include filtered/transformed source-derived information. Preserve the above source/creator credit and CC BY 4.0 link with redistribution, and state that the project filtered, normalized and reformatted records for its recorded experiments and catalogue comparisons. Saved historical labels remain attributed to their source; model estimates and newly computed QE outcomes are identified separately. Do not imply upstream endorsement.

## CHGNet

Credit Bowen Deng, Peichen Zhong, KyuJung Jun, Janosh Riebesell, Kevin Han, Christopher J. Bartel, Gerbrand Ceder and contributors: [CHGNet primary paper](https://doi.org/10.1038/s42256-023-00716-3) . The project used package 0.4.2 and pretrained model 0.3.0. The installed package licence matches [CHGNet 0.4.2 licence](https://github.com/CederGroupHub/chgnet/blob/v0.4.2/LICENSE) . It is the upstream **Modified BSD** text: three BSD redistribution conditions plus an enhancement grant; it is not MIT. Copyright is held by the Regents of the University of California through Lawrence Berkeley National Laboratory and UC Berkeley, subject to the approvals specified in that text.

Retain the full original copyright, conditions, disclaimer and enhancement paragraph if redistributing code/binary components. The package and bundled pretrained model are recreated through pinned dependency installation rather than newly published as project Git blobs or these local research-model archives. Recorded CHGNet results are distinct from code, weights and the MPtrj training dataset. The trained `.joblib` archives are local project selector models; they are not CHGNet or CrystalFormer checkpoints.

## Quantum ESPRESSO and pseudopotentials

Credit the Quantum ESPRESSO collaboration: [Quantum ESPRESSO collaboration](https://www.quantum-espresso.org/) . The used Windows distribution is pinned to Quantum ESPRESSO 7.5 and records GNU GPL terms for QE plus independent Intel, Microsoft MPI and external-library terms. Retain the 13 selected README/component notice files under `vendor/quantum_espresso/qe-7.5-win-oneapi-msmpi/`. Binaries and runtimes remain upstream-retrieval/private-backup content, not newly approved redistribution. The pinned binary source is [pinned Windows QE distribution](https://github.com/QMatSuite/quantum-espresso-windows-exe/releases/tag/qe-7.5-win-oneapi-msmpi) . Retaining notices does not by itself establish source-distribution closure for a new binary release.

SSSP source record: [SSSP source record](https://archive.materialscloud.org/records/rcyfm-68h65) . Credit Gianluca Prandini, Antimo Marrazzo, Ivano E. Castelli, Nicolas Mounet, Elsa Passaro, Jusong Yu, Nicola Marzari and contributors; cite [SSSP primary paper](https://doi.org/10.1038/s41524-018-0127-2) . The archive's metadata/collection are CC BY 4.0 **with pseudopotential-family exceptions**, explicitly set out in [SSSP family-specific licence record](https://archive.materialscloud.org/records/rcyfm-68h65/files/LICENSE.txt?download=1) . The complete UPF archive must not be treated as uniformly CC BY 4.0.

The exact used UPFs, matched by MD5 to `SSSP_1.3.0_PBE_efficiency.json`, are:

| UPF filename | SSSP family | Family terms in SSSP LICENSE.txt | Attribution |
| --- | --- | --- | --- |
| `Ca_pbe_v1.uspp.F.UPF` | GBRV-1.2 | GPL version 3 | K. F. Garrity, J. W. Bennett, K. M. Rabe, D. Vanderbilt; [GBRV primary paper](https://doi.org/10.1016/j.commatsci.2013.08.053) |
| `Mg.pbe-n-kjpaw_psl.0.3.0.UPF` | 031PAW (pslibrary 0.3.1 family) | GPL version 2 or later | Header author A. Dal Corso; E. Kucukbenli et al., [pslibrary family reference](https://arxiv.org/abs/1404.3015) |
| `O.pbe-n-kjpaw_psl.0.1.UPF` | 031PAW (pslibrary 0.3.1 family) | GPL version 2 or later | Header author Lorenzo Paulatto, modified by A. Dal Corso; [pslibrary family reference](https://arxiv.org/abs/1404.3015) |

Individual UPF filename versions are retained exactly; the SSSP family label does not rename them. The files contain generation/header information but no embedded full licence text. Publicly repackaging them would require the correct family notices and appropriate GPL/source closure rather than a blanket project licence. Phase 3 resolves this publication scope conservatively: the raw UPFs, full SSSP archive, and the three locally prepared archives that contain UPFs remain local/private-only; exact upstream retrieval URLs, hashes and settings remain available for reconstruction. The retained Phase 2 archive manifests describe the original bytes and are not rewritten.

The withheld archives are `flamel-qe-scratch-001.zip` (20 UPF members), `flamel-qe-scratch-002.zip` (16), and `flamel-research-inputs-001.zip` (41). Other archive and first-party source decisions still require their independent privacy/secret gates. This scope decision is not a claim that GPL-family redistribution is forbidden; it avoids a new, incompletely prepared UPF distribution.

## Website code, diagrams and images

Keep `website/THIRD_PARTY_NOTICES.md`, `website/licenses/**`, the pinned package lock and dependency inventories. The original W1 inventory records 73 packages / 89 retained licence-notice files; later W6 inventories are also retained. React, React DOM, React Is, Recharts, Three.js and Vite use their retained MIT notices; TypeScript uses its retained Apache 2.0 notice. Transitive dependency texts remain authoritative; top-level labels do not replace them. Production bundles and historical release archives retain their notice payloads. Development environments, Node distributions and `node_modules` are recreated.

The locally recorded scientific figures are project-produced Matplotlib renderings of the saved study and source-derived data; the 26 per-stage structure fallbacks are renders of actual saved cells. Underlying WBM/MP-derived information retains its upstream attribution. Seven-stage workflow cards contain original inline SVG method schematics, generalized from primary CrystalFormer and CHGNet references; they are not copied architecture figures or observed candidate trajectories. `website/reports/WORKFLOW_VISUALS_UPDATE.md` and `WORKFLOW_VISUALS_SCIENCE_REVIEW.md` record this provenance. The header icon is code-native cube/hexagon/copper linework; the retained implementation reports do not claim rights over the user's reference bitmap. Actual website screenshots are labelled as such; any separately generated promotional art must retain its illustrative/generated label and cannot be used as scientific evidence. This audit did not locate a `website/social-assets` folder or establish a new blanket licence for original website artwork.

## Retained notice pack

The [notice-pack instructions](publication/third-party/README.md) define which files must accompany a future research-artifact distribution. Complete retained texts are [Apache 2.0](publication/third-party/APACHE-2.0-CrystalFormer.txt), [the pinned checkpoint README](publication/third-party/CrystalFormer-checkpoint-README.md), [CHGNet Modified BSD](publication/third-party/CHGNet-0.4.2-LICENSE.txt), [CC BY 4.0](publication/third-party/CC-BY-4.0.txt), and [SSSP family exceptions](publication/third-party/SSSP-LICENSE.txt). [Primary evidence](publication/third-party/PRIMARY_EVIDENCE.json) records exact source URLs and observed metadata; the [component matrix](publication/third-party/PUBLICATION_MATRIX.json) records the licence-scope decisions. These records do not establish that any release has been uploaded.
