# Phase 1 offline recovery instructions

<!-- backup-relocation-current:start -->
> **Current backup:** D:\Backups\TheFlamelProject. See [current recovery and cleanup status](../BACKUP_RELOCATION.md).
> Historical receipts retain their original paths and hashes. Current cleanup: complete.
<!-- backup-relocation-current:end -->

Source snapshot: D:\bears, captured before adding Phase 1 reports or changing the publication plan.
Backup root: D:\Backups\TheFlamelProject\phase1-20261111-0140-SGT
Accepted snapshot: project-snapshot (only if verification.json says VERIFIED).
Use project-snapshot only. The rejected first attempt is historical and is not used for recovery.

## What is preserved

The complete original project tree is copied with no Git-ignore exclusions. Every file has a relative path, byte length, SHA-256, original metadata, backup location and provisional publication/storage category in project-snapshot/inventory.jsonl. Directory records include empty directories. Historical source, evidence, checkpoints, datasets, vendor content, installed environments, caches, production packages, configurations and failed outputs are retained.

The current backup and working project both reside on D: (physical disk 0). The original Phase 1 capture was verified on C: (physical disk 1); that historical fact remains in preserved receipts. This is now a same-disk local backup, not an off-machine or cloud backup.

File contents, relative paths, empty directories and file modified times are verified. Original hardlinks are materialized as independent files. Original metadata is inventoried; this is not an OS image and does not preserve ACLs, alternate data streams, creation-time semantics or hardlink topology. Reparse points are rejected rather than silently followed. No such points were present in the captured tree.

## Verify the project backup

Use an available Python 3.11+ interpreter. A standalone Windows Python is also preserved inside the backup:

~~~powershell
$backup = 'D:\Backups\TheFlamelProject\phase1-20261111-0140-SGT'
$python = Join-Path $backup 'project-snapshot\bears\.runtime\python\cpython-3.11.14-windows-x86_64-none\python.exe'
$tool = Join-Path $backup 'tools\project_snapshot_v1_1.py'
& $python -I -B $tool verify --snapshot (Join-Path $backup 'project-snapshot') --workers 8
if ($LASTEXITCODE -ne 0) { throw 'Backup verification failed' }
~~~

The verifier checks the inventory checksum, full path/directory sets, all file lengths, all file modified times and every file SHA-256. It does not fetch GitHub content or use the network.

Compare inventory.jsonl against inventory.sha256 and the independent digest recorded in the Phase 1 completion report. A mismatched manifest, missing file or corrupt file is a failure, not a warning.

## Restore to a new directory

The target must not already exist. Use an explicit fresh path outside the working project:

~~~powershell
$destination = 'D:\bears-restored'
$receipt = Join-Path $backup ('restore-verification-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
& $python -I -B $tool restore --snapshot (Join-Path $backup 'project-snapshot') --destination $destination --report $receipt --workers 8
if ($LASTEXITCODE -ne 0) { throw 'Restoration failed' }
~~~

This copies every file, recreates directories and independently rehashes all restored files. It refuses to overwrite an existing directory. If the original D:\bears has been lost and that path no longer exists, it may be used explicitly as the restoration target. Do not delete or overwrite an existing project to rehearse recovery.

The historical Phase 1 receipt records the full restoration rehearsal at D:\bears-phase1-restore-20261111-0140-SGT. That verified copy was promoted into the retained original snapshot at D:\Backups\TheFlamelProject\phase1-20261111-0140-SGT\project-snapshot\bears. The historical receipt is preserved.

Stored Windows environments preserve the original bytes; moving them to another path or machine does not prove they are executable there. Recreate environments using the later portable-installation phase where needed. Keep frozen historical evidence and locks unchanged.

## Verify the active production backup

~~~powershell
& (Join-Path $backup 'production\tools\verify-production.ps1') -Root (Join-Path $backup 'production')
~~~

production/htdocs contains all 88 currently served release files, 33 separately captured image backing sidecars and two accepted local hosting configurations. PRODUCTION_BASELINE.json, its checksum sidecar, CAPTURE_PROVENANCE.json and DEPENDENCY_CLOSURE.json record the evidence.

The 88 served files and 33 sidecars were retrieved from the live website and matched retained hashes. Root, /refresh and /index.html returned the current entry with no-store headers. The protected Apache configuration files were retained from accepted local records and their effective routing/caching behavior was checked live; their physical server bytes were not downloaded.

This is a verified recovery set for the active website, not an exhaustive physical FTP export of unknown, unreferenced or obsolete hosting files. The full project snapshot separately retains historical packages and rollback material.

## Recover production only when an actual recovery is intended

Follow production/README.md and the preserved website publication instructions. Preserve existing hosting files before recovery. Upload immutable dependencies first, then any changed mutable pointers, preserve image sidecars/child configuration, apply the accepted current root configuration, and upload index.html last. Keep /refresh serving the current entry with no-store headers.

Do not replace the accepted root policy with the obsolete image-only configuration. Do not clear the hosting document root. Verify the actual submission link, UI/research build identities, response headers and interactions after a real recovery.

Phase 1 does not perform a live rollback, publish new code or change hosting.

## Acceptance records

- project-snapshot/verification.json: full original-tree capture and independent backup verification.
- restoration-verification.json: full restoration and independent rehash.
- tool-validation/validation-results.json: ten isolated safety checks.
- production/PRODUCTION_BASELINE.json: live package and sidecar comparison.
- production/OFFLINE_RESTORE_VERIFICATION.json: standalone offline production verification.
- production/DEPENDENCY_CLOSURE.json: emitted assets, crystal fallback and backing-image closure.
- PHASE1_COMPLETION.json: final aggregate acceptance and checksums.
- phase1-documentation/: separate backup of the subsequently added Phase 1 reports, tools and plan status. These additions are not retroactively included in the original snapshot.

No completion claim is valid until the aggregate receipt and both project verification receipts report success.