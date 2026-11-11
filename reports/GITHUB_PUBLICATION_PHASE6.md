# GitHub publication Phase 6

Status: COMPLETE — 11 November 2026. Source: [zacxu/the-flamel-project](https://github.com/zacxu/the-flamel-project), private. [CI guide](../CI.md).

Five separate workflow paths are implemented and have passed on fresh GitHub runners. Website and research checks run for relevant pull requests and main pushes. Evidence auditing, packaging and deployment preparation are manual/reusable workflows, tested together by the dedicated acceptance workflow. The original Phase 5 workflow is retained only as a manual check of its immutable historical commit.

## Hosted acceptance

Accepted source commit: 3f37d432f803b5aa5012f1beeb672f1b421d598c.

| Check | Actual hosted result |
| --- | --- |
| Website CI | [PASS](https://github.com/zacxu/the-flamel-project/actions/runs/42970059046): clean pinned tools, parser-only Python, TypeScript, W6 regressions, tour/download and installer guards |
| Research CI | [PASS](https://github.com/zacxu/the-flamel-project/actions/runs/42970059160): actual selection/budget/gate/catalog fixtures, control policy, package safety, integrity and saved-evidence checks |
| Evidence audit | [PASS](https://github.com/zacxu/the-flamel-project/actions/runs/42970051876): committed frozen provenance, without bulk downloads or scientific execution |
| Release packaging | [PASS](https://github.com/zacxu/the-flamel-project/actions/runs/42970051876): selected commit built, packaged, guarded in a new external stage, independently checked and uploaded as an Actions artifact |
| Deployment preparation | [PASS](https://github.com/zacxu/the-flamel-project/actions/runs/42970051876): separate Linux runner downloaded the package and verified its producing run, source SHA, ZIP members, checksums, entry, policy and upload plan |

The acceptance run is 42970051876. Its package artifact is flamel-package-3f37d432f803b5aa5012f1beeb672f1b421d598c; artifact ID 13833016867. Actions artifacts have 14-day retention and are not permanent GitHub Release assets. The final main commit, final CI runs, independent clone and full recovery-seal hashes are recorded externally in D:/Backups/TheFlamelProject/phase6-20261111-ci/PHASE6_COMPLETION.json. This avoids a commit claiming to contain its own hash.

The first hosted packaging attempt stopped before building because the Windows runner exposed multiple Python executables. Selecting the first actual application resolved the argument binding; the accepted run above completes packaging and the independent artifact handoff. The original accepted evidence remained unchanged throughout.

## Checks and source preservation

Local clean-install validation passed 27 actual-source research fixtures and nine control-policy tests. The website run passed all eleven W6 validators, 384 integration checks and 224,507 source regression assertions, 123 tour checks, 76,491 compact-URL checks, 330 orientation checks, eleven publication-guard scenarios, and 34 checks over seven retained download files. Windows installer guards passed nine tests. Manual package fixtures passed thirteen tests locally with two Windows symlink privilege skips; the Linux hosted job runs the full suite.

The local real package contains 88 payload files and passed the unchanged publication guard plus independent ZIP/stage verification. Local and hosted results are kept distinct; LOCAL_CHECKS.json identifies its measurements as local, and the hosted links above establish runner acceptance.

The complete Phase 5 seal passed before edits. This phase adds 30 files, bringing the exact Git selection to 5,308, and changes eleven existing operational documentation/metadata files. All other 5,267 Phase 5 file records match their original hashes. Scientific/application source, accepted research/browser evidence, historical dependency locks, vendor bytes and the public/private archive policy were preserved. Source validators operate in disposable exports; the original checkout is verified before and after their execution.

Existing active application/research/publication source is explicitly enumerated as mutable for future pull requests. That declaration is separate from actual edits in this phase. The verifier pins the original complete baseline and rejects metadata exemptions for frozen artifacts, datasets, configuration, contracts, historical reports, requirements and vendor files. It compares every selected Git blob to source; the independent external seal additionally authenticates all current control bytes.

New and modified selected controls were scanned before publication with zero credential findings. Unchanged baseline bytes retain the prior scoped audit. Pattern scanning is not a general guarantee that unknown secrets cannot exist.

## Workflow isolation

Routine jobs use read-only contents permission, immutable reviewed action revisions, nonpersistent checkout credentials, explicit timeouts and cancellation of outdated runs. Deployment preparation adds only read-only Actions access for earlier-run artifact validation. No hosting credentials or broad write token are configured.

Research fixtures need only the frozen NumPy wheel. Website parsing uses forty hash-pinned packages from the existing tested maintenance profile; torch, CHGNet and JAX are absent. The routines do not install the complete research model stack, download bulk research archives, generate crystals, relax structures, train models or launch QE/DFT. Existing Windows-only installer tests run on Windows rather than Linux.

The separate manual evidence audit supports explicitly requested scoped public asset and pinned upstream UPF retrieval. Public archive retrieval deliberately rejects unpublished availability before network access. The eleven permitted archives and companion notice ZIP remain unpublished until Phase 7; three private UPF-containing archives remain excluded.

## Packaging and hosting boundaries

The website is already deployed on InfinityFree. Phase 6 changes CI and prepares future update packages; it performs no hosting upload.

Fresh Git clones retain partial historical stage metadata while generated entry files are ignored. The new wrapper calls the existing verifyPublication and stagePublication APIs with a fresh external stage, preserving all historical staged files. Package validation checks exact file sets, paths, regular-file types, source/run binding, hashes, release identity, entry bytes and the accepted hosting policy. The recorded source_tree and producer_workflow_commit fields are producer assertions in this phase, rather than independent attestations.

The deployment-preparation job explicitly returns VERIFIED_PACKAGE_NOT_DEPLOYED. Actual GitHub Release publication, permitted-archive upload, predecessor reconstruction and fresh browser/release acceptance belong to Phase 7. The legacy full release validator needs the historical predecessor cache omitted from Git; it is not falsely reported as passed here. InfinityFree transport integration, index-last upload, live /refresh/submission-link acceptance and rollback belong to Phase 8.

Implementation details and exact local receipts are described in [website-design.md](github-publication-phase6/website-design.md), [research-design.md](github-publication-phase6/research-design.md) and [manual-design.md](github-publication-phase6/manual-design.md).
