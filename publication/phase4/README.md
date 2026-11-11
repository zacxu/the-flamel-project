# Phase 4 reproduction controls

Start with [the installation guide](../../INSTALLATION.md) and [the completion report](../../reports/GITHUB_PUBLICATION_PHASE4.md).

- [Python environment/security decision](ENVIRONMENT_POLICY.md) and [exact specifications](../../requirements/phase4/README.md).
- [Standalone website installation](WEBSITE_INSTALLATION.md).
- [Permitted asset retrieval](ASSETS.md), [public selector](public-assets.json) and [exact upstream UPFs](upstream-upfs.json).
- [Measured asset validation](ASSET_VALIDATION.json).
- baseline-inputs.json records the complete Phase 3 selected bytes before Phase 4 changes.
- control-paths.json declares the new/modified Phase 4 overlay without rewriting scientific history.

Use scripts/github_publication/verify_phase4.py for baseline/coverage checks. Default mode explicitly leaves mutable controls unsealed. Full verification requires the independently trusted external selected-files.json and its SHA-256 from the Phase 4 completion receipt.

Historical Phase 2/3 manifests and previous seals remain immutable. The public selector intentionally does not promise full private scratch recovery. All release URLs remain unpublished; source installation/asset tests do not establish actual remote GitHub or live hosting acceptance.
