# Reproduce The Flamel Project v0.1.0

The repository and release are private. Use normal GitHub authentication with repository access. This release packages the production website and frozen research evidence; publishing it does not update the live InfinityFree website.

## Get source and declared assets

Install Git, Python 3.11 or later and the official GitHub CLI. If needed, authenticate with gh auth login; never put a credential in a URL, source file or downloaded manifest. Release publication was tested with the official Windows x64 GitHub CLI 2.103.3.

Use new directories. From PowerShell:

~~~powershell
git clone -c core.longpaths=true -c core.autocrlf=false https://github.com/zacxu/the-flamel-project.git D:\FlamelRelease\source
Set-Location -LiteralPath 'D:\FlamelRelease\source'
git switch --detach v0.1.0
$releaseCommit = (git rev-parse HEAD).Trim()
$ghExe = (Get-Command gh -CommandType Application | Select-Object -First 1).Source
python -I -B scripts/github_publication/phase7/release_transport.py --gh $ghExe bootstrap --tag v0.1.0 --source-commit $releaseCommit --destination 'D:\FlamelRelease\assets' --receipt 'D:\FlamelRelease\retrieval.json'
~~~

Bootstrap needs only this checkout and normal authenticated GitHub access. It resolves the actual tag commit, checks the exact seventeen remote assets, fetches the canonical record and checksum file, validates their relationships, then verifies every downloaded byte against the declared SHA-256. Downloads are literal names; unexpected files, the three private UPF archives, wrong source commits and changed payloads are rejected.

The seventeen assets are twelve original research/notice archives, the production bundle, exact predecessor support, release-validation evidence, the canonical release record and SHA256SUMS. [release-layout.json](publication/phase7/release-layout.json) declares their roles. The record lists fifteen payloads; SHA256SUMS lists those payloads and the record, avoiding self-reference.

The eleven permitted original archives and companion notice ZIP remain byte-identical to their audited source. Details and scope are in [ASSETS.md](publication/phase7/ASSETS.md). The canonical record and stable download URLs are declared by the [v0.1.0 release](https://github.com/zacxu/the-flamel-project/releases/tag/v0.1.0).

## Verify and recover research

The existing standard-library tools verify selected archives even when the directory also contains production assets:

~~~powershell
python -I -B scripts/github_publication/public_assets.py verify --manifest publication/phase7/public-assets.json --asset-dir 'D:\FlamelRelease\assets' --notice-dir 'D:\FlamelRelease\assets' --scope all
python -I -B scripts/github_publication/public_assets.py hydrate --manifest publication/phase7/public-assets.json --asset-dir 'D:\FlamelRelease\assets' --notice-dir 'D:\FlamelRelease\assets' --scope project --destination 'D:\FlamelRelease\source' --merge-existing
python -I -B scripts/github_publication/public_assets.py upfs --manifest publication/phase4/upstream-upfs.json --cache-dir 'D:\FlamelRelease\upstream-cache' --destination 'D:\FlamelRelease\source' --merge-existing --restore-recorded-paths --report 'D:\FlamelRelease\upfs.json'
python -I -B scripts/github_publication/audit_saved_evidence.py
~~~

Hydration restores the selected research evidence and required notices without deserializing models or running experiments. To add those files to a separate fresh research checkout, use that checkout as --destination and add --merge-existing; matching files are reused and different bytes are rejected. The measured mapping adds 767 ignored project files and 41 ignored raw-UPF placements while reusing ten identical tracked notices, preserving a clean Git checkout. Hydrate before building: the recovered historical dist is ignored and the new validation build replaces it; hydration after building can correctly reject different derived bytes.

Exact upstream reconstruction restores three canonical raw UPFs and forty-one recorded input placements. Thirty-six byte-different QE-serialized scratch UPFs and other withheld restart history remain private. This is scoped reproducibility, not a claim to recover the withheld private scratch state. All required family licences and upstream identities remain in the source and notice bundle.

## Independently build and validate

Use the clean source checkout before running validators that rewrite reports. Existing scripts write only inside this disposable checkout; accepted originals remain in Git.

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/phase7/prepare_release.ps1 -CandidateRoot 'D:\FlamelRelease\source' -SourceCommit $releaseCommit -PredecessorArchive 'D:\FlamelRelease\assets\flamel-predecessor-v0.1.0.zip' -ToolchainRoot 'D:\FlamelRelease\validation-tools' -OutputDirectory 'D:\FlamelRelease\validation-package'
~~~

This bootstraps pinned standalone Python, forty parser dependencies, Node 24.22.1 and npm 12.2.1, restores the eighty-four exact predecessor files, performs one build, runs all W6 regressions/tour/download checks, packages the result, runs the unchanged full release validator, stages through the publication guard and independently verifies the package. It does not install the model stack, load checkpoints, train, generate structures, relax crystals or run DFT. Windows x64 and its normal Microsoft VC runtime are the tested standalone build target.

Compare the validation build's payload inventory, UI identity and file checksums with the canonical production package. The independent rebuild is a verification result; the original published production package remains the deployment input. Repacking or rebuilding must not silently replace those shipping bytes.

For a fresh browser smoke, run the retained browser_smoke.mjs helper with the pinned Node executable: --website-root=<validated source/website> --browser=<Chrome executable> --output=<new external folder>. It uses an isolated headless Chrome profile and loopback server. Browser checks have their measured scope and do not establish a live InfinityFree deployment.

## Production bundle

flamel-website-v0.1.0.zip is a seven-file handoff bundle containing payload.zip, package-record.json, upload-plan.json, host/.htaccess, entry-last/index.html, provenance.json and SHA256SUMS. Extract only into a new external folder after validating the outer archive; use the existing Phase 6 manual_ci.py verify-package gate with the exact source commit and package directory to verify its payload and staged host policy.

The compatibility provenance.json inside this seven-file bundle retains the Phase 6 schema. For a local build its run fields say local; the fixed workflow-name field is not evidence of a GitHub Actions build. The canonical release record and attached Phase 7 release-preparation.json identify the actual local disposable build, exact source/tree and single successful build.

The separate predecessor support ZIP contains only the files pinned by website/reports/W6_BASELINE.json. It enables the complete historical compatibility validator from a fresh clone rather than depending on the original workstation cache.

Release-validation evidence includes the full gate results and source/build identities. [The Phase 7 report](reports/GITHUB_PUBLICATION_PHASE7.md) records actual publication and fresh retrieval acceptance; in-progress records must not be treated as completed releases.

## Update and rollback

Use a new release tag for future versions. Do not move v0.1.0, overwrite its assets or regenerate its production archive. Preserve historical source, evidence and third-party notices. GitHub Release publication and immutable hosting upload are separate actions: Phase 8 integrates InfinityFree transport, uploads immutable dependencies first, preserves sidecars and older assets, applies the accepted host configuration, publishes index.html last, and checks /refresh plus the saved submission link.
