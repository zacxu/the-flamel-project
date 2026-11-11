# GitHub publication Phase 1: complete

<!-- backup-relocation-current:start -->
> **Current backup:** D:\Backups\TheFlamelProject. See [current recovery and cleanup status](BACKUP_RELOCATION.md).
> Historical receipts retain their original paths and hashes. Current cleanup: complete.
<!-- backup-relocation-current:end -->

Completed 11 November 2026. The original-project backup, independent destination verification, full restoration rehearsal and active-production reconciliation passed.

## Recovery locations

- Working project: `D:\bears`.
- Independent backup: `C:\Users\Admin\Backups\TheFlamelProject\phase1-20261111-0140-SGT`.
- Accepted original snapshot: `project-snapshot\bears` under the independent backup.
- Complete inventory: `project-snapshot\inventory.jsonl` and `inventory.sha256`.
- Full restoration rehearsal: `D:\bears-phase1-restore-20261111-0140-SGT`.
- Active-site recovery tree: `production\htdocs` under the independent backup.
- [Offline verification and restoration instructions](github-publication-phase1/RECOVERY.md).
- [Final acceptance receipt](github-publication-phase1/COMPLETION.json).
- [Inventory summary](github-publication-phase1/INVENTORY_SUMMARY.json).

Windows storage associations confirm that the backup on C: is on physical disk 1 and the source on D: is on physical disk 0. This is a separate local-disk backup, not an off-machine or cloud backup.

## Original project preserved

The original pre-documentation snapshot contains **105,551 files**, **11,077 directories including the root**, **8 empty directories**, and **19,209,577,902 file bytes**.

No files were excluded. Hidden/ignored environments, caches, runtimes, node_modules, vendor distributions, checkpoints, datasets, model lineages, scientific scratch files, research source/configuration, successful/failed outputs, historical production packages, hosting configurations, sidecars and rollback records are retained.

Every file inventory entry records relative path, size, SHA-256, original metadata/file identity, backup location and provisional intended storage category. Directories and empty directories are recorded. Publication categories remain subject to Phase 2; this backup does not finalize exclusions.

Inventory SHA-256: `0a224fb688a3bd99825e5e53dd999ad2c4874c42675b8715a6a05e580b6aa17d`.

The source was checked before, during and after capture, then checked again before adding the phase documentation. Every backup file was independently reopened and hashed. Exact file/directory sets, file lengths, content digests and file modified times matched. The original .gitignore remains unchanged.

## Restoration and safety verification

A full restoration into a fresh directory independently verified all **105,551 files** and **19,209,577,902 bytes**, with matching path sets and file modified times. No source overwrite, network access or GitHub access was needed.

All **10 isolated recovery-tool safety fixtures passed**, covering hidden/ignored and empty files/directories, binary/CRLF/Unicode data, hardlink materialization, overwrite/nesting rejection, same-length/same-mtime corruption detection, inventory tampering and restoration to a missing original location.

The rejected first backup attempt is retained separately at `original-project/FAILED.json`. Windows DirEntry.stat returned zero inode/device identifiers while os.stat returned real identifiers. Version 1.1 uses consistent os.stat metadata and passed the safety fixtures. Only `project-snapshot/verification.json` with status VERIFIED is an accepted original backup.

[Backup verification](github-publication-phase1/BACKUP_VERIFICATION.json) · [Full restore verification](github-publication-phase1/RESTORE_VERIFICATION.json) · [Tool safety validation](github-publication-phase1/TOOL_VALIDATION.json).

## Current production reconciled

Read-only live HTTPS retrieval established:

- All **88 active release files**, totaling **5,691,844 bytes**, match the retained release package byte-for-byte.
- All **33 separately downloaded image backing sidecars** match their retained hashes.
- Two accepted local Apache configurations are preserved.
- The complete active-site recovery tree has **123 files**, totaling **8,228,951 bytes**.
- Root, /refresh and /index.html returned the current entry with Cache-Control: no-store.
- UI identity: `ui-w6-351e6182d7af3a9d062d`.
- Research identity: `data-v1-2a138b7808f0d12c5151`.
- **452 production checks passed**, with zero failures.
- Standalone offline verification passed for every recovery file and all **75 research payloads**, without the source checkout, network or GitHub.
- Dependency closure passed for six emitted assets, 26 crystal fallback mappings and 33 backing-image mappings.

Production manifest SHA-256: `054723b75f9717b74f6f8b103cd509a3b5ca08f42550095a09da336ac232cefc`.

The protected .htaccess files came from accepted local records; physical server bytes were not downloaded. Their effective routing/caching behavior was checked live. Captured effective image responses and separately requested backing sidecars are distinguished.

This preserves the complete **active application recovery dependency set**, not an exhaustive physical FTP export of unknown, unreferenced or obsolete hosting files. The full original project separately retains historical releases and rollback material. Capture provenance distinguishes original retrieval from the later verification resume.

[Production comparison](github-publication-phase1/PRODUCTION_BASELINE.json) · [Offline production verification](github-publication-phase1/PRODUCTION_OFFLINE_VERIFICATION.json) · [Dependency closure](github-publication-phase1/PRODUCTION_DEPENDENCY_CLOSURE.json) · [Capture provenance](github-publication-phase1/PRODUCTION_CAPTURE_PROVENANCE.json).

## Recovery scope and completion

File contents, paths, empty directories and file modified times are preserved and verified. Original metadata is recorded; hardlinks are materialized. This is not an OS image and does not reconstruct ACLs, alternate data streams, creation-time semantics or original hardlink topology. No reparse points were present. Stored Windows environments may require recreation after moving to another path/machine.

The original snapshot was taken before this phase's documentation changes. New reports, helper tools and the plan status are separately backed up in `phase1-documentation/` with a checksum inventory. The final completion receipt is also mirrored between the working project and external backup.

Production restoration must preserve old assets/sidecars, use the accepted current configuration, update dependencies and mutable pointers first, and publish index.html last. A real restoration must verify the actual submission link and browser controls afterward. Phase 1 did not perform a live rollback or fresh interactive-browser QA.

**Completion condition satisfied:** the original project and current active production version can be recovered independently of GitHub.

Git was not initialized, ignore rules were not changed, no code was uploaded, hosting was not changed and no scientific experiments were run. Phase 2 and all subsequent publication/CI/CD phases remain separate.