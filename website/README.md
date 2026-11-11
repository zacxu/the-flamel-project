# The Flamel Project website

**Permanent submission link:** [Open the latest published website](https://theflamelproject.42web.io/refresh). This address serves the current `index.html` with no-store headers; it is not tied to a release ID. For future updates, use the [guarded publication workflow](deployment/latest-link/README.md) and [website publication instructions](AGENTS.md). The guard checks the prepared build, complete release inventory and hosting policy, and stages the exact configuration and entry for upload. Verify the live build after publishing.

**Shared-link cache fix — 23 October 2026:** The host's former 30-day HTML cache is now disabled for the homepage and `/index.html`; clicked links loaded the current UI. A [fresh entry link](https://theflamelproject.42web.io/refresh) bypasses copies cached before this fix. Future uploads must preserve [the current 1230-byte root configuration](deployment/cache-fix/.htaccess), which retains the image adapter. [Verification and rollback](reports/CACHE_FIX_UPDATE.md).

**W1-W7 complete: live deployed and verified.** Explore [The Flamel Project](https://theflamelproject.42web.io/). The [deployment record](DEPLOYMENT_RECORD.md) and [W7 completion](reports/W7_COMPLETION.md) retain final live checks, image-routing adaptation and rollback instructions.

The [live Crystal Lab refresh](reports/CRYSTAL_LAB_UPDATE.md) adds a responsive camera/atom control panel, saved lattice-axis presets and a Cartesian orientation compass. Active UI: `ui-w6-351e6182d7af3a9d062d`. [Workflow architectures and contribution text](reports/WORKFLOW_VISUALS_UPDATE.md), the cleaned footer, compact URLs, paper/copper logo, frozen research and historical evidence remain intact.

The six views connect the frozen study's workflow, recorded acquisition replay, real crystal structures, generation/uncertainty findings and complete validation evidence. The six-step guided presentation runs for three minutes, with pause, previous, next and exit controls. Ordinary browsing remains available. No website interaction trains a model, generates a crystal or runs DFT.

- [W6 completion report](reports/W6_COMPLETION.md) and [QA report](QA_REPORT.md): completed work, exact final measurements, browser coverage, screenshots and remaining verification limits.
- [Local preview and rehearsal](LOCAL_PREVIEW.md): PowerShell commands, a thirteen-step fallback rehearsal and the local release handoff.
- [Implementation status](IMPLEMENTATION_STATUS.md), [phased plan](PHASED_IMPLEMENTATION_PLAN.md) and [website plan](WEBSITE_PLAN.md): all requirements, historical phase evidence and final optional-feature dispositions.
- [Independent source/science review](reports/W6_REQUIREMENTS_REVIEW.md) and [integration validation](reports/W6_INTEGRATION_VALIDATION.json): fresh regression assertions, scientific boundaries, source hashes and contrast measurements.
- [Release verification](reports/W6_RELEASE_VALIDATION.json) and [package record](reports/W6_RELEASE_PACKAGE.json): exact build ID, file inventory/hashes, measured file budgets, cached predecessor compatibility and ZIP location. W7 deployed the same base with a separately recorded static host adapter.
- [Tour contract](contracts/GUIDED_TOUR_CONTRACT.md): deterministic presets, presentation state and cancellation. [Route/state](contracts/ROUTE_STATE.md), [replay](contracts/REPLAY_CONTRACT.md), [geometry/export](contracts/CRYSTAL_CONTRACT.md), [findings/evidence](contracts/FINDINGS_EVIDENCE_CONTRACT.md), [data](contracts/DATA_CONTRACT.md) and [component](contracts/COMPONENT_PATTERNS.md) contracts define the existing interfaces.
- Historical completion reports: [W1](reports/W1_COMPLETION.md), [W2](reports/W2_COMPLETION.md), [W3](reports/W3_COMPLETION.md), [W4](reports/W4_COMPLETION.md), [W5](reports/W5_COMPLETION.md). Their dated reports and accepted evidence are preserved.

Run from `website/` in PowerShell. The pinned wrapper reuses the local Node 24 runtime and workspace npm 12.2.1; no global npm installation is needed. Dependencies are already installed in this checkout. First-use setup elsewhere is documented in [runtime setup](reports/W1_TOOLING.md).

```powershell
.\scripts\npm.ps1 run build
.\scripts\npm.ps1 run preview -- --port 4173
```

Open [the local HTTP preview](http://127.0.0.1:4173/) and stop the foreground server with `Ctrl+C` after presenting. `build` automatically prepares the source-bound UI identity before strict TypeScript checking and Vite production compilation. Do not open `dist/index.html` through `file://`.

For read-only validation and a newly prepared local release:

```powershell
.\scripts\npm.ps1 run w6:integration -- --run
.\scripts\npm.ps1 run w6:tour
.\scripts\npm.ps1 run build
.\scripts\npm.ps1 run w6:downloads
.\scripts\npm.ps1 run release:package
.\scripts\npm.ps1 run w6:release
.\scripts\npm.ps1 run w6:tooling
.\scripts\npm.ps1 run w6:integration -- --include-tooling
```

The integration runner executes eleven W6 source/science/state/geometry/lifecycle validators and binds their report hashes. Those regressions passed **224,507 assertions**; totals include repeated contexts, not independent scientific observations. Other individual commands are `w6:state`, `w6:data-guards`, `w6:loader`, `w6:research`, `w6:replay`, `w6:playback`, `w6:crystal`, `w6:viewer`, `w6:generation`, `w6:uncertainty` and `w6:evidence`. W6 commands preserve historical W1-W5 reports. Use these current commands for current code; older phase commands are retained for historical reproducibility and can replace their own dated reports if invoked.

`w6:downloads` runs after `build` prepares the current UI identity and verifies retained actual W6 browser files; it does not conduct a new native-browser session. Recollect the affected browser files after any change to their interactions, selection semantics, output or recorded build identity. Package before final tooling: packaging adds the two release-manifest/inventory files that tooling must bind. Browser actions, real three-minute rehearsal and any unavailable environments are documented in [QA_REPORT.md](QA_REPORT.md). W6 used the available in-app browser on desktop and mobile viewports. Chrome and Edge access was attempted but unavailable; physical touchscreen and other untested device/browser behavior remain explicit limits. Repository/write-up/video controls remain disabled until verified public assets exist.

The active research release is pinned in [release.ts](src/data/release.ts), with manifest integrity enforced by [loadRelease.ts](src/data/loadRelease.ts). All 103 research inputs, 75 curated payloads, both manifest copies, numerical freeze and experiment/budget ledgers remain unchanged. UI-only darker policy colours improve graphical contrast; the original exported palette and scientific figure bytes remain available. Lossless presentation images are separately versioned and hash-bound.

The retained W7 image transport uses thirty-three opaque image sidecars and root/child configuration recorded in [W7 host files](reports/W7_HOST_FILES.json). Use direct-file upload for recovery and publish the saved entry last; ZIP extraction is not the tested upload method. The original hosting files and local rollback payload are retained. Website completion does not complete the hackathon write-up, video, repository publication or submission. Preserve accepted W1-W7 evidence before running commands that can replace their dated reports.
