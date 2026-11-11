# Third-party notice pack

This is the source notice pack for The Flamel Project's wider repository/research-artifact publication. It supplements the [root notice](../../THIRD_PARTY_NOTICES.md) and preserves the [website's separately frozen notice](../../website/THIRD_PARTY_NOTICES.md). It does not choose a blanket licence for original project work or record an upload.

Every future distribution of any of the **11 candidate archives** below must be accompanied by the root `THIRD_PARTY_NOTICES.md` and this complete `publication/third-party/` folder. A release may provide these as a downloadable companion notice bundle in the same release; deliver that bundle together with the research archive when mirroring or sharing the archive separately. Do not send a detached archive while omitting its applicable attribution and licence texts. Production and historical website archives must also retain their existing in-archive frontend licence payloads. Merely placing this folder in Git does not insert it into an already prepared ZIP.

The original Phase 2 ZIPs/manifests remain byte-for-byte unchanged. Future release tooling must enforce attachment of the companion pack and the separate privacy/secret/selection gates before upload. This pack records licence scope only; publication selection/status is controlled by the Phase 3 release records.

## Candidate archives requiring this pack

- `flamel-active-production-001.zip`
- `flamel-composition-catalogs-001.zip`
- `flamel-crystalformer-checkpoint-001.zip`
- `flamel-historical-datasets-001.zip`
- `flamel-qe-scratch-003.zip`
- `flamel-research-models-001.zip`
- `flamel-research-models-002.zip`
- `flamel-research-models-003.zip`
- `flamel-research-models-004.zip`
- `flamel-research-models-005.zip`
- `flamel-website-builds-001.zip`

## Three private archives

These complete original archives remain local/private-only because they contain GPL-family UPF files without a separately prepared redistribution/source closure:

- `flamel-qe-scratch-001.zip`: 20 UPF members.
- `flamel-qe-scratch-002.zip`: 16 UPF members.
- `flamel-research-inputs-001.zip`: 41 UPF members.

Pinned upstream retrieval and exact identity/settings records preserve reconstruction. The full upstream SSSP tarball and raw UPFs also remain upstream-retrieval/private-backup content. This is a publication scope decision, not a claim that GPL redistribution is forbidden. Do not relabel all SSSP files CC BY 4.0: its primary licence explicitly lists family exceptions.

## Included records

- `APACHE-2.0-CrystalFormer.txt`: full licence from the pinned source revision.
- `CrystalFormer-checkpoint-README.md`: exact pinned model-repository README independently declaring Apache 2.0 for its checkpoints.
- `CHGNet-0.4.2-LICENSE.txt`: exact pinned upstream Modified BSD text, including its enhancement paragraph.
- `CC-BY-4.0.txt`: full official legal text for the historical WBM/MP hosted data and source-derived outputs.
- `SSSP-LICENSE.txt`: exact upstream collection/family exception record; retained to explain reconstruction and the withheld UPF scope.
- `PRIMARY_EVIDENCE.json`: primary URLs, capture times, retained-text hashes and compact version-specific metadata observations. Large API responses remain in the private audit rather than being duplicated here.
- `PUBLICATION_MATRIX.json`: component decisions and the 11-candidate/3-private archive mapping. Candidate does not mean published.
- `USED_PSEUDOPOTENTIALS.json`: exact Ca/Mg/O family/MD5 identity records; it contains no UPF payload.

The root notice supplies creator credit and states the data transformations. Keep all parts together. Retain `website/licenses/**` and the original dependency notices for frontend code shipped in production. Retain original component notices for any separately redistributed third-party code. No new permission is inferred for original model training datasets.
