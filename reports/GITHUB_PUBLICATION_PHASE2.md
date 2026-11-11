# GitHub publication Phase 2: complete

<!-- backup-relocation-current:start -->
> **Current backup:** D:\Backups\TheFlamelProject. See [current recovery and cleanup status](BACKUP_RELOCATION.md).
> Historical receipts retain their original paths and hashes. Current cleanup: complete.
<!-- backup-relocation-current:end -->

Completed 11 November 2026. Every frozen input file has a storage decision and verified recovery mapping. The prepared assets are local/unpublished; Phase 3 secret, sensitive-data and redistribution review remains pending.

[Storage decisions](../publication/README.md) · [Retrieval and verification](../publication/RETRIEVAL.md) · [Policy](../publication/storage-policy.json) · [Artifact manifest](../publication/artifacts.json).

## Content inventory

| Destination | Frozen input files | Original bytes |
|---|---:|---:|
| Git | 5,118 | 297,230,585 |
| Release archives | 5,579 | 5,572,611,064 |
| Recreate/pinned retrieval; original backup retained | 94,868 | 13,340,019,207 |
| Private configuration backup | 1 | 1,053 |
| Total | 105,566 | 19,209,861,909 |

The input cutoff includes the Phase 1 additions and excludes this phase's declared generated-control paths, including the plan. Generated tools/docs/manifests and completion receipt mirrors are classified separately as Git controls and sealed in the external control inventory. Counts and bytes reconcile exactly; no input is silently dropped.

The Git input selection is 297.23 MB before generated controls, with no input file over 20,705,627 bytes. It preserves project source/configuration, small scientific evidence, all 103 bound website input files, website validation reports, all 60 saved deployment sidecars (33 active), source/deployment tooling and current/historical hosting policies. Existing frozen bytes and line endings were retained. Small evidence pickles are explicitly selected.

All 86 non-environment CrystalFormer original files match the pinned source. All 67 generated build copies are identical to selected source; no unique code is omitted. All 13 QE component notices remain selected. The local .env remains private. No blanket checkpoint or binary redistribution licence was inferred.

## Prepared archives and actual restore verification

Fourteen stored ZIPs total 5,582,625,555 bytes. Each is below 1 GiB. All archive digests, regular-file member sets, member lengths and member SHA-256 values passed independent verification.

| Archive | Members | Archive bytes | Restore scope |
|---|---:|---:|---|
| flamel-active-production-001.zip | 130 | 8,510,319 | production |
| flamel-composition-catalogs-001.zip | 2 | 61,558,121 | project |
| flamel-crystalformer-checkpoint-001.zip | 1 | 166,094,303 | project |
| flamel-historical-datasets-001.zip | 3 | 241,635,204 | project |
| flamel-qe-scratch-001.zip | 1974 | 804,920,049 | project |
| flamel-qe-scratch-002.zip | 2797 | 582,234,847 | project |
| flamel-qe-scratch-003.zip | 1 | 239,904,254 | project |
| flamel-research-inputs-001.zip | 41 | 37,717,958 | project |
| flamel-research-models-001.zip | 31 | 791,135,064 | project |
| flamel-research-models-002.zip | 31 | 790,600,275 | project |
| flamel-research-models-003.zip | 31 | 790,731,084 | project |
| flamel-research-models-004.zip | 31 | 790,882,986 | project |
| flamel-research-models-005.zip | 6 | 153,282,397 | project |
| flamel-website-builds-001.zip | 630 | 123,418,694 | project |

All 5,579 project members (5,572,611,064 original bytes) were restored into a fresh directory and independently rehashed. All 130 production-scope members were also restored and independently checked. These include the 123 active-site recovery files plus seven metadata/tool files. The production package's own standalone offline verifier passed for 123 files and 75 research payloads.

All 24 portable safety fixtures passed, including corruption, unsafe paths, duplicates/case collisions, links/junctions, overwrite rejection, merge preflight and planned URLs never being fetched. No destination file was overwritten. These checks did not retrain models, rerun DFT or establish new scientific results.

## Exact local locations and availability

- Prepared archives: C:\Users\Admin\Backups\TheFlamelProject\phase2-20261111-0225-SGT/archives
- Byte-verified Git review tree: C:\Users\Admin\Backups\TheFlamelProject\phase2-20261111-0225-SGT/git-review-tree
- Project artifact restore: C:\Users\Admin\Backups\TheFlamelProject\phase2-20261111-0225-SGT/restored-project
- Production recovery restore: C:\Users\Admin\Backups\TheFlamelProject\phase2-20261111-0225-SGT/restored-production
- Full generated-control seal/backup: C:\Users\Admin\Backups\TheFlamelProject\phase2-20261111-0225-SGT/control-files.json and controls/bears
- Final aggregate receipt: C:\Users\Admin\Backups\TheFlamelProject\phase2-20261111-0225-SGT/PHASE2_COMPLETION.json, mirrored in reports/github-publication-phase2/COMPLETION.json

The complete per-file disposition inventory is publication/file-dispositions.jsonl.gz (5,865,012 bytes). Each record includes path, size, SHA-256, destination/reason and exact verified original-backup mapping. The artifact manifest records each archive's actual local bytes/digest and every member; download_url remains null and planned URLs are explicitly unpublished.

Pinned upstream recipes preserve URLs and digests for optional distributions. Exact originals remain in Phase 1. No new upstream retrieval or portable installation was claimed; do not invoke historical setup scripts on the frozen working tree.

## Follow-up and boundaries

Current ignore rules conflict with 114 selected inputs. Their paths/rules remain in the summary for Phase 3; actual ignore files were not changed and root Git was not initialized. The exact literal allowlist is a reviewed baseline, not permission to bypass the later security/integrity checks. Future phase additions must be inventoried before the Phase 5 push.

Git LFS is deliberately unused for this frozen baseline. Large evidence uses optional checksummed archives. Archives were not uploaded, release URLs/tags were not created and hosting was not changed.

The production archive preserves Phase 1's active-website recovery capture. Protected Apache policies come from accepted local records with effective behavior checked during Phase 1. This is not a new live capture or exhaustive export of unknown physical hosting files. A real deployment still requires the existing publication guard and saved-submission/browser acceptance.

**Phase 2 completion condition satisfied:** every input and generated file has an explicit disposition, and all required assets remain recoverable. Final clearance, portable installation, Git publication and production deployment remain in their later phases.
