> Phase 7 complete: [private v0.1.0](https://github.com/zacxu/the-flamel-project/releases/tag/v0.1.0) passed full validation, actual retrieval/recovery and an independent byte-identical rebuild. See [the release guide](RELEASE.md).

> Current release work: [Phase 7](reports/GITHUB_PUBLICATION_PHASE7.md) and [release guide](RELEASE.md). The Phase 7 integrity overlay supersedes the current checkout gate; prior phase records remain historical.

# Continuous integration

The website is already hosted on InfinityFree. These workflows validate future changes and prepare verified update packages. They do not change the currently hosted site.

## Routine checks

| Workflow | Trigger | Checks |
| --- | --- | --- |
| Website CI | Relevant pull requests and pushes to main; manual | Clean pinned Node/npm and parser installation; TypeScript; saved-source checks; W6 integration, tour and download validators; publication guard fixtures; production build |
| Research CI | Relevant research/publication pull requests and main pushes; manual | Exact Git/source bytes and frozen baseline; workflow syntax; actual acquisition selection; budget, gates and streamed catalog parsing; saved-evidence and artifact safety fixtures |

Both workflows have read-only repository access, immutable action revisions, explicit timeouts and concurrency cancellation for outdated routine runs. Checkout credentials are not persisted. No routine job runs CrystalFormer generation, CHGNet relaxation, training or DFT. Small pinned NumPy/parser dependencies support deterministic tests and saved CIF parsing only.

Validators that write dated output paths execute in a new source export under runner temporary storage. Pre/post source checks keep accepted evidence unchanged. The website's original package manifest, npm lock and historical research locks remain unchanged.

## Manual workflows

Open the repository's Actions tab, choose the workflow and select Run workflow. Use an exact 40-character source commit; branch names and moving tags are not package identities.

| Workflow | Default and outputs | Boundary |
| --- | --- | --- |
| Evidence audit | Verify committed saved provenance without bulk downloads; optional declared public assets or exact upstream UPFs | Authenticated retrieval verifies the published Phase 7 selector; three private UPF-containing archives stay excluded |
| Release packaging | Build a selected accepted commit in a disposable copy, package it, verify ZIP/payload/source provenance and run publication --stage; downloadable Actions artifact | Does not publish a GitHub Release or assert a new browser session |
| Production deployment preparation | Download and verify the exact package artifact and stage the hosting handoff | Reports NOT_DEPLOYED; InfinityFree upload and live acceptance belong to Phase 8 |

These three also expose workflow_call for the dedicated Phase 6 acceptance workflow. The acceptance workflow runs intentionally on pushes changing CI code on ci/phase6, or manually; ordinary website/research changes do not trigger it. Its saved-evidence job, real package job and dependent handoff job establish fresh-run acceptance without creating a hosting credential or uploading anything.

The previous initial-ci.yml is a manual historical audit of the fixed Phase 5 commit. It does not run on normal pushes or pull requests.

## Evidence and release limits

The read-only saved-evidence audit checks retained inputs and payloads; it does not rerun historical experiments or claim a new scientific result. Optional external asset retrieval uses the scoped Phase 4 public selector, exact hashes and upstream policy. Actual permitted-asset upload and fresh release retrieval passed in Phase 7.

Package verification enforces the selected source SHA, producing run, payload inventory, staged entry and hosting policy. The recorded source_tree and producer_workflow_commit fields are producer assertions in this phase, rather than separate independently authenticated claims. Phase 7 can strengthen release attestations.

The full website release validator needs the historical predecessor omitted from Git. Phase 7 supplies the eighty-four-file support ZIP; manual packaging retrieves and validates it before running the full gate. Fresh shipping/rebuild Chrome smoke passed separately. Future changed interactions still require an appropriate fresh browser check; no live deployment is inferred.

## Integrity and review

Run the current gate from a clean committed checkout:

~~~powershell
python -I -B scripts/github_publication/verify_phase7.py --require-clean
~~~

Before committing, the same checker accepts --index. Supply --seal and --seal-sha256 with the independent recovery manifest to authenticate every selected byte. Without the external seal, current controls are compared to Git and explicitly reported as externally unsealed. The pinned completed Phase 6 baseline authenticates unchanged inputs.

Existing active application/research/publication source paths are explicitly enumerated as mutable controls so ordinary code edits can pass through normal pull requests. The baseline declaration field modified_frozen_input_paths includes these permitted source paths; it does not claim every listed file changed in this phase. actual_modified_baseline_paths records actual Phase 6 edits separately.

New files require exact additions to publication/git-files.txt, its literal NUL pathspec, generated controls and Phase 6 controls. The verifier rejects attempts to exempt baseline artifacts, datasets, configuration, contracts, historical reports, requirements or vendor files through metadata. Updating those frozen inputs needs a separately reviewed future protocol/overlay rather than a routine UI edit. Preserve prior baseline manifests and original evidence; do not force-add directories or normalize their bytes.

Official action and tool pins, permissions, triggers and acceptance boundaries are recorded under publication/phase6 and reports/github-publication-phase6. GitHub's [secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use) supports minimal permissions and full action commit pins; [workflow documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow) explains manual and reusable triggers.

## Later phases

Phase 7 published and independently retrieved/rebuilt v0.1.0 with the permitted assets. Phase 8 connects the accepted package to InfinityFree's verified upload transport, preserves old assets and sidecars, publishes index.html last, checks /refresh and the submission link, and verifies rollback. Hosting secrets belong only to that isolated deployment path.
