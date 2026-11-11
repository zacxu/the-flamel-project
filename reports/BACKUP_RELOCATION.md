# Backup relocation and current recovery paths

Current relocation state: **complete**.

The retained backup is now at **D:\Backups\TheFlamelProject**, outside the working project at D:\bears.
The current backup and working project share physical disk 0 (D:). This is a local
same-disk backup; the independent C: copy is removed after verified copying.

## Current locations

- Original full snapshot: D:\Backups\TheFlamelProject\phase1-20261111-0140-SGT\project-snapshot\bears
- Original inventory: D:\Backups\TheFlamelProject\phase1-20261111-0140-SGT\project-snapshot\inventory.jsonl
- Prepared release archives: D:\Backups\TheFlamelProject\phase2-20261111-0225-SGT\archives
- Production recovery tree: D:\Backups\TheFlamelProject\phase1-20261111-0140-SGT\production\htdocs
- Machine-readable current paths: [backup-paths.json](../publication/backup-paths.json)
- Current source-control seal: D:\Backups\TheFlamelProject\relocations\20261111-to-D\current-controls.json
- Relocation data verification: D:\Backups\TheFlamelProject\relocations\20261111-to-D\RELOCATION_DATA_VERIFIED.json
- Cleanup receipt: D:\Backups\TheFlamelProject\relocations\20261111-to-D\CLEANUP_COMPLETE.json

## What was preserved

The original snapshots, archive bytes, manifests, completion receipts, validation
receipts and frozen Phase 1/2 control seals are preserved byte-for-byte. Their
old C: paths are historical evidence. The prefix mapping in backup-paths.json
resolves those recorded locations; it does not rewrite historical receipts.

Active instructions, active path fields, the Git allowlist and current controls
were updated separately. The original bytes of changed files are retained under
D:\Backups\TheFlamelProject\relocations\20261111-to-D\backup-before. Use the current relocation seal for these active files;
the frozen Phase 2 seal describes its historical input/control cutoff.

## Redundant copies

The full Phase 1 restoration rehearsal at D:\bears-phase1-restore-20261111-0140-SGT is
verified and promoted into the retained original snapshot.
Its historical restoration receipt remains available.

- phase2_project_restore: removed_verified_redundant_copy
- phase2_production_restore: removed_verified_redundant_copy
- phase2_git_review_tree: removed_verified_redundant_copy

These trees are validation/review duplicates. Their verified receipts remain,
even after the redundant file trees are removed. No scientific evidence in the
working project or retained snapshot is deleted by this path-update tool.

## Current verification commands

~~~powershell
$paths = Get-Content 'D:\bears\publication\backup-paths.json' -Raw | ConvertFrom-Json
$python = Join-Path $paths.phase1_backup_root 'project-snapshot\bears\.runtime\python\cpython-3.11.14-windows-x86_64-none\python.exe'
& $python -I -B 'D:\bears\scripts\github_publication\project_snapshot.py' verify --snapshot $paths.original_snapshot --workers 8
& $python -I -B 'D:\bears\scripts\github_publication\artifact_io.py' verify --manifest 'D:\bears\publication\artifacts.json' --asset-dir $paths.archive_dir --scope all
& (Join-Path $paths.phase1_backup_root 'production\tools\verify-production.ps1') -Root (Join-Path $paths.phase1_backup_root 'production')
~~~

These are current commands, not a claim that this documentation updater reran
large-file hashing. The parent relocation receipt records actual copied-file
verification. No Git repository was initialized, no code was uploaded and live
hosting was not changed. Secret/licence and portable-installation work remains
in the planned later phases.
