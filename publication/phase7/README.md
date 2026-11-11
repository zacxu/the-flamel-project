> v0.1.0 is published privately. All seventeen release assets were downloaded and verified, research/production recovery passed, and independent local/GitHub-runner builds matched the published payload. See [the completed release report](../../reports/GITHUB_PUBLICATION_PHASE7.md). Historical preparation notes below retain their original scope.

# Reproducible release

Phase 7 creates the private v0.1.0 GitHub Release. Publication and independent retrieval must succeed before the phase is marked complete. See [the release guide](../../RELEASE.md) and [completion report](../../reports/GITHUB_PUBLICATION_PHASE7.md).

- baseline-inputs.json retains the exact completed Phase 6 source seal. verify_phase7.py pins its SHA-256.
- control-paths.json declares current mutable source and operational controls separately from actual changes. Accepted scientific evidence, contracts, historical requirements, vendor bytes and prior phase manifests stay frozen.
- public-assets.json selects the unchanged eleven permitted research archives plus the mandatory notice ZIP. The three private UPF-containing archives remain excluded. This selector uses actual v0.1.0 release URLs; repository authentication remains required.
- release-layout.json declares the twelve research/notice assets and five production/metadata assets.
- The production bundle contains the exact built website ZIP and its staged entry, policy, upload plan and checksums. The predecessor support ZIP contains only the eighty-four files pinned by the historical W6 baseline.
- The canonical release record identifies the selected passing source commit, tree, UI identity, payload checksums and validation evidence. Its asset table excludes itself and SHA256SUMS to avoid self-reference.

The selected release commit remains fixed after publication. Later completion documentation may advance main without moving the release tag or rebuilding its production bytes. Actual hosting upload remains Phase 8; the existing InfinityFree site is unchanged.
