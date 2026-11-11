> v0.1.0 is published privately. All seventeen release assets were downloaded and verified, research/production recovery passed, and independent local/GitHub-runner builds matched the published payload. See [the completed release report](../../reports/GITHUB_PUBLICATION_PHASE7.md). Historical preparation notes below retain their original scope.

# Versioned research assets

The Phase 7 selector is [public-assets.json](public-assets.json). It describes the eleven original archives permitted by the Phase 3 audit plus the mandatory third-party notice ZIP for tag v0.1.0. Its member inventories and archive hashes remain identical to the historical Phase 4 selector; the earlier manifests and original archives are unchanged.

The source repository remains private. "Public assets" names the audited redistribution subset, not anonymous access to this private release. The selector is prepared in the release candidate; actual publication and availability are established by the release and independently verified download receipts in the phase completion record.

The twelve files total 4,157,779,365 compressed bytes. Their 907 verified members contain 4,157,516,044 bytes. Every file is below 1 GiB; the largest is 791,135,064 bytes. The three private UPF-containing originals are excluded, and the companion notice ZIP is mandatory.

## Retrieve from another source checkout

Use a new Windows x64 source checkout and normal GitHub authentication. Install GitHub CLI through its official supported distribution if necessary, and use gh auth login for your own account when authentication is not already configured. Never paste credentials into a URL, manifest or script.

~~~powershell
git clone -c core.longpaths=true -c core.autocrlf=false --branch v0.1.0 https://github.com/zacxu/the-flamel-project.git 'D:\flamel-source-v0.1.0'

$Source = 'D:\flamel-source-v0.1.0'
$Assets = 'D:\flamel-assets-v0.1.0'
$SourceCommit = (git -C $Source rev-parse HEAD).Trim()

python -I -B "$Source\scripts\github_publication\phase7\research_assets.py" download --manifest "$Source\publication\phase7\public-assets.json" --destination $Assets --gh-exe gh --source-commit $SourceCommit --report 'D:\flamel-asset-download-v0.1.0.json'
~~~

The helper asks GitHub CLI for the published release metadata and resolves the actual Git tag to its commit. It rejects a draft release, changed source tag, unexpected repository/URL, absent notice ZIP, private archive names, raw UPFs, incomplete uploads, duplicate names and wrong sizes or server digests. GitHub CLI downloads only the twelve literal expected filenames. The helper then checks every downloaded SHA-256 and all 907 ZIP members using the existing audited verifier. It never deserializes model contents.

An existing asset directory may be reused only when it contains expected regular files with exactly the pinned bytes. Invalid or extra files are rejected rather than overwritten. Reports must be new files outside the checkout. The helper uses GitHub CLI's normal credential provider or caller-provided ephemeral environment; it does not read, print or save a credential.

For local/offline verification after a normal authenticated gh release download:

~~~powershell
python -I -B "$Source\scripts\github_publication\public_assets.py" verify --manifest "$Source\publication\phase7\public-assets.json" --asset-dir $Assets --notice-dir $Assets --scope all --report 'D:\flamel-asset-verification-v0.1.0.json'
~~~

The older anonymous download command cannot authenticate to this private repository. Do not treat an HTTP 404 while signed out as evidence that the authenticated release is missing.

## Restore the permitted project evidence

Restore into the fresh checkout without changing existing matching source bytes:

~~~powershell
python -I -B "$Source\scripts\github_publication\public_assets.py" hydrate --manifest "$Source\publication\phase7\public-assets.json" --asset-dir $Assets --notice-dir $Assets --scope project --destination $Source --merge-existing --report 'D:\flamel-project-hydration-v0.1.0.json'
~~~

The project scope restores 777 permitted files, including the required notices. It is a scoped research recovery operation, not a claim that the withheld private scratch history is available. Existing different bytes, traversal, links/reparse paths and unlisted members are rejected before writes. Use a new target without --merge-existing if restoring the asset subset by itself.

Retrieve the exact raw pseudopotentials directly from the pinned upstream source:

~~~powershell
python -I -B "$Source\scripts\github_publication\public_assets.py" upfs --manifest "$Source\publication\phase4\upstream-upfs.json" --cache-dir 'D:\flamel-upstream-cache-v0.1.0' --destination $Source --merge-existing --restore-recorded-paths --report 'D:\flamel-upstream-inputs-v0.1.0.json'
~~~

This verifies the upstream collection and three exact UPFs, then restores their 41 original raw input placements. It does not substitute raw UPFs into the 36 byte-different serialized QE scratch representations. The three original private archives remain private. Full private recovery still uses the original verified backups.

Use [INSTALLATION.md](../../INSTALLATION.md) for the separately pinned website/parser or scientific environment. Merely installing or restoring bytes does not run generation, relaxation, training or DFT.

## Historical production recovery

The active-production archive is a preserved historical hosting recovery set. A separate --scope production hydration recreates that namespace with the mandatory notices outside htdocs and supports its retained offline verifier. It is distinct from the new selected-commit website package attached to this release. Offline restoration does not update InfinityFree or establish fresh live-browser acceptance.

The Phase 7 website package and release inventory carry their own source/UI identity and package hashes. Phase 8 deploys those exact verified bytes using the accepted immutable-first, entry-last publication order.
