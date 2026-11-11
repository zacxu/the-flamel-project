# Public research assets and exact UPF inputs

This is the Phase 4 retrieval path. The historical Phase 2 manifest remains the full **private recovery** record. Do not use that older full-scope manifest as a public upload list.

The new [public-assets.json](public-assets.json) selects **11 permitted original archives plus the required companion notice ZIP**. It excludes the three UPF-containing originals by name and identity. Project hydration includes the notice files; production hydration includes the same notices outside the captured htdocs tree.

All release URLs remain unpublished. Local verification and hydration are working now. A later release must attach the notice ZIP, record actual permitted download URLs and set the new public manifest's publication status deliberately. Current planned URLs are never fetched. The downloader refuses an unpublished manifest before making a request.

## Verify and hydrate the public subset

Run from a fresh source checkout using Python 3.11 or later. These commands require only Python's standard library and the retained sibling artifact_io.py, whose exact digest is checked. Restoration namespaces and member inventories are bound to the retained original artifact manifest and Phase 3 selection, including the exact notice-member list. No Codex runtime, existing Python research environment or scientific model execution is required.

For the retained local assets:

~~~powershell
$Assets = 'D:\Backups\TheFlamelProject\phase2-20261111-0225-SGT\archives'
$Notices = 'D:\Backups\TheFlamelProject\phase3-20261111-audit\release-sidecars'

python -I -B scripts/github_publication/public_assets.py verify --manifest publication/phase4/public-assets.json --asset-dir $Assets --notice-dir $Notices --scope all

python -I -B scripts/github_publication/public_assets.py hydrate --manifest publication/phase4/public-assets.json --asset-dir $Assets --notice-dir $Notices --scope project --destination 'D:\flamel-public-research-new'
~~~

The destination must be new. To fill an existing fresh checkout, pass that checkout as the destination and add --merge-existing. The entire operation preflights collisions; matching existing files may be reused and different bytes are never overwritten. Do not mutate the destination concurrently. Atomic commits require hardlink support such as the tested NTFS volumes.

For standalone production recovery use --scope production and a separate new destination. Then run its own tools/verify-production.ps1 against that destination. This is an offline restore check, not a deployment or fresh live-browser acceptance check.

The two asset directories may be the same when a later download folder contains all 12 files. The notice ZIP is mandatory for either hydration scope. The helper supports an optional --scratch-dir for its small temporary adapter manifest.

## Retrieve the exact upstream pseudopotentials

[upstream-upfs.json](upstream-upfs.json) pins the exact SSSP archive URL, size, SHA-256 and three used UPF identities. Download and place the canonical inputs in a new project target:

~~~powershell
python -I -B scripts/github_publication/public_assets.py upfs --manifest publication/phase4/upstream-upfs.json --cache-dir 'D:\flamel-download-cache' --destination 'D:\flamel-upf-inputs-new'
~~~

For an existing fresh source checkout use its directory as the destination and --merge-existing. The default creates only data/pseudopotentials/Ca_pbe_v1.uspp.F.UPF, Mg.pbe-n-kjpaw_psl.0.3.0.UPF and O.pbe-n-kjpaw_psl.0.1.UPF. Archive size/hash are checked before extraction and after reading; only the three selected files are written. No extractall, pickle loading or DFT runs occur.

There are **77 UPF-containing members** in the three private archives. Only **41** are byte-identical raw input placements reconstructible from the upstream files. The other **36** are QE-serialized .save scratch representations with different bytes and hashes. They are mapped explicitly in the manifest and stay private; they must never be filled with a byte-different raw UPF while claiming historical recovery.

Optional --restore-recorded-paths creates the 41 exact raw input placements. It does not restore the 36 serialized scratch UPFs, wavefunctions, restart files or other withheld history. Full historical private recovery continues to use the original verified backup/archives.

SSSP collection metadata has CC BY 4.0 terms with pseudopotential-family exceptions. Used Ca is GPLv3; Mg/O family is GPLv2-or-later. The [retained family licence](../third-party/SSSP-LICENSE.txt), source identity and authors remain authoritative. This tool retrieves upstream inputs for local use; it does not add raw UPFs to the public release selection.

## Later GitHub downloads

The download command is available only for a deliberately published public selector:

~~~powershell
python -I -B scripts/github_publication/public_assets.py download --manifest publication/phase4/public-assets.json --destination 'D:\flamel-release-downloads-new'
~~~

Today this command is expected to fail closed because nothing has been released. Once valid URLs are recorded, it permits only the intended GitHub repository's release paths without URL credentials/query tokens, bounds each response by the pinned length and commits only the expected SHA-256 bytes. Redirects must remain on the explicit HTTPS host allowlist. No embedded account credentials are supported. For a private GitHub repository, use normal authenticated GitHub CLI release download after the release exists, then run local verification; do not put tokens in URLs or files. Authenticated GitHub download and availability on another machine remain later release acceptance work.

The SSSP source currently redirects to its official CSCS storage host. The allowed host was observed from the public upstream response. Temporary signed redirect URLs and cookie/auth values are not saved in source or reports.

## Measured validation

See [ASSET_VALIDATION.json](ASSET_VALIDATION.json):

| Check | Recorded result |
| --- | --- |
| All permitted archive/member bytes | 12 archives, 907 members verified |
| Fresh project hydration | 777 files, 4,149,045,899 bytes; independent rehash passed |
| Fresh production hydration with notices | 140 files, 8,539,590 bytes; independent rehash passed |
| Restored production's own verifier | 123 captured files and 75 research payloads passed offline |
| Real upstream retrieval through the new tool | One fresh HTTPS fetch; archive SHA matched; three canonical UPFs passed |
| Optional exact raw input placement | 41 files passed; 36 serialized scratch members untouched |
| Final safety suite | 34 passed, zero failures/skips |
| Fresh-path tool portability | Copied tool and manifests verified without original checkout imports |

The test fixtures include byte preservation, exact notice/scope requirements, private archive rejection, corrupt/unlisted members, traversal/reparse guards, no-overwrite preflight, unpublished-network rejection, redirect/URL restrictions, bounded downloads, changed cached archives and safe tar extraction.

Historical manifests, archives, original environments and scientific evidence were not changed. No scientific computation, root Git initialization, remote upload or deployment was performed.
