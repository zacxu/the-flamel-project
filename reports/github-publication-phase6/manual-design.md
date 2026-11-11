# Manual CI workflows

These workflows support workflow_dispatch and workflow_call. Routine website/research checks do not call their optional network or packaging work. A dedicated Phase 6 acceptance caller exercises saved-evidence verification, real packaging and same-run artifact preparation once.

## Evidence audit

The default job authenticates the retained 103 scientific source inputs, 75 public payloads, numerical freeze and completed saved audit. It does not re-execute the 3,587 historical checks, deserialize models or launch experiments. Receipts are retained as a small Actions artifact; accepted source is verified before and after.

The explicit retrieve_public_archives option invokes the unchanged public_assets.py downloader and then its full exact-member verifier. The existing selector permits only eleven original archives plus the notice ZIP, excluding the three private UPF-containing archives. The current selector is unpublished, so selecting this option correctly fails before network requests. Phase 7 must deliberately publish/update availability metadata before a public archive download can succeed. Planned URLs never count as available assets.

The separate retrieve_upstream_upfs option retrieves the pinned SSSP source and verifies/extracts the three exact canonical UPFs into 41 recorded input placements outside the checkout. It does not reconstruct 36 serialized scratch/restart copies. This opt-in retrieval is outside routine CI.

## Release packaging

A selected full lowercase 40-character commit SHA must be present on main. The one-off acceptance caller may select only its exact ci/phase6 push SHA. Checkout and workflow-controller credentials are not persisted.

A disposable candidate checkout installs the existing pinned Node 24.22.1/npm 12.2.1 toolchain with lifecycle scripts disabled, type-checks, builds and runs the existing package-release.mjs. The existing verifyPublication and stagePublication APIs are then invoked with an explicit --stage in a new external staging directory.

A fresh clone contains historical staged .htaccess/upload-plan records but omits ignored staged entry bytes. Reusing that partial stage correctly fails. The external staging wrapper preserves those historical files and uses the same unchanged guard to generate a complete new stage; it never removes, overwrites or bypasses a guard check.

The independent standard-library checker verifies the source commit/tree, archive SHA/size, exact regular ZIP member inventory, per-member SHA/size, public path/file bounds, release-manifest identity and inventory, staged current entry, accepted .htaccess digest, upload-plan inventory, bundle checksums and producing run. Source-file hashes before/after packaging allow changes only to the generated UI module and package report inside the disposable candidate. The workflow/controller checkout stays clean.

The downloadable Actions artifact is flamel-package-<source_commit>. It contains payload.zip, package-record.json, upload-plan.json, host/.htaccess, entry-last/index.html, provenance.json and SHA256SUMS. It records VERIFIED_PACKAGE_NOT_DEPLOYED. No GitHub Release is created. Artifacts expire after 14 days; they are CI test outputs, not permanent release storage.

The old w6:release validator unconditionally needs .cache/w6-previous-dist, an excluded historical cache. Phase 6 does not claim that full legacy predecessor-cache check passed on a fresh runner. Phase 7 must reconstruct the required predecessor inputs, complete release/browser acceptance and publish permanent release assets. The new Phase 6 package gate verifies exact current bytes and the existing publication guard without inventing missing history.

## Production deployment preparation

A reusable same-run call downloads the exact package uploaded by its successful packaging dependency and binds provenance to the current Actions run ID. Manual cross-run use additionally verifies the producing run through the read-only GitHub Actions API: same repository, release-packaging.yml, main, manual dispatch, completed and successful. The selected artifact must match the source SHA and producing run.

It independently verifies the complete bundle, ZIP, manifest, staged entry, .htaccess and immutable-first/index-last upload plan, then uploads a verification receipt. The result explicitly remains VERIFIED_PACKAGE_NOT_DEPLOYED. There are no hosting credentials, FTP actions, document-root deletion or network writes. Phase 8 connects verified transport and performs live /refresh, response-header and browser acceptance against the already hosted website.

## Pins and permissions

Existing immutable official checkout/setup-python pins are reused. The official v4 action refs were resolved through GitHub's primary Git Data API on 11 November 2026:

- actions/upload-artifact: ea165f8d65b6e75b540449e92b4886f43607fa02; https://api.github.com/repos/actions/upload-artifact/git/ref/tags/v4
- actions/download-artifact: d3f86a106a0bac45b974a628896c90dbdf5c8093; https://api.github.com/repos/actions/download-artifact/git/ref/tags/v4

All jobs have contents:read; cross-run deployment preparation additionally uses actions:read. The short-lived GitHub token is exposed only to the read-only API/download step. No hosting credentials are configured or requested.

## Local verification

Fifteen adversarial fixtures cover valid packages, immutable commit/run binding, corruption, missing/extra files, resealed stale entries and host policies, path traversal/Windows hazards, case collisions, duplicate JSON, link/output-parent protection and producing-run policy. On Windows, thirteen pass and two symlink cases skip because unprivileged creation is unavailable; Linux CI runs those cases.

The default manual evidence mode passed locally with 103 source inputs, 75 payloads, no model deserialization and no experiments. Private logs and actual package-build receipts are in D:/Backups/TheFlamelProject/phase6-20261111-ci/manual-tests. The root Phase 6 completion receipt records the final hosted workflow results.
