# Website release validation and predecessor recovery

Phase 7 adds helpers under scripts/github_publication/phase7 without changing the retained application, scientific evidence, dependencies or historical website validators.

The complete release gate requires the exact 84-file W5 predecessor omitted from Git. website_predecessor.py pins the W6_BASELINE.json digest 1ff35e05aaceb42f5a38293fd296e5b7a50d7774d010f6991062f8c32716f893 and W5 identity w5-ui-61310ee383dfae8b9003. It creates, verifies or restores only the baseline's exact filenames, sizes and hashes. Extra/missing/duplicate paths, links, corrupt bytes and overwrites are rejected. The production-support ZIP is separate from the eleven permitted research archives and their mandatory notice bundle.

The approved support ZIP contains 84 files and 5,227,006 raw bytes. Its deterministic ZIP is 2,743,450 bytes with SHA-256 24ed7e551669d53a10eef4920b6f0ff5ecf6659aa2f14d28accfceaf0505add4. It includes the predecessor's retained public notices; it adds no raw research models, private configuration or pseudopotentials. The release must also distribute the mandatory full companion notice bundle required by policy.

prepare_release.ps1 requires a clean disposable Git checkout, an immutable source SHA, this support ZIP and new external tools/output paths. It installs the existing pinned parser-only environment and Node/npm; performs exactly one successful production build; runs all eleven W6 regressions, tour, compact URL, orientation, publication guard and retained download checks; packages the unchanged dist; runs the complete existing verify-release.mjs; stages the exact package through the existing guard APIs in a new external directory; and runs the independent ZIP/stage verifier. Tracked input mutations are confined to reports and the generated UI identity in that disposable checkout. The original checkout is untouched. No model execution or hosting upload occurs.

A prototype against completed Phase 6 source ce05e715cbd7a9cc946c785c6c6356c2cd2c7c23 passed the full sequence: 1,098/1,098 release checks, 84 authenticated predecessor files and 94 actual loopback HTTP responses. Its package has 88 files and 5,691,844 raw bytes; the deterministic ZIP has 3,110,793 bytes and SHA-256 668b9a7767e283f5a2a47e82b90f3a16cf571b3bd770332ef25eb2ac9636af4c. These are prototype measurements, not a claim that the shipping release was built from that source. Root coordination selects the passing Phase 7 source before the single shipping build.

browser_smoke.mjs uses Node 24's built-in WebSocket and Chrome DevTools Protocol with a new isolated headless profile and a read-only loopback server. It verifies actual dataset hydration, compiled package identity, Crystal Lab WebGL canvas and physical sites, lattice/XYZ axes, actual rotate/axes/site/reset controls, absence of page/console/request errors, absence of external application requests and preservation of every built file. This is focused browser smoke, not full manual/touch testing or production acceptance. The prototype passed 99 checks and closed its browser and loopback server. Screenshots show actual local rendered UI.

CLI examples:

~~~powershell
python -I -B scripts/github_publication/phase7/website_predecessor.py verify --root <clone> --archive <downloaded-w5-predecessor.zip>

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/github_publication/phase7/prepare_release.ps1 -CandidateRoot <clean-disposable-clone> -SourceCommit <full-sha> -PredecessorArchive <downloaded-w5-predecessor.zip> -ToolchainRoot <new-external-tools> -OutputDirectory <new-external-bundle>

& <pinned-node.exe> scripts/github_publication/phase7/browser_smoke.mjs --website-root=<candidate/website> --browser=<chrome.exe> --output=<new-external-smoke-folder>
~~~

Prototype receipts, logs and screenshots are under D:/Backups/TheFlamelProject/phase7-20261111-release/website/prototype. Shipping source, package, fresh retrieval and final verification are recorded separately in the phase-level completion receipt.
