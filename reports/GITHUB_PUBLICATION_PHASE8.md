# InfinityFree deployment and rollback

On 20 November 2026, a fresh Chrome session opened the website link saved in [submission 7](https://scientificintelligence.org/campaigns/osi-hackathon-2026/submissions/7). The site served the original Crystal Lab controls release, build `ui-w6-351e6182d7af3a9d062d`.

| Live check | Result |
| --- | --- |
| Entry at /refresh and / | Both returned HTTP 200 and a no-store cache directive. The 1,150-byte entry matched SHA-256 `49fb03717c0efe8f037ade093072b35f5d90c90f1db50938bcfe2233b701ef68`. |
| Original hosting payload | All 88 files matched the original production package record by size and SHA-256. Six predecessor resources remained available. |
| Crystal Lab | Camera rotation, reset, XYZ compass and lattice axes passed. |
| Downloads | Clicking CIF and CSV download links produced the expected names, content hashes and sizes of 2,321 and 1,632 bytes. |

## Production package selection

The original hosting ZIP is an audited member of `flamel-website-builds-001.zip` in [private release v0.1.0](https://github.com/zacxu/the-flamel-project/releases/tag/v0.1.0). Its digest is `ccff9618e0c74d9c98ac3c378b7e361876e18befdd32640b7e64bf6cdec19ca5`. Its original package record has digest `f7d9fdf1e162a4d906d09fadf3ea7507edc658df10d6fa8354ec53fd66575da0`.

The Phase 7 rebuilt website bundle matches 87 of the 88 hosted files. Its versioned manifest records the W5 build used for reproduction. The original production manifest records the actual previous production build, `ui-w6-359b66f2fb63f90e993c`. The two manifests differ only in `predecessorUiBuildId`. Publishing the rebuild onto the existing site would overwrite a versioned path with different bytes. The deployment workflow therefore selects the archived original for this release and verifies its entire inventory.

## Rollback test

On a local explicit FTPS server, the client verified a TLS 1.3 connection and encrypted data transfers. The rehearsal started with the immediately preceding archived production ZIP. Seven files changed during deployment, the entry was published last, and a second deployment wrote zero files. Restoring the entry brought back the previous release. All 92 original files and test sentinels, including an image sidecar and child hosting configuration, matched afterward. The saved snapshot and readback results are in `FTPS_LOOPBACK_ACCEPTANCE.json`.

## Evidence

The independent local browser receipt and screenshots are in `D:\Backups\TheFlamelProject\phase8-20261120-deployment\live-production`. The receipt SHA-256 is `5c10938b1bc8abed291f8570518006c72da5b5770440691adad5c16df3997241`. The comparison against the Phase 7 rebuild is retained alongside it under `live-release-comparison`.

The [deployment and rollback guide](../DEPLOYMENT.md) describes the workflow operations and snapshot retention. Authenticated host verification is pending.
