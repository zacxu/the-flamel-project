# Publication storage decisions

> Current CI implementation: [Phase 6](../reports/GITHUB_PUBLICATION_PHASE6.md) and [CI guide](../CI.md). The Phase 6 overlay pins the complete published Phase 5 baseline; current recovery seals remain independent of Git. The permitted-archive policy and existing hosting are unchanged.

> Current source publication: [Phase 5](../reports/GITHUB_PUBLICATION_PHASE5.md). Git source and initial CI are published in the private repository; optional release assets remain local and unpublished. Use the Phase 4 public selector for future asset distribution.

<!-- phase4-current:start -->
> **Current reproduction:** [Installation guide](../INSTALLATION.md), [Phase 4 report](../reports/GITHUB_PUBLICATION_PHASE4.md), [public asset instructions](phase4/ASSETS.md) and [current public selector](phase4/public-assets.json). The new tool verifies/hydrates the permitted 11 originals plus notice ZIP and retrieves exact upstream inputs. The older 14-archive commands below remain full private-recovery instructions.
<!-- phase4-current:end -->


<!-- phase3-current:start -->
> **Current publication policy:** [Phase 3 audit](../reports/GITHUB_PUBLICATION_PHASE3.md), [disposition override](phase3/disposition-overrides.json), [release selection](phase3/release-selection.json) and [staging instructions](phase3/STAGING.md) supersede preliminary Phase 2 decisions. The signed download-header original stays private. Eleven archives are candidates requiring the companion notice pack; three UPF-containing archives stay private. All remain local/unpublished. Historical Phase 2 counts and manifests below are retained as evidence.
<!-- phase3-current:end -->


<!-- backup-relocation-current:start -->
> **Current backup:** D:\Backups\TheFlamelProject. See [current recovery and cleanup status](../reports/BACKUP_RELOCATION.md).
> Historical receipts retain their original paths and hashes. Current cleanup: complete.
<!-- backup-relocation-current:end -->

Phase 2 assigns every frozen input file exactly one destination. See [the completion report](../reports/GITHUB_PUBLICATION_PHASE2.md), [storage policy](storage-policy.json), [summary](storage-summary.json) and [retrieval instructions](RETRIEVAL.md).

## Selected contents

| Destination | Input files | Original bytes |
|---|---:|---:|
| Git | 5,118 | 297,230,585 |
| Versioned release archives | 5,579 | 5,572,611,064 |
| Recreate/retrieve; exact originals retained in Phase 1 | 94,868 | 13,340,019,207 |
| Private configuration backup only | 1 | 1,053 |
| Total frozen inputs | 105,566 | 19,209,861,909 |

These are input-cutoff totals. The plan and newly generated Phase 2 controls are separately inventoried and sealed externally to avoid a manifest hashing itself. Every actual project file is covered by either the frozen input dispositions or that generated-control inventory.

Git retains all project research/application source, configuration, small scientific evidence, required vendor source/notices, website src/public/contracts/scripts/licences, validation reports, deployment tooling, Apache configurations and all 60 retained image sidecars, including the 33 active sidecars. All 103 website-bound original inputs remain in Git. The six approximately 20.7 MB validation reports remain because current checks read them. The largest input Git file is 20,705,627 bytes.

The 86 selected CrystalFormer source files match pinned upstream originals. Its local .env is kept private. All 67 generated build-file copies are identical to selected original source; no unique local code is lost. QE's 13 distribution/component notices remain in Git. No new blanket software licence has been chosen.

Large model lineages, raw datasets, composition catalogs, exact pseudopotential inputs, all scientific scratch/restart evidence, the checkpoint and compiled/historical website packages are in archives. Small .pkl/.npz evidence is retained in Git where selected; filename extensions alone do not determine whether evidence is dropped.

## Inventories and staging

- file-dispositions.jsonl.gz: complete compact per-file path, size, SHA-256, reason, destination and verified backup mapping.
- git-input-files.json: frozen Git input file records.
- git-files.txt and git-pathspec.nul: exact selected Git paths, including generated Phase 2 controls.
- artifacts.json: archive sizes/digests, every member's path/size/digest and explicitly unpublished availability.
- pinned-upstreams.json: upstream retrieval records and exact hashes.
- generated-control-paths.json: declared generated-file scope; its full byte inventory is sealed outside this project.
- SHA256SUMS: checksums of the primary storage manifests.

The retained archives and backup records are under:
D:\Backups\TheFlamelProject\phase2-20261111-0225-SGT

The historical review tree was a byte-verified validation duplicate and is removed. It is not required for recovery; use the retained source inputs, allowlist and archives. Git was not initialized and no files were staged or uploaded.

Phase 3 replaced broad root exclusions with explicit dispositions and byte-preserving attributes. Eight unchanged CrystalFormer originals retain upstream ignore conflicts; their exact hash-checked staging exceptions are documented. The prior count of 114 conflicts belongs to the unchanged Phase 2 receipt.

## Archive policy

Fourteen ZIP assets total 5,582,625,555 bytes. All are below the local 1 GiB limit. They contain 5,579 project members and 130 production-recovery members. The latter are the 123-file active-site recovery tree plus seven recovery metadata/tool files.

No Git LFS pointers are selected for this frozen baseline. GitHub Release assets allow large evidence downloads to remain optional. GitHub currently rejects ordinary Git files over 100 MiB; the local policy keeps input Git files below 50 MiB and release assets below 1 GiB, within the documented release-asset limit. [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github), [release guidance](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

All archives are LOCAL and UNPUBLISHED. The later Phase 3 selection decides which may proceed to release preparation. Planned URLs are metadata, not working download links. Phase 3 records scoped credential/rights review and private-only exclusions; dependency advisories and fresh installation remain explicit follow-up work. Publishing or changing availability metadata belongs to later phases.

## Recovery scope

Phase 1's exact original backup remains unchanged. Every recreate/private record points to that verified original or a separately preserved post-snapshot copy. The environments/runtimes may be recreated later; Phase 2 did not test portable installation or invoke historical setup scripts.

The production archive uses Phase 1's verified active application capture. Protected .htaccess files came from accepted local records; their effective behavior was checked live in Phase 1. Unknown/obsolete physical hosting files were not enumerated. Phase 2 restored and verified that recovery set without recapturing or changing hosting. After a real deployment, the saved submission link and browser controls still require live acceptance.