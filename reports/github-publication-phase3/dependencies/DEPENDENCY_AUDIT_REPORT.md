# Phase 3 dependency and provenance audit

Audit date: 11 November 2026, Singapore time. Scope: `D:\bears`, source and installed metadata only. Evidence directory: `D:\Backups\TheFlamelProject\phase3-20261111-audit\dependencies`.

## Outcome

The dependency audit is complete with findings recorded. The historical research dependencies remain frozen; they must not be described as free of known advisories. No package installations, upgrades, scientific runs, source changes, lock regeneration, deployment, or remote repository changes occurred in this audit.

- Website: Node v24.22.1 and the existing npm 12.2.1 CLI were inspected. Manifest root fields match package-lock v3; 73 installed packages match their exact lock versions. The lock contains 117 dependency entries, including optional/platform variants; 44 entries are not installed on this machine.
- Isolated `npm audit --package-lock-only --ignore-scripts --json`, with an explicit public registry and empty user/global config, returned 0 reported advisories across 117 dependency entries. Source manifests were copied into a new external input folder; source and copied hashes agree after the audit. No source npm wrapper/bootstrap was run.
- Analysis: all 51 installed distributions match all 51 exact frozen pins. Generator: all 60 exact pins match; the 61st installed distribution is the declared local CrystalFormer 0.6. No undeclared packages, missing pins or version mismatches were found.
- Metadata-only base requirements: analysis 70 and generator 102 applicable base requirements were checked with the frozen Python 3.11.14/Windows marker context; 0 missing dependencies, version conflicts or parse errors. Extras, binary loading, CUDA execution and runtime/API compatibility were not tested.
- All 89 retained frontend licence/notice file hashes match the existing W1 inventory of 73 installed packages. No notice was replaced or removed.
- OSV returned HTTP 200 with all 77 requested package/version results and no pagination. Full retrieval succeeded for 34 advisory records; none was withdrawn. Alias deduplication yields 31 advisory groups: 19 for torch and 12 for filelock. Other queried versions returned no matching records; this is advisory-database coverage, not proof that every release is available or secure.

## Findings and disposition

The frozen analysis environment includes `torch==2.6.0+cu124` and `filelock==3.32.3`. These dependencies run locally for research, not in the static browser exhibit. No exploit, malicious checkpoint, hostile lock directory or current website compromise was observed or tested.

1. **High: PyTorch checkpoint loading.** The maintainer's [GHSA-63cw-57p8-fm3p](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p) states that loading a malicious checkpoint can cause arbitrary code execution even with `weights_only=True`; its patched version begins at 2.10.0. This does not mean 2.10.0 resolves every returned PyTorch advisory: another returned GHSA has a fixed event at 2.13.0. Preserve original research locks as historical evidence. Before future research execution, separately resolve and test a compatible maintenance environment and evaluate all returned advisory groups; do not load untrusted checkpoints into the frozen environment.
2. **High: filelock local lock-directory attack.** The maintainer's [GHSA-v4x8-3wr5-3wq8](https://github.com/tox-dev/filelock/security/advisories/GHSA-v4x8-3wr5-3wq8) affects 3.20.4 through 4.2.0 and identifies 4.2.1 as patched. Its described attack requires another local user to plant or rename entries beside the SQLite-backed lock and contains POSIX-specific details. The frozen version falls in the published range; actual use of the vulnerable API/path was not established. The full set also contains Windows-specific filelock advisories. Preserve the historical lock and record a separate tested remediation decision before new research execution.
3. **Portability:** the generator lock and installed direct-url metadata refer to `file:///C:/Users/Admin/Desktop/bears/vendor/CrystalFormer`; this path does not relocate with the project. Preserve these original bytes. Phase 4 should supply a separate portable specification/bootstrap with the same historical versions and explicit upstream commit/local patch provenance, plus a documented security decision. Do not silently change the old lock or claim the new portable specification cures the advisories.
4. **Supply-chain/reproduction limits:** Python pins have no wheel/source hashes and include a platform-specific CUDA torch build; version matching alone does not prove artifact identity. The setup script uses Windows CPython 3.11.14 and the official CUDA 12.4 wheel index. The source's unsafe-best-match index strategy and external bootstrap downloads need explicit treatment in a future install workflow. No network installation or full fresh-environment reproduction was attempted here.
5. **Distribution scope:** retain website notices and all 89 copied frontend texts. The existing scoped website notice credits CrystalFormer Apache 2.0, CHGNet Modified BSD, QE GPLv2, and source-derived CC BY 4.0 datasets separately; it does not grant one blanket licence to checkpoints, pseudopotentials, datasets, or every upstream artifact. Root publication licences are audited separately by the parent task.

A private source publication can retain known historical versions with these findings visible; source preservation does not make them suitable for automatic execution. Phase 4/CI must keep any historical reproduction workflow explicitly separated from routine safe website checks and should not automatically install or run the frozen research environments until its recorded dependency decision is implemented and validated.

## Captured advisory groups

These are source-database affected-version results, deduplicated by shared advisory/CVE aliases. Fixed events are copied from returned records and are not a tested upgrade prescription. A missing severity label is retained as unknown rather than inferred from a different record. Full aliases, summaries, CVSS vectors and source references are in the JSON evidence.

| Package | Advisory group | Source severity | Returned fixed version events |
| --- | --- | --- | --- |
| torch | [GHSA-3749-ghw9-m3mg](https://github.com/advisories/GHSA-3749-ghw9-m3mg) | LOW | 2.7.1-rc1 |
| filelock | [GHSA-567q-5qvw-pf92](https://github.com/advisories/GHSA-567q-5qvw-pf92) | LOW | 4.2.1 |
| torch | [GHSA-63cw-57p8-fm3p](https://github.com/advisories/GHSA-63cw-57p8-fm3p) | HIGH | 2.10.0 |
| filelock | [GHSA-6627-m3xw-93mp](https://github.com/advisories/GHSA-6627-m3xw-93mp) | MODERATE | 4.2.1 |
| filelock | [GHSA-69hj-f68j-2879](https://github.com/advisories/GHSA-69hj-f68j-2879) | MODERATE | 4.2.1 |
| torch | [GHSA-887c-mr87-cxwp](https://github.com/advisories/GHSA-887c-mr87-cxwp) | MODERATE | 2.8.0 |
| filelock | [GHSA-8mx5-7m5m-r77g](https://github.com/advisories/GHSA-8mx5-7m5m-r77g) | MODERATE | 4.2.1 |
| filelock | [GHSA-9c4x-gm8v-wgc4](https://github.com/advisories/GHSA-9c4x-gm8v-wgc4) | MODERATE | 4.2.1 |
| filelock | [GHSA-9vhv-jxww-xfm5](https://github.com/advisories/GHSA-9vhv-jxww-xfm5) | LOW | 4.2.1 |
| filelock | [GHSA-cwqr-hh33-gh44](https://github.com/advisories/GHSA-cwqr-hh33-gh44) | MODERATE | 4.2.1 |
| filelock | [GHSA-fq56-3cx3-fjxp](https://github.com/advisories/GHSA-fq56-3cx3-fjxp) | MODERATE | 4.2.1 |
| filelock | [GHSA-j8f7-rjxc-mr56](https://github.com/advisories/GHSA-j8f7-rjxc-mr56) | MODERATE | 4.0.9 |
| filelock | [GHSA-m462-7rxw-wvpg](https://github.com/advisories/GHSA-m462-7rxw-wvpg) | MODERATE | 4.2.1 |
| torch | [GHSA-qfhq-4f3w-5fph](https://github.com/advisories/GHSA-qfhq-4f3w-5fph) | LOW | 2.10.0 |
| filelock | [GHSA-rfpc-qcw5-3pc4](https://github.com/advisories/GHSA-rfpc-qcw5-3pc4) | MODERATE | 4.2.1 |
| torch | [GHSA-rrmf-rvhw-rf47](https://github.com/advisories/GHSA-rrmf-rvhw-rf47) | LOW | 2.13.0 |
| filelock | [GHSA-v4x8-3wr5-3wq8](https://github.com/advisories/GHSA-v4x8-3wr5-3wq8) | HIGH | 4.2.1 |
| torch | [GHSA-vgrw-7cvw-pwgx](https://github.com/advisories/GHSA-vgrw-7cvw-pwgx) | MODERATE | 2.9.1 |
| torch | [PYSEC-2025-198](https://osv.dev/vulnerability/PYSEC-2025-198) | Not labelled by source | 2.7.0 |
| torch | [PYSEC-2025-199](https://osv.dev/vulnerability/PYSEC-2025-199) | Not labelled by source | 2.7.0 |
| torch | [PYSEC-2025-200](https://osv.dev/vulnerability/PYSEC-2025-200) | Not labelled by source | 2.7.0 |
| torch | [PYSEC-2025-201](https://osv.dev/vulnerability/PYSEC-2025-201) | Not labelled by source | 2.7.0 |
| torch | [PYSEC-2025-202](https://osv.dev/vulnerability/PYSEC-2025-202) | Not labelled by source | 2.7.0 |
| torch | [PYSEC-2025-203](https://osv.dev/vulnerability/PYSEC-2025-203) | Not labelled by source | 2.9.0 |
| torch | [PYSEC-2025-204](https://osv.dev/vulnerability/PYSEC-2025-204) | Not labelled by source | 2.9.0 |
| torch | [PYSEC-2025-205](https://osv.dev/vulnerability/PYSEC-2025-205) | Not labelled by source | 2.7.1 |
| torch | [PYSEC-2025-206](https://osv.dev/vulnerability/PYSEC-2025-206) | Not labelled by source | 2.9.0 |
| torch | [PYSEC-2025-207](https://osv.dev/vulnerability/PYSEC-2025-207) | Not labelled by source | 2.7.1 |
| torch | [PYSEC-2025-208](https://osv.dev/vulnerability/PYSEC-2025-208) | Not labelled by source | 2.7.1 |
| torch | [PYSEC-2025-209](https://osv.dev/vulnerability/PYSEC-2025-209) | Not labelled by source | 2.7.1 |
| torch | [PYSEC-2026-139](https://osv.dev/vulnerability/PYSEC-2026-139) | Not labelled by source | No fixed event in returned record |

## Evidence and reproduction notes

- `dependency-metadata-verified.json` is the authoritative metadata inventory. The earlier `dependency-metadata.json` is retained as an intermediate result; its first-line BOM parsing misclassified generator absl-py and the direct requirement. The verified inventory corrects both without editing source.
- `frontend-installed-metadata.json`, `frontend-licence-preservation.json`, and `python-base-metadata-check.json` record local checks.
- `npm-audit.json`, `npm-audit.stderr.txt`, `npm-input/`, `npm-cache/` and `npm-logs/` retain the isolated npm audit evidence. The npm notice of a newer patch release was informational; no update was applied.
- `osv-python-request.json`, `osv-python-response.json`, `osv-python-summary.json`, `osv-python-advisory-records.json`, `osv-python-advisory-triage.json`, and `osv-python-deduplicated.json` retain the official API queries/results and alias-aware triage.
- `source-input-preservation.json` confirms all four initially hashed source manifests/locks remained byte-identical: analysis lock, generator lock, website package.json, and website package-lock.json. The copied licence texts were independently checked against the existing hash inventory.
- The only `.npmrc` content exposed to the auditor's output was key names (`save-exact`, `engine-strict`, `fund`, `update-notifier`, `cache`). Empty isolated user/global configs were used for the npm audit; no credential values were printed.
- No fresh `npm ci`, build, pip installation, compiled runtime validation, model load, training, DFT calculation, or deployment was performed. These claims must not be inferred from the audit.

Official API method: [OSV batched package/version queries](https://google.github.io/osv.dev/post-v1-querybatch/). Full records were retrieved with `/v1/vulns/{id}`. Results describe the advisory database at audit time and require rechecking before future execution/publication.
