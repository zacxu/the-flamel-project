# GitHub publication Phase 7

Status: COMPLETE — 11 November 2026. [Private release v0.1.0](https://github.com/zacxu/the-flamel-project/releases/tag/v0.1.0) | [Release guide](../RELEASE.md) | [Release state](../publication/phase7/release-state.json).

The reproducible release is published, independently downloaded and rebuilt using the tagged repository and declared assets. It contains exactly seventeen verified assets totaling 4,168,276,975 bytes. The existing InfinityFree website is unchanged.

## Fixed release identity

- Source commit: 84115354ef9d1acad65401869ade392e9039da16.
- Source tree: 4e59b829f4ea23b7c8f4833f5c1e23e9cffd0d55.
- UI identity: ui-w6-351e6182d7af3a9d062d.
- Release ID: 441459014.
- Production payload: 88 files, 5,691,844 bytes.
- Payload ZIP SHA-256: 668b9a7767e283f5a2a47e82b90f3a16cf571b3bd770332ef25eb2ac9636af4c.
- Outer production bundle SHA-256: a97a4b6411e044d29d5fca545b767c4bf5480494757d047a3acc445aed248bf9.
- Canonical record SHA-256: 8f0a9bd6c65bf377aff12d7578b311571b10eab551d82c5edad4b74abc10ee45.

The selected passing commit is contained in main with the same source tree. Website and research CI passed on the selected source and its containing main commit. Release publication never changes that tag or rebuilds its shipping bytes. Later main commits record completion metadata; final main/clone/recovery hashes are external to avoid self-reference.

## What was released

The twelve research/notice archives retain their audited bytes: eleven permitted originals and the mandatory third-party notice ZIP. Five additional assets provide the seven-file production handoff ZIP, exact eighty-four-file predecessor support, complete release-validation evidence, canonical record and SHA256SUMS. The record lists fifteen payloads; checksums also cover the record. Neither metadata file hashes itself. Bootstrap validates their relationships and all seventeen GitHub API digests.

The repository remains private and retrieval requires normal authenticated GitHub access. The helper rejects an unexpected asset set, missing notices, changed archive hashes, unsafe names, wrong tags/source commits and all three withheld UPF archives, including renamed copies. No credentials or signed query URLs are embedded in the release.

The actual GitHub immutable-release flag is false; this is not a claim that GitHub administratively locks the assets. Source and release identities are fixed by checksums and the no-clobber workflow. Future updates require a new version.

## Measured acceptance

| Check | Actual result |
| --- | --- |
| Selected-source CI | Website and research PASS; [website](https://github.com/zacxu/the-flamel-project/actions/runs/42992100693), [research](https://github.com/zacxu/the-flamel-project/actions/runs/42992100376) |
| Containing-main CI | [Website PASS](https://github.com/zacxu/the-flamel-project/actions/runs/42992722215), [research PASS](https://github.com/zacxu/the-flamel-project/actions/runs/42992722087) |
| Shipping build | One local disposable build; full release validator 1,098/1,098; 84 pinned predecessor files and 94 actual loopback HTTP responses |
| Shipping browser | Fresh-profile Chrome: 99/99 desktop/loopback smoke checks, actual saved geometry/canvas/axes/controls; no page, console or request errors |
| Actual GitHub retrieval | 17 assets, 4,168,276,975 bytes downloaded through the actual tagged fresh-clone helper; all file/API digests matched |
| Research verification | 12 archives, 907 members |
| Project recovery | 777 files; 767 new ignored paths, ten matching tracked notices reused |
| Exact upstream retrieval | One real new fetch, three canonical UPFs and 41 raw input placements |
| Saved evidence | 103 source inputs and 75 public payloads PASS; no model deserialization |
| Source preservation before rebuild | All 5,332 tagged files matched before/after hydration; Git clean |
| Production cold recovery | 140 files with notices; restored offline verifier independently checked 123 captured files and 75 payloads |
| Independent rebuild | Fresh standalone toolchain from the same tag plus downloaded/upstream assets; 1,098/1,098 release checks and 99/99 fresh Chrome smoke checks |
| Rebuild comparison | All 88 file records, UI identity and payload ZIP match the published shipping package byte for byte |
| Off-workstation evidence | [GitHub Linux PASS](https://github.com/zacxu/the-flamel-project/actions/runs/43000973414): authenticated permitted-archive retrieval/verification and exact upstream audit |
| Off-workstation full build | [GitHub Windows PASS](https://github.com/zacxu/the-flamel-project/actions/runs/43000978144): full release gate; downloaded Actions validation payload matches the permanent release ZIP SHA-256 |
| Shipping immutability | Original seven-file handoff and shipping payload retained unchanged; verification rebuild was never substituted |

The namespace-isolated full recovery/rebuild ran on the original Windows host using only the fresh source and declared inputs. Separately, actual GitHub-hosted Linux/Windows runners verified remote asset retrieval/upstream inputs and the full website build. The remote Windows output was downloaded and its payload ZIP matched the published shipping archive. It remains a validation artifact and never replaced the release.

The final shipping build was local, not a GitHub Actions production build. Its accurate source/tree/build-count receipt is in the validation asset. The seven-file bundle retains Phase 6 compatibility provenance; a fixed workflow-name field there is not an Actions attestation. The canonical record states the actual producer.

## Integration correction and safeguards

The first real attempt exposed GitHub's draft API behavior: release-by-tag omits drafts. It stopped after creating an empty draft and before transferring any asset. The owned empty draft and tentative unpublished tag were removed, and the rejected candidate/evidence were retained separately. The source helper now uses a bounded repository-list fallback, exact unique tag/repository/draft validation and twenty-one passing transport fixtures. The corrected source received a new final shipping build. No published release was overwritten.

Additional boundaries passed fifteen research-asset fixtures, eleven predecessor fixtures and five Phase 7 control-policy fixtures. Source/operational controls and new support/production/validation archives were scanned, including nested ZIPs, with zero unresolved credential findings. Pattern scanning is not a guarantee of unknown-secret detection. Historical manifests, locks, vendor bytes, application/scientific source and accepted research evidence remain preserved.

## Scope and next phase

The public-distribution-eligible subset is hosted privately. The three original UPF-containing archives, thirty-six byte-different serialized scratch UPFs and other withheld restart history remain outside this release. Upstream reconstruction restores only exact raw placements. Full private historical recovery still uses the original backup; this release does not claim to restore withheld scratch or establish new scientific results.

Browser results are fresh desktop headless loopback smoke, not full manual/touch or live hosting acceptance. No training, generation, relaxation, QE/DFT or InfinityFree upload ran.

Phase 8 connects deployment of these exact verified bytes to the existing InfinityFree site, preserves old dependencies/sidecars, publishes index.html last, and verifies the live /refresh/submission link and rollback. The final external PHASE7_COMPLETION.json binds current main, the independent clone, release identities, recovery seals and cleanup.
