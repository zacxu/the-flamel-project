# Updating the existing InfinityFree website

The production site is [The Flamel Project](https://theflamelproject.42web.io/). The permanent link in [hackathon submission 7](https://scientificintelligence.org/campaigns/osi-hackathon-2026/submissions/7) is [/refresh](https://theflamelproject.42web.io/refresh). Both entry URLs should serve the same release. For v0.1.0 the existing site uses the archived Crystal Lab controls ZIP inside the asset named `flamel-website-builds-001.zip` from the [published GitHub release](https://github.com/zacxu/the-flamel-project/releases/tag/v0.1.0).

## Preparing and verifying the release

Open [Production deployment](https://github.com/zacxu/the-flamel-project/actions/workflows/production-deployment.yml), choose **Run workflow**, select **main** and choose **prepare**. The controller reads the recorded release identity, downloads the production bundle, checks the outer archive, selected ZIP and original package record, and stages the entry and hosting rules using the publication guard. The report identifies the release and the files approved for upload. Download and keep the verified package and reports with the release. For the original production target the expected HTML digest is `49fb03717c0efe8f037ade093072b35f5d90c90f1db50938bcfe2233b701ef68`.

The release state binds the repository, release ID, source commit and tree, build ID and asset digests. For a future version, publish and verify a new release first, then point `publication/phase8/deployment-target.json` to its verified release state through a pull request.

## Inspecting the existing site

In the hosting account's **FTP Details**, find the hostname, username and hosting password. Add them as GitHub Actions secrets named `INFINITYFREE_FTP_HOST`, `INFINITYFREE_FTP_USERNAME` and `INFINITYFREE_FTP_PASSWORD`. For this account set the hostname to `ftpupload.net`. The client uses explicit FTPS on port 21 and validates the server certificate.

Inspect the live entry through a browser. Confirm the build ID in the running site. In the browser network panel, confirm the final HTML response from `/refresh` has `Cache-Control: no-store`. The live acceptance receipt records the SHA-256 of those exact HTML bytes under `entries`. Supply this **current** entry digest to the workflow and select **inspect**. Compare its findings against the intended release before deployment. A changed immutable path needs investigation. A matching site needs no upload.

## Publishing a change

Select **deploy** on main using the observed current entry digest. Save the deployment run ID, attempt and source commit. Download the encrypted rollback snapshot for long-term recovery. The workflow encrypts it with the 32-byte `FLAMEL_ROLLBACK_KEY` Actions secret. Retain that key for as long as its snapshots are needed. A recovery copy encrypted for the original Windows user is stored outside Git in the Phase 8 backup as `rollback-key.current-user.dpapi`. The workflow verifies existing files, retains older versioned files, scientific image sidecars and child configuration, then uploads new immutable content, updates mutable pointers, applies the staged root configuration and publishes the entry last. Check the job result and the browser acceptance evidence before recording a successful update.

Open the website link on the submission. Check that the final HTML matches the staged entry, its response has `no-store`, and the expected versioned resources load. In Crystal Lab, rotate the structure, inspect its axes and select a site. Exercise file downloads and verify their sizes and digests.

## Rolling back

Use **rollback** on main with the run ID for the deployment whose snapshot you need to restore. Specify the workflow attempt if the run was retried. GitHub keeps these snapshots for up to 90 days, subject to repository retention limits. The snapshot contains the bytes served by that site before the deployment. The workflow checks the snapshot and current remote bytes before restoring mutable files, the root configuration and then the entry. It preserves old versioned dependencies. Recheck the submission, entry digest, cache header, Crystal Lab and downloads against the preceding release.

If a run stops midway, inspect its snapshot and receipts before retrying. Preserve evidence and review any differences from both expected states before making another change. For manual recovery after a snapshot artifact expires, use the retained snapshot or the preceding verified hosting package and its upload plan. Verify every prerequisite and restore the saved entry last.


## Opening a downloaded snapshot on the original Windows account

Retain the deployment run ID, its attempt number, the full release source commit and the encrypted `snapshot.bin`. Run the following PowerShell commands from the project root. Supply the values from the deployment that **created** the snapshot. Choose an output directory that does not already exist. These commands authenticate the snapshot and recover files on local disk.

```powershell
Add-Type -AssemblyName System.Security
$phase8Backup = 'D:\\Backups\\TheFlamelProject\\phase8-20261120-deployment'
$protectedKey = [IO.File]::ReadAllBytes((Join-Path $phase8Backup 'rollback-key.current-user.dpapi'))
$rawKey = [Security.Cryptography.ProtectedData]::Unprotect($protectedKey, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
try {
    $env:FLAMEL_ROLLBACK_KEY = [Convert]::ToBase64String($rawKey)
    node scripts/github_publication/phase8/snapshot-crypto.cjs open $outputDirectory $snapshotFile $sourceCommit $deploymentRunId $deploymentAttempt
    if ($LASTEXITCODE) { throw 'Snapshot authentication or recovery failed' }
} finally {
    [Array]::Clear($rawKey, 0, $rawKey.Length)
    Remove-Item Env:FLAMEL_ROLLBACK_KEY -ErrorAction SilentlyContinue
}
```

The recovered directory contains the previous payload ZIP, public inventory, and saved entry, research pointer and root configuration. Keep this directory with the private recovery files. The DPAPI recovery file requires the original Windows user profile.
