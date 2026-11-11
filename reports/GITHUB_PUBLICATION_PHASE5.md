# GitHub publication Phase 5

Status: prepared for first publication. Repository: https://github.com/zacxu/the-flamel-project (private).

The completed Phase 4 seal was verified before changes: 5,260 selected files. This phase adds the initial CI workflow, exact Git index/tree byte verification, and a publication overlay. Historical scientific inputs, environments, locks, website source and archived assets remain unchanged.

## Publication procedure

1. Configure root Git with branch main, SHA-1 objects, core.autocrlf=false and core.longpaths=true. Use the existing authenticated Git identity and normal credential manager.
2. Stage the reviewed literal file selection, then only the eight hash-reviewed upstream ignore exceptions. Compare the complete index path set and every staged blob SHA-256 with the reviewed source/seal.
3. Run local integrity, evidence, archive and installer safety checks and inspect ignored files. Scan the exact candidate source; index/source equality transfers that scan to the staged bytes.
4. Commit and dry-run the push. Publish main only to the intended empty private repository without force.
5. Resolve the remote commit and independently clone it with Windows long-path handling. Verify every selected file against the external candidate seal and the committed Git tree.
6. Record the first successful import/clone and then publish a closeout documentation commit. Final commit/clone/seal hashes live in external PHASE5_COMPLETION.json, avoiding a commit containing its own hash.

Current per-step receipts are in reports/github-publication-phase5 and D:/Backups/TheFlamelProject/phase5-20261111-publication. A prepared record is not a claim that a push or remote CI run has succeeded.

## Initial CI

The initial workflow has read-only contents permission and immutable pins for official checkout and setup-python actions. It checks committed source bytes, the saved evidence and small safety fixtures on Ubuntu 24.04 with Python 3.11.14. Windows 2025 independently runs the existing hash-verified Node 24.22.1/npm 12.2.1 installer, builds the website and compares all 86 files with the frozen production-byte proof.

No scientific environment or research archive is downloaded by this workflow. Python installer tests exercise only rejection/checkpoint-metadata guards; they do not install or run models. The baseline suite exercises pure standard-library logic. Full Phase 6 workflow separation, evidence audit automation, release packaging and deployment remain later work.

The new Git checker compares exact paths, regular-file modes, text attributes and all Git blob bytes with source files. It rejects extra staged private files, missing paths, source edits after staging and unexpected newline conversion. Local fixture tests exercise these failures.

## Preserved boundaries

The repository remains private. Large frozen artifacts retain their declared local/release dispositions; three UPF-containing archives and private configuration stay out of Git. No release assets, tags or hosting files are published in this phase. GitHub source publication does not establish public anonymous access or new scientific findings.

The actual current source commit is obtainable with git rev-parse HEAD. The final external completion receipt binds the commit, remote ref, clone and complete selected-file manifest. Earlier Phase 1-4 records remain historical and unchanged.
