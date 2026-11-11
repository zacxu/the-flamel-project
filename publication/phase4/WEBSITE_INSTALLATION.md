# Standalone website installation

Tested platform: Windows x64, Windows PowerShell 5.1, Node 24.22.1, npm 12.2.1. The source declares Node ^24.15.0 and exact npm 12.2.1; this installer deliberately chooses one exact tested Node release. Linux/macOS are not asserted tested by this Windows installer.

From a clean source checkout, use a tool directory outside the repository:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\github_publication\install_website.ps1 -ToolchainRoot 'D:\FlamelTools'
~~~

The installer downloads Node from its official release URL and verifies the pinned SHA-256. It inspects archive paths, extracts only a previously absent runtime, and verifies every installed runtime file against the pinned ZIP before reuse. It uses the repository's existing SHA-512-pinned npm bootstrap and separately verifies all 1,942 installed npm files against that archive before executing npm.

User/global npm configuration and inherited environment options do not enter the child install. The public website .npmrc remains unchanged. The installer runs npm ci --ignore-scripts, npm ls --all, strict TypeScript checking and the production build. Dependency lifecycle scripts stay disabled; the locked frontend built successfully without them. The exact package.json and package-lock.json hashes must remain unchanged.

The installer sets FLAMEL_NODE and an isolated PATH for its child commands, so a Codex runtime or global Node/npm installation is not required. It restores the caller's environment on completion. Downloads, cache and installation receipt stay in ToolchainRoot; node_modules, generated UI identity and dist are in the checkout. Existing website tooling remains unchanged.

## Verify saved research in a disposable copy

The source/science validators replace their W6 report files. Run them in a disposable source copy, never over accepted historical evidence. Pass the separately installed Phase 4 maintenance Python explicitly:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\github_publication\install_website.ps1 -ToolchainRoot 'D:\FlamelTools' -PythonExe 'D:\FlamelPython\envs\analysis-maintenance-cpu\Scripts\python.exe' -ValidateSavedEvidence
~~~

This runs the eleven W6 integration validators, tour, short-URL, orientation and publication-guard tests using saved inputs only. It does not train a model, generate structures, relax candidates, run DFT or deploy. The Python environment requires the separately pinned scientific parsing packages; a bare Python interpreter is insufficient for the CIF validators.

For local preview, set the pinned Node override and use the existing wrapper from website/:

~~~powershell
$env:FLAMEL_NODE = 'D:\FlamelTools\node-v24.22.1-win-x64\node.exe'
Set-Location -LiteralPath .\website
.\scripts\npm.ps1 run preview -- --port 4173
~~~

Open http://127.0.0.1:4173/ and stop the foreground server with Ctrl+C. Do not open dist/index.html with file://.

The build preserves the frozen data release and derives its UI ID from the exact website source. Original source/build inputs are not reformatted. A successful install/build and automated source/HTTP checks do not establish fresh native-browser interactions or production acceptance. Actual deployment remains subject to website/AGENTS.md and the permanent submission-link guard.

The future repository is still unpublished during Phase 4. The clean exported source used for local reproduction is a byte-verified stand-in for the future clone; no remote clone or GitHub runner execution is claimed.
