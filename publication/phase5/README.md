# Initial Git publication

The Phase 5 overlay preserves the exact Phase 4 baseline while adding publication controls and the initial CI workflow. Large datasets/models remain optional declared assets; private configuration, the signed-header original and three UPF-containing archives remain excluded.

- baseline-inputs.json: all 5,260 selected records at the completed Phase 4 cutoff.
- control-paths.json: the exact new/modified Phase 5 paths; complete current hashes are sealed externally.
- ci-pins.json: primary sources and immutable official action revisions.
- The current literal staging selection remains publication/git-files.txt and git-pathspec.nul.
- Eight hash-reviewed upstream ignore exceptions remain in publication/phase3; never force-add a directory.

Run verify_phase5.py for baseline/coverage checks, or supply the external complete --seal and trusted --seal-sha256 to authenticate every current byte. verify_git_publication.py additionally compares the complete index or HEAD path set and every Git blob with the working files. Default index staging is never inferred from broad add commands.

The initial workflow runs standard-library source/evidence/safety checks on Ubuntu and a pinned-tool website build on Windows. It downloads no research archives, installs no research model environment and runs no scientific experiments. Full workflow separation, evidence/release automation and deployment remain Phase 6 onward.

The first baseline push and its independent clone are recorded before the closeout documentation commit. Final commit/tree/clone hashes live in the external PHASE5_COMPLETION.json, avoiding the impossible requirement for a commit to contain its own hash. Git itself identifies the checkout's current commit.

The repository stays private. Hosting and versioned release assets are unchanged by this phase.
