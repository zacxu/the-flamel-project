# Reviewed baseline staging policy

Phase 3 does not initialize Git, stage, commit, push or deploy. Phase 4 still owns fresh installation. In Phase 5, configure Git before the first staging:

```powershell
git init -b main
git config core.autocrlf false
git config core.longpaths true
```

The root .gitattributes sets * -text, preserving original bytes even with autocrlf enabled. Never run git add --renormalize on this baseline. Windows clones need git -c core.longpaths=true clone ... when paths could exceed MAX_PATH.

Stage only the audited literal entries in publication/git-pathspec.nul. Eight original CrystalFormer files are ignored by its unchanged upstream .gitignore. Their exact paths and expected hashes are in upstream-ignore-exceptions.json; upstream-ignore-force-pathspec.nul includes only those eight. Phase 5 must verify their source bytes and security review, stage the remaining allowlist normally, then force-add only the eight reviewed literal paths. Never git add -f a directory or all ignored paths.

After staging, compare the index path set against git-files.txt, inspect every staged blob hash against the final Phase 3 integrity seal plus later approved changes, and rerun the secret scan. A new file, changed byte or unknown ignore conflict invalidates earlier clearance. The private HTTP header receipt and local environment config are excluded explicitly.

Historical Phase 2 inventories/seals remain immutable. Phase 3 disposition-overrides.json controls the one newly withheld input. Release uploads must use release-selection.json, not all entries from the older artifacts.json. Public candidates must ship their required sidecar licence notices. All archives remain local/unpublished at this phase.
