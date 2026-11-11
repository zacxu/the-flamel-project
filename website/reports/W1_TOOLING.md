# W1.1: pinned local frontend tooling

Verified 22 October 2026. This is the W1 foundation and build smoke check. The six-view website, interaction implementation, final payload-size check and deployment belong to W2–W7.

## Runtime and pinned dependencies

The existing bundled **Node v24.19.0** is reused. The project engine is Node `^24.15.0`. Vite 8.3.5 declares `^20.19.0 || >=22.12.0`, so the selected runtime is supported. This was verified against the [official Vite requirements](https://vite.dev/guide/) and exact-version [npm registry metadata](https://registry.npmjs.org/vite/8.3.5), saved in [npm_metadata.json](npm_metadata.json).

The bundled runtime does not include npm. [npm.ps1](../scripts/npm.ps1) therefore uses a **workspace-only npm 12.2.1**, downloaded from the official registry with the archive's pinned SHA-512 integrity checked before extraction. Its files live under ignored `.tooling/`; its download cache lives under ignored `.cache/`. No global package installation, permanent PATH change, Python installation or scientific-environment modification was performed. Node 24.19.0 also satisfies npm 12.2.1's `^24.15.0` engine branch.

| Package | Exact version | Role |
|---|---|---|
| React / React DOM / react-is | 19.3.1 | UI runtime and Recharts peer |
| TypeScript | 7.0.2 | Strict type checking |
| Vite | 8.3.5 | Local development and static production build |
| @vitejs/plugin-react | 6.1.2 | React compilation |
| Recharts | 3.10.1 | Planned recorded-data charts |
| Three.js | 0.186.1 | Planned crystal viewer |
| @types/node | 24.10.0 | Node 24 type declarations |
| @types/react / @types/react-dom | 19.3.0 | React type declarations |
| @types/three | 0.186.0 | Three.js type declarations |

All direct versions are exact. `package-lock.json` version 3 pins transitive tarball identities/integrity. `engine-strict=true` rejects unsupported runtimes. Build configuration uses relative asset paths, binds local servers to loopback, disables source maps and uses a conservative 850 kB chunk warning. The W6 release gate must enforce actual provider limits on the complete application.

## Reproduce locally

Run from `website/` in PowerShell:

```powershell
.\scripts\npm.ps1 ci --ignore-scripts --audit=false
.\scripts\npm.ps1 run data:export
.\scripts\npm.ps1 run data:validate
.\scripts\npm.ps1 run data:verify-loader
.\scripts\npm.ps1 run typecheck
.\scripts\npm.ps1 run build
.\scripts\npm.ps1 run tooling:verify
.\scripts\npm.ps1 run preview -- --port 4173
```

The wrapper resolves `FLAMEL_NODE` first, then the existing Codex bundled Node under the user's profile, then a Node executable on PATH. Set `FLAMEL_NODE` if another supported Node 24 installation should be used. npm is not required globally. The first wrapper invocation needs network access to bootstrap npm; `ci` needs either registry access or a populated local cache. `--ignore-scripts` is supported by this pinned dependency tree: the actual Windows native bundler is installed as a resolved optional package, and the verified build does not need install scripts.

The data commands call [run-python.mjs](../scripts/run-python.mjs), which reuses `../.envs/analysis/Scripts/python.exe`, or `FLAMEL_PYTHON` if explicitly configured. Export logic remains in the W1 research scripts. The helper permits only scripts inside `website/scripts/` and does not create or modify an analysis environment.

To repeat the local tooling/HTTP verification with the selected Node executable:

```powershell
$nodeExe = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
& $nodeExe scripts/verify-tooling.mjs
```

Add `--audit` only when a fresh advisory query is desired. It uses npm's official registry advisory endpoint. Without that flag, the verifier uses the recorded advisory response. It starts and closes a temporary loopback HTTP preview on port 4177; no background server is left running.

## Verification evidence

- `npm ci --ignore-scripts --audit=false` completed from the exact lockfile: **73 installed packages** on Windows x64.
- `npm run build` completed **strict TypeScript checking and the Vite production build**.
- **124/124 final tooling/build-copy checks passed**, including exact installed/lockfile pins, package engine compatibility, a complete dependency tree, the recorded registry audit, local HTTP entry/module loading, foundation JS size and every production research asset. The initial setup had 46 checks; final integration adds release/manifest and copied-asset checks. See [runtime.json](runtime.json).
- The recorded [dependency advisory audit](dependency_audit.json) reported **0 info, low, moderate, high or critical vulnerabilities**. This is the registry result at the recorded verification time, not a guarantee about future advisories.
- Foundation output: `index.html` **436 bytes**; JS **219,846 bytes uncompressed**, approximately **68.74 kB gzip**. These figures cover the W1 smoke entry only. Complete exported-data/image and W2–W6 UI payloads require their later measurements.
- Installed third-party licence texts, including vendored nested notices, are copied under [licenses/dependencies](../licenses/dependencies/). [W1_DEPENDENCY_LICENSES.json](W1_DEPENDENCY_LICENSES.json) records hashes and provenance. Non-Windows optional packages present only in the cross-platform lockfile are recorded in [dependency_licenses.json](dependency_licenses.json); they were not installed or bundled here.

`tooling:verify` checks an existing production build; it does not rebuild it. Run `build` after source/export changes and before that verifier. The final production copy contains only the active pinned data release, with each file compared to its expected hash and size. Loader corruption and scientific source checks have separate reports linked in [W1_COMPLETION.md](W1_COMPLETION.md).

The minimal entry truthfully labels itself the W1 foundation. No charts, viewer, six-view navigation, guided tour, scientific backend, hosting login or upload is claimed by these checks. Runtime caches, `node_modules/`, `dist/` and local logs are excluded from source control by the website-local `.gitignore`; only reviewed `dist/` contents become a later deployment payload.
