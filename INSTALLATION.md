> Reproducible release: [Phase 7](reports/GITHUB_PUBLICATION_PHASE7.md) | [Release guide](RELEASE.md). Existing release availability is verified in the Phase 7 completion record; historical manifests below keep their original scope.

# Standalone installation and use

This guide is separate from the frozen research protocol. Use a fresh checkout or disposable source copy. Keep the original research evidence unchanged. Current Windows x64 setup uses Python 3.11.14, Node 24.22.1 and npm 12.2.1 without Codex, global Node/npm or an existing project environment.

Phase 4 validated a checksum-verified source export. Phase 5 has published and independently verified the source clone in the private repository. Clone with your normal GitHub authentication:

~~~powershell
git clone -c core.longpaths=true -c core.autocrlf=false https://github.com/zacxu/the-flamel-project.git
~~~

See [the source publication record](reports/GITHUB_PUBLICATION_PHASE5.md) for actual verification status. Release assets remain local/unpublished until their later release phase.

## GitHub CI

See [CI.md](CI.md) for fresh-run website/research checks, hash-pinned parser dependencies, manual evidence auditing and package preparation. The current source gate is scripts/github_publication/verify_phase7.py --require-clean; historical Phase 3-5 gates retain their original baseline scope. No model execution is part of routine CI.

## View and build the website

From the fresh project root:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/install_website.ps1 -ToolchainRoot 'D:\flamel-tools\website'
~~~

This downloads and verifies the pinned standalone tools, installs package-lock.json with npm ci and lifecycle scripts disabled, runs TypeScript checking and builds the retained site. It does not need research models or Python for an ordinary website build. Toolchains must be outside the project. The package manifest and lock remain unchanged.

Start the preview from that checkout:

~~~powershell
$env:FLAMEL_NODE = 'D:\flamel-tools\website\node-v24.22.1-win-x64\node.exe'
Push-Location -LiteralPath website
try {
    .\scripts\npm.ps1 run preview -- --host 127.0.0.1 --port 4173
} finally {
    Pop-Location
}
~~~

Open [the local preview](http://127.0.0.1:4173/) and stop the server with Ctrl+C. Use HTTP rather than opening dist/index.html as a file. The preview serves recorded study data; browser actions do not run a generator or DFT.

For the complete saved-source/website regression sequence, first install the maintenance Python profile below. Then run the website installer from a disposable checkout with its explicit Python override:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/install_website.ps1 -ToolchainRoot 'D:\flamel-tools\website' -PythonExe 'D:\flamel-python\envs\analysis-maintenance-cpu\Scripts\python.exe' -ValidateSavedEvidence
~~~

Existing validators write their dated reports in that disposable copy. This option does not recapture browser downloads, conduct a new browser interaction session or deploy. See [the detailed website instructions](publication/phase4/WEBSITE_INSTALLATION.md).

## Verify saved evidence without research dependencies

Python 3.11+ is sufficient for the standard-library audit. It needs no installed scientific packages, model files or bulk archives:

~~~powershell
python -I -B scripts/github_publication/audit_saved_evidence.py
~~~

After using the installer below, its standalone interpreter can replace a machine Python:

~~~powershell
& 'D:\flamel-python\runtime\python\python.exe' -I -B scripts/github_publication/audit_saved_evidence.py
~~~

The command verifies 103 original source inputs, 75 public payloads, the frozen budget/events, and the authenticity and completed status of the saved historical audit. It does not re-execute the 3,587 historical checks, recompute metrics or deserialize models. An optional --report must name a new file outside the project.

The historical phase6_finalize.py writes scientific closure records. Its retained review_command fields describe that original workflow. Use a disposable research reproduction copy with all required inputs if running it; the read-only command above is the default integrity check.

## Install Python environments

The installer needs Windows x64, PowerShell 5.1+, built-in tar and network access. Native scientific wheels also need the Microsoft Visual C++ x64 runtime. The tested machine already provided vcruntime140, vcruntime140_1 and msvcp140 (14.50.35719.0); the installer does not change this system prerequisite. Use [Microsoft's official instructions](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if it is missing. The installer bootstraps the verified uv/Python distributions itself.

Recommended maintenance profile for tooling and future compatibility work:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/install_python.ps1 -Destination 'D:\flamel-python' -Environment analysis-maintenance-cpu
~~~

Historical reproduction profiles remain separate:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/install_python.ps1 -Destination 'D:\flamel-historical-analysis' -Environment analysis-historical
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/install_python.ps1 -Destination 'D:\flamel-historical-generator' -Environment generator-historical
~~~

Every Destination must be new; repeated calls never modify existing environments. The three examples therefore use separate destinations. Alternatively use -Environment all once with a new destination to install all three together. Each environment lives in Destination/envs/<profile>/Scripts/python.exe. A separate -CacheDirectory can reuse verified downloads. Consult [the exact specifications](requirements/phase4/) and [the environment/security decision](publication/phase4/ENVIRONMENT_POLICY.md) before choosing a profile.

| Profile | Purpose | Relationship to frozen results |
| --- | --- | --- |
| analysis-historical | Exact 51 historical analysis pins, including torch 2.6.0+cu124 | Retains the original versions and known advisory findings |
| generator-historical | Exact 60 registry pins plus the unchanged, pinned CrystalFormer vendor source | Relative source installation removes the former C: path; native Windows JAX uses CPU |
| analysis-maintenance-cpu | Separate tested CPU analysis/tooling environment | Updated torch/filelock/sympy and required setuptools; does not replace or revalidate the original scientific results |

The hash-pinned specifications are new files under requirements/phase4; requirements/analysis-lock.txt and generator-lock.txt retain their original bytes. The installer separates the official CUDA/CPU torch wheel from the PyPI package index instead of using unsafe-best-match. Source or local builds needed by selected packages are explicitly recorded in the installation evidence.

The historical CUDA wheel is approximately 2.53 GB. Installing it does not by itself establish GPU execution, numerical equivalence, Linux portability or support for a different GPU/driver. The maintenance profile is deliberately CPU. Neither installation starts training, structure generation, relaxation or QE.

Virtual environments are recreated at their target location rather than moved between directories. [Python venv documentation](https://docs.python.org/3/library/venv.html) explains this constraint. The new locks use package hashes; see [pip's hash-checking documentation](https://pip.pypa.io/en/stable/topics/secure-installs/).

## Retrieve declared research artifacts

The reduced publication collection contains 11 permitted original archives plus the required notice ZIP. Three complete UPF-containing archives remain private. The historical 14-archive manifest is still available for full private recovery; it is not the public selector.

Currently all release archives are local and unpublished. For the owner's verified local archive set:

~~~powershell
$FlamelAssets = 'D:\Backups\TheFlamelProject\phase2-20261111-0225-SGT\archives'
$FlamelNotices = 'D:\Backups\TheFlamelProject\phase3-20261111-audit\release-sidecars'
python -I -B scripts/github_publication/public_assets.py verify --manifest publication/phase4/public-assets.json --asset-dir $FlamelAssets --notice-dir $FlamelNotices --scope all
python -I -B scripts/github_publication/public_assets.py hydrate --manifest publication/phase4/public-assets.json --asset-dir $FlamelAssets --notice-dir $FlamelNotices --scope project --destination 'D:\flamel-evidence'
~~~

The destination must be new. Explicit --merge-existing can add verified missing files to a disposable fresh checkout; matching existing files are reused and differing files are rejected. It never overwrites existing evidence. Production recovery uses --scope production and a separate new destination.

The future download subcommand rejects unpublished URLs before making a request. A later release must deliberately update/verify availability metadata and published URLs. No GitHub download is claimed yet. The source-export tests use declared local assets as their provider, independently of D:\bears and its installed environments.

Retrieve the three exact upstream pseudopotentials without redistributing the private archives:

~~~powershell
python -I -B scripts/github_publication/public_assets.py upfs --manifest publication/phase4/upstream-upfs.json --cache-dir 'D:\flamel-tools\sssp' --destination 'D:\flamel-upfs'
~~~

This downloads the exact pinned SSSP archive, verifies its SHA-256, inspects the archive safely and extracts only the three hash-matched canonical UPFs. Add --restore-recorded-paths to recreate the 41 exact recorded input placements in a new destination. The other 36 withheld UPFs were serialized by QE inside scratch directories; they have different bytes and are not reconstructed as canonical inputs. Scratch/restart history is still available only from the full private recovery set.

Ca uses GPLv3; the Mg/O family uses GPLv2-or-later. Preserve [the upstream notices](publication/third-party/README.md). The helper reports exact retrieval/licence scope, not a new claim of stable materials or complete private-history restoration. Detailed asset policy and commands are in publication/phase4.

## Run a new research study

Use the separate maintenance environment as a tested starting point. The compatibility smoke checks establish imports, dependency consistency and selected model loading; they do not reproduce the frozen discovery experiment or certify future scientific results.

Keep new inputs, outputs, configuration and budgets in a new study directory. The original ledgers, numerical freeze, queues and hard-stop rules remain part of the recorded hackathon study. Do not reuse the historical dispatch commands to change that evidence. A GPU generator or fresh QE campaign needs a separately validated backend and protocol; routine website checks only read the saved study.

## Current integrity and publication boundary

Use scripts/github_publication/verify_phase5.py to validate the baseline/declared overlay. Full current file verification additionally takes --seal and --seal-sha256 from the independently recorded current integrity receipt. Default mode explicitly reports new/changed controls as unsealed.

Root .gitattributes preserves exact bytes. Git for Windows must use core.longpaths=true and core.autocrlf=false before staging; eight original vendor files retain their exact reviewed ignore exceptions. [The GitHub publication plan](GITHUB_CICD_PUBLICATION_PLAN.md) covers staging, remote verification, CI, releases and guarded hosting.

Source publication and verified cloning are recorded in Phase 5. Release archives and production hosting remain separate later phases.
