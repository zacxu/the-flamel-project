# Phase 3 publication audit

The final completion record is [the Phase 3 report](../../reports/GITHUB_PUBLICATION_PHASE3.md). Historical Phase 2 manifests remain unchanged. This directory contains explicit current overrides rather than rewriting their provenance.

- baseline-inputs.json: exact 5,148 selected source records before Phase 3 changes.
- control-paths.json: all new/changed Phase 3 controls, explicit modified baseline paths and the private original removed from Git.
- disposition-overrides.json: the signed-redirect/cookie receipt remains private; its sanitized derivative is clearly labelled.
- secret-review-exceptions.json: only 13 exact immutable historical local-worker UUID findings, never broad rule/path suppression.
- upstream-ignore-exceptions.json and force pathspec: exactly eight original upstream files, with hashes.
- release-selection.json: 11 later-release candidates, three private-only archives. Full local recovery retains all 14.
- notice-bundle.json: exact verified companion ZIP required with all permitted archives.
- STAGING.md: exact allowlist, Windows long-path handling and byte-preservation policy.

Run the standard-library read-only verifier from the project root:

~~~powershell
python -I -B scripts/github_publication/verify_phase3.py
~~~

Default mode verifies original baseline files and explicitly reports current controls as unsealed. To verify every current selected byte, use the external selected-files.json and its independently recorded SHA-256 under D:/Backups/TheFlamelProject/phase3-20261111-audit:

~~~powershell
python -I -B scripts/github_publication/verify_phase3.py --seal 'D:/Backups/TheFlamelProject/phase3-20261111-audit/selected-files.json' --seal-sha256 <trusted-digest-from-external-PHASE3_COMPLETION.json>
~~~

The external complete seal avoids a file hashing itself. Current controls are also backed up separately; publication/backup-paths.json points to that control seal. Neither command stages, publishes or runs scientific work. New/changed files in Phase 4 invalidate the frozen candidate seal and require a new audited overlay before Phase 5.

For credential rechecks use scripts/github_publication/scan_secrets.py with an independently verified Gitleaks executable and an existing private scratch directory outside the project. It scans only the literal Git selection, optionally all 14 exact local archives, rejects unsafe paths/junctions and returns metadata without token values. A new finding or changed reviewed UUID file fails closed. Reports must be new private outputs outside source/archive scopes.

Fresh dependency installation, security remediation and public-subset asset hydration remain Phase 4. Git commits/pushes remain Phase 5. Release/hosting operations remain later phases.
