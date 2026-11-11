> Reproducible release: [Phase 7](../reports/GITHUB_PUBLICATION_PHASE7.md) | [Release guide](../RELEASE.md). Existing release availability is verified in the Phase 7 completion record; historical manifests below keep their original scope.

> Current source/CI verification: [Phase 6 CI guide](../CI.md). Use scripts/github_publication/verify_phase7.py for the current selected checkout. The older verification and archive commands below retain their declared historical scope.

# Retrieve, verify and restore publication assets

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

## Full private local recovery

The prepared archives currently exist only in:
D:\Backups\TheFlamelProject\phase2-20261111-0225-SGT\archives

The following full-scope commands require all 14 private/local archives. They are recovery commands, not instructions to publish all archives. Run them from D:\bears using Python 3.11+:

~~~powershell
$assets = 'D:\Backups\TheFlamelProject\phase2-20261111-0225-SGT\archives'
python -I -B scripts/github_publication/artifact_io.py verify --manifest publication/artifacts.json --asset-dir $assets --scope all
~~~

This verifies archive digests, exact regular-file member sets, member sizes and SHA-256 values, safe paths and namespace uniqueness. It performs no network requests and never deserializes scientific pickle/model contents.

Restore research files into a NEW directory:

~~~powershell
python -I -B scripts/github_publication/artifact_io.py hydrate --manifest publication/artifacts.json --asset-dir $assets --scope project --destination 'D:\flamel-research-assets-restored'
~~~

To add missing artifacts to a separate, freshly cloned repository, use explicit merge mode:

~~~powershell
python -I -B scripts/github_publication/artifact_io.py hydrate --manifest publication/artifacts.json --asset-dir $assets --scope project --destination 'D:\flamel-fresh-clone' --merge-existing
~~~

Merge mode preflights collisions before writing. Existing files are accepted only when their bytes match; differing files are never overwritten. Reparse parents, links, traversal, unsafe/colliding names and unexpected members are rejected. Incomplete runs do not produce success receipts; verified matching files can be reused on a later explicit merge. Do not mutate the destination concurrently. Atomic file commits require hardlink support, as provided by the tested NTFS volumes.

Restore the production recovery set separately:

~~~powershell
python -I -B scripts/github_publication/artifact_io.py hydrate --manifest publication/artifacts.json --asset-dir $assets --scope production --destination 'D:\flamel-production-assets-restored'
& 'D:\flamel-production-assets-restored\tools\verify-production.ps1' -Root 'D:\flamel-production-assets-restored'
~~~

This produces htdocs plus recovery metadata. It does not deploy anything. Follow its README and the website publication guard for a real restoration; preserve current root/child policies and sidecars and publish index.html last.

## Future GitHub retrieval

No assets or release tag have been published. artifacts.json retains the historical 14-archive private preparation manifest. Only the 11 candidates in phase3/release-selection.json plus the companion notice ZIP may proceed to later release preparation. Three UPF-containing originals remain private. When a release exists, download only its permitted assets with normal GitHub authentication. For example:

~~~powershell
gh release download <published-tag> --repo zacxu/the-flamel-project --pattern 'flamel-*.zip' --dir <asset-directory>
~~~

Verify each permitted downloaded archive against its exact size/SHA in phase3/release-selection.json and notice-bundle.json. The older artifact_io full-scope commands above expect all 14 archives and therefore cannot hydrate the reduced public collection by themselves. Phase 4 supplies and tests public_assets.py with the explicitly scoped public-assets.json selector and upstream-upfs.json retrieval record; use the linked current instructions for the three exact used UPFs. Do not fill gaps by silently uploading private archives. Upstream reconstruction does not reproduce withheld scratch/restart history; full private historical recovery remains available locally. This gh example is a future instruction, not a command tested during Phase 2. The current verifier deliberately accepts the local-preparation schema and never fetches planned URLs. Changing publication metadata requires a deliberate later policy/schema update and corresponding checks; unchanged archives can still be verified against this historical manifest.

## Recreated or pinned upstream content

pinned-upstreams.json records exact URLs, lengths and SHA-256 values for the QE distribution, SSSP archive and CrystalFormer source archive. Validate downloads before extraction; retain all component notices. Required CrystalFormer source is also in Git. The checkpoint candidate has an explicit Apache 2.0 declaration at its pinned model revision and requires the companion notices. Exact UPF bytes remain in the three private archives and the Phase 1 snapshot; public reconstruction uses the pinned SSSP source and correct family licences. See the Phase 3 notices and release selection.

These are frozen provenance records, not claims that new upstream downloads or portable installations were tested. Existing setup scripts can rewrite historical manifest locations; do not run them against frozen evidence to retrieve optional dependencies. Use a fresh installation target and the later Phase 4 instructions.

Installed Python environments, node_modules, runtimes, caches and generated vendor build/egg-info copies are recreate-only publication content. Their exact originals remain recoverable from the Phase 1 backup. The local .env is private-backup-only and must not be added to Git or release archives.

## Safety fixtures

~~~powershell
python -I -B scripts/github_publication/test_artifact_io.py --output-root 'D:\Backups\TheFlamelProject\flamel-artifact-safety-new'
~~~

The test output root must be new. The suite uses 24 isolated cases covering valid restoration, corruption, traversal, collisions, links/junctions, overwrite rejection, merge preflight and local-only availability. It does not need the large research archives, GitHub access or the original source environment.