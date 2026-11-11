Repository: **[zacxu/the-flamel-project](https://github.com/zacxu/the-flamel-project)** is private. Audited research and production website source is published on main. See [the publication report](reports/GITHUB_PUBLICATION_PHASE5.md) for initial commit, clone and CI verification.

<!-- backup-relocation-current:start -->
> **Current backup:** D:\Backups\TheFlamelProject. See [current recovery and cleanup status](reports/BACKUP_RELOCATION.md).
> Historical receipts retain their original paths and hashes. Current cleanup: complete.
<!-- backup-relocation-current:end -->

I inspected your project at `D:\bears`. The plan below covers the research code, production website, saved scientific evidence, and future CI/CD.

**Original inspection findings (before Phases 1-5)**

- The project folder initially had **no root Git repository**; Phase 5 initialized and published it.
- `artifacts/` contains approximately **5.08 GB**, including **3.32 GB of saved models**.
- The CrystalFormer checkpoint is approximately **166 MB**.
- The website has existing build, validation, packaging, and deployment safeguards.
- Several research and website manifests depend on **exact file bytes**. Changing line endings during import could invalidate them.
- The current ignore rules exclude vendor code, checkpoints, and some datasets. They need review before staging files.

GitHub blocks individual files larger than **100 MiB** in ordinary Git, so this requires an explicit artifact-storage plan. [GitHub file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

**1. Preserve the complete project and current production baseline**

Create a verified backup before initializing Git or changing ignore rules.

The inventory should record each file's relative path, size, SHA-256 checksum, and intended storage location. Include ignored files in this inventory.

Preserve:

- All research source, configuration, inputs, outputs, and failed experiments.
- Checkpoints and model lineage files.
- Website source and existing production packages.
- Hosting configuration, image sidecars, deployment records, and rollback files.

Compare the retained production package with the current hosting files before declaring it the production baseline.

**Completion condition:** the original project and production version can be recovered independently of GitHub.

**Phase 1 status: COMPLETE  -  11 November 2026.** [Completion report](reports/GITHUB_PUBLICATION_PHASE1.md) | [Offline recovery instructions](reports/github-publication-phase1/RECOVERY.md). Verified full-project backup and restoration; active production reconciled and preserved independently of GitHub.

**2. Decide what goes into Git and what becomes release assets**

My recommendation is to keep all source and production configuration in Git, with large frozen artifacts attached to versioned GitHub Releases.

| Project content | Recommended destination |
|---|---|
| `research_*.py`, `scripts/`, `config/`, dependency specifications | Git |
| Research reports, small inputs, CIFs, manifests, ledgers, and reference results | Git |
| `website/src/`, `public/`, contracts, scripts, dependency lockfile | Git |
| Deployment guard, current `.htaccess`, image adapter, required sidecars | Git |
| Required CrystalFormer source and third-party notices | Git, retaining upstream revision and licence |
| Large datasets, checkpoints, saved models, and bulk research outputs | Checksummed release archives |
| Built production website and deployment package | GitHub Release |
| Installed environments, `node_modules`, downloaded runtimes, caches | Recreate through documented installation |

Use Git LFS selectively if particular large files need to accompany normal development checkouts. Frozen multi-gigabyte evidence is better distributed as downloadable release archives.

The artifact manifest must provide retrieval and verification instructions. Nothing should disappear merely because `.gitignore` excludes it.

**Completion condition:** every project file has a documented disposition, and all required assets remain recoverable.

**Phase 2 status: COMPLETE  -  11 November 2026.** [Storage decisions](publication/README.md) | [Completion report](reports/GITHUB_PUBLICATION_PHASE2.md). Every frozen input has one destination; all prepared archives and restoration checks passed. Assets remain local and unpublished, pending Phase 3 review.

**3. Audit secrets, dependencies, and file integrity**

Before the first commit:

- Scan source, notebooks, logs, configuration, deployment records, and archives for credentials.
- Add appropriate exclusions for local secrets and provide configuration examples containing placeholders.
- Retain third-party licences, attribution, upstream revisions, and any local modifications.
- Review the current broad exclusions for `vendor/`, `checkpoints/`, `*.pkl`, and `*.zip`.

Configure `.gitattributes` **before staging** to preserve the bytes of frozen code and evidence. Avoid formatting or newline conversion during this migration.

There is also a portability issue: [generator-lock.txt](D:/bears/requirements/generator-lock.txt:10) references the former `C:` project location. Preserve that historical lock and add a separate portable installation specification.

**Completion condition:** the publication contains no credentials, preserves required attribution, and matches the original checksum inventory.

**Phase 3 status: COMPLETE — 11 November 2026.** [Completion report](reports/GITHUB_PUBLICATION_PHASE3.md) · [Current audit policy](publication/phase3/README.md). Exact selected source and all 14 local archives were scanned; the signed-header original and three UPF-containing archives are withheld. Original research/production bytes and historical locks remain unchanged. Known Python advisories are recorded for a separate Phase 4 security decision; this is not a security-clean environment claim.

**4. Make clean installation reproducible**

A fresh clone should work without depending on your existing environments or Codex installation.

Document and verify:

- A separate tested maintenance/security decision for the known torch/filelock advisories; preserve historical locks and keep research execution out of routine website CI.
- A scoped public retrieval/hydration workflow for the 11 permitted archives plus the notice bundle and exact upstream UPFs. The existing full private-recovery manifest requires all 14 original archives.
- The pinned Python environments.
- The website's declared Node and npm versions.
- Installation using `package-lock.json`.
- Retrieval and checksum verification of external research assets.
- Separate instructions for viewing the website, auditing saved research, and running new experiments.

The website already supports `FLAMEL_PYTHON` and `FLAMEL_NODE` overrides. CI should use those instead of workstation-specific executable paths.

Retain the existing directory structure during import. Moving research files can break relative paths and recorded provenance.

**Completion condition:** installation succeeds in a fresh location without relying on the original checkout.

**Phase 4 status: COMPLETE - 11 November 2026.** [Completion report](reports/GITHUB_PUBLICATION_PHASE4.md) and [installation guide](INSTALLATION.md). Exported standalone installers passed all three Python profiles, clean npm installation/build and saved-evidence checks. The 86 website application/public files match production bytes. Scoped asset hydration and real upstream UPF retrieval passed. Historical environments/locks remain unchanged; actual GitHub clone and release-download acceptance stay in later phases.

**5. Initialize Git and publish the audited baseline**

After the preceding checks, initialize Git in `D:\bears`:

```powershell
Set-Location -LiteralPath 'D:\bears'

git init -b main
git config core.autocrlf false
git config core.longpaths true
git remote add origin https://github.com/zacxu/the-flamel-project.git
```

Stage files using the reviewed inventory and the exact eight hash-checked upstream ignore exceptions in publication/phase3/STAGING.md. Inspect both staged files and ignored files before committing. Preserve the root .gitattributes policy; do not normalize frozen bytes.

The first publication should contain the audited source, documentation, artifact manifest, and initial CI workflows. Run local checks, inspect the commit, perform a push dry run, and then push `main`.

Because the remote is empty, this initial commit establishes the baseline. Subsequent changes should use branches and pull requests.

**Completion condition:** GitHub's commit SHA matches the local commit, and a fresh clone preserves the expected file hashes.

**Phase 5 status: COMPLETE - 11 November 2026.** [Publication report](reports/GITHUB_PUBLICATION_PHASE5.md). The initial commit was pushed to the private repository and independently cloned with all 5,278 source files verified. Initial CI includes source/evidence checks and the byte-identical website build. The final closeout head and CI results are bound in the external completion receipt. Release assets and hosting remain unchanged.

**6. Add CI appropriate to this project**

Use separate workflows so routine website changes do not download gigabytes of research evidence or launch scientific calculations.

| Workflow | Trigger | Purpose |
|---|---|---|
| Website CI | Pull requests and pushes | Type checking, relevant validators, production build |
| Research CI | Pull requests affecting research code | Small deterministic checks for selection, budgets, gates, and parsing |
| Evidence audit | Manual run | Retrieve frozen artifacts and verify historical provenance |
| Release packaging | Selected commit/tag | Produce and verify downloadable production/research packages |
| Production deployment preparation | Manual initially | Verify/stage an exact package in Phase 6; connect hosting upload in Phase 8 |

Reuse the actual website commands in [package.json](D:/bears/website/package.json:8), including `typecheck`, W6 integration validators, tour checks, and the publication-guard tests.

Several existing research audit scripts write into historical output locations. They should run in disposable audit copies. Add focused temporary-directory tests where necessary rather than treating those scripts as ordinary repeatable unit tests.

Keep full model generation, CHGNet relaxation, and DFT outside routine CI.

Use minimal workflow permissions, reviewed action versions, and isolated deployment credentials. [GitHub Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use).

**Completion condition:** a fresh GitHub runner validates the code without changing accepted evidence or launching costly experiments.

**Phase 6 status: COMPLETE - 11 November 2026.** [CI guide](CI.md) | [Completion report](reports/GITHUB_PUBLICATION_PHASE6.md). All five workflow paths passed fresh GitHub-runner acceptance, including separate-run package download and byte verification. Accepted evidence stays unchanged. The website is already deployed on InfinityFree; this phase adds CI and package preparation, with hosting transport integration in Phase 8.

**7. Create a reproducible release**

For a selected, passing commit:

1. Run the release validation sequence in a disposable checkout.
2. Build the website and generate its package.
3. Run package verification and the publication guard against that exact package record.
4. Record the source commit, UI build identity, package checksum, and artifact inventory.
5. Attach the production package and only the archives permitted by publication/phase3/release-selection.json, together with the verified third-party notice bundle. Keep the three UPF-containing archives private; reconstruct their exact inputs through pinned upstream retrieval.
6. Test retrieval from a separate fresh clone.

Build once for each release and deploy those exact verified bytes.

Existing download checks validate retained browser files; they do **not** establish fresh browser behaviour. Changed interactions require a new browser check before release.

**Completion condition:** another machine can retrieve, verify, and build the release using only the repository and declared assets.

**Phase 7 status: COMPLETE - 11 November 2026.** [Release guide](RELEASE.md) | [Completion report](reports/GITHUB_PUBLICATION_PHASE7.md). Private v0.1.0 is published with seventeen verified assets. Fresh authenticated retrieval, research/production recovery, exact upstream inputs and an independent byte-identical website rebuild passed. Existing hosting is unchanged.

**8. Connect deployment to InfinityFree**

Start with automated build, validation, and deployment-package preparation. Then automate upload once the account's supported transport has been verified. InfinityFree permits GitHub Actions uploads. [InfinityFree guidance](https://forum.infinityfree.com/t/using-github-actions-for-automatic-upload-to-infinityfree/111008).

The upload process must follow your existing [publication instructions](D:/bears/website/AGENTS.md:3):

1. Run the publication guard with the new package and `--stage`.
2. Upload new immutable assets and release metadata.
3. Update changed mutable pointers.
4. Preserve older assets, image sidecars, and child configuration.
5. Apply the accepted hosting configuration.
6. Publish `/htdocs/index.html` **last**.

Do not use a deployment tool that clears or blindly synchronizes the entire document root.

After deployment, verify the actual submission link, current build identity, `/refresh` response headers, crystal viewer, and downloads. Keep the preceding verified package available for rollback.

Private-repository branch protection and deployment approval features depend on the GitHub plan; check availability before relying on them. [Branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

**Completion condition:** production serves the intended release, the permanent submission link works, and rollback is documented and tested.

Phases 1-7 preserve the original baseline, audit its scope, verify standalone installation, publish source, validate CI and publish an independently retrieved/rebuilt release. Subsequent changes should use branches and pull requests.

**Current implementation status:** Phases 1-7 are complete. Private v0.1.0 and all seventeen assets are published and independently verified/rebuilt. Next: Phase 8, automate verified updates to the existing InfinityFree website and complete live acceptance/rollback. The live site remains unchanged by Phase 7.
