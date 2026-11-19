# Updating the existing InfinityFree website

The production site is [The Flamel Project](https://theflamelproject.42web.io/). The permanent link in [hackathon submission 7](https://scientificintelligence.org/campaigns/osi-hackathon-2026/submissions/7) is [/refresh](https://theflamelproject.42web.io/refresh). Both entry URLs should serve the same release. For v0.1.0 the existing site uses the archived Crystal Lab controls ZIP inside the asset named `flamel-website-builds-001.zip` from the [published GitHub release](https://github.com/zacxu/the-flamel-project/releases/tag/v0.1.0).

## Preparing and verifying the release

Open [Production deployment](https://github.com/zacxu/the-flamel-project/actions/workflows/production-deployment.yml), choose **Run workflow**, select **main** and choose **prepare**. The controller reads the recorded release identity, downloads the production bundle, checks the outer archive, selected ZIP and original package record, and stages the entry and hosting rules using the publication guard. The report identifies the release and the files approved for upload. Download and keep the verified package and reports with the release.

The release state binds the repository, release ID, source commit and tree, build ID and asset digests. For a future version, publish and verify a new release first, then point `publication/phase8/deployment-target.json` to its verified release state through a pull request.

## Inspecting the existing site

In the hosting account's **FTP Details**, find the hostname, username and hosting password. Add them as GitHub Actions secrets named `INFINITYFREE_FTP_HOST`, `INFINITYFREE_FTP_USERNAME` and `INFINITYFREE_FTP_PASSWORD`. Use the FTP hostname from the account. The client uses explicit FTPS on port 21 and validates the server certificate.

Inspect the live entry through a browser. In its network panel confirm that the final HTML response from `/refresh` contains the expected build ID and `Cache-Control: no-store`. Compute the SHA-256 of that response body. Supply this **current** entry digest to the workflow and select **inspect**. Compare its findings against the intended release before deployment. A changed immutable path needs investigation. A matching site needs no upload.

## Publishing a change

Select **deploy** on main using the observed current entry digest. Save the deployment run ID and download the rollback snapshot from the run for long-term recovery. The workflow verifies existing files, retains older versioned files, scientific image sidecars and child configuration, then uploads new immutable content, updates mutable pointers, applies the staged root configuration and publishes the entry last. Check the job result and the browser acceptance evidence before recording a successful update.

Open the website link on the submission. Check that the final HTML matches the staged entry, its response has `no-store`, and the expected versioned resources load. In Crystal Lab, rotate the structure, inspect its axes and select a site. Exercise file downloads and verify their sizes and digests.

## Rolling back

Use **rollback** on main with the run ID for the deployment whose snapshot you need to restore. Specify the workflow attempt if the run was retried. GitHub keeps these snapshots for up to 90 days, subject to repository retention limits. The snapshot contains the bytes served by that site before the deployment. The workflow checks the snapshot and current remote bytes before restoring mutable files, the root configuration and then the entry. It preserves old versioned dependencies. Recheck the submission, entry digest, cache header, Crystal Lab and downloads against the preceding release.

If a run stops midway, inspect its snapshot and receipts before retrying. Preserve evidence and review any differences from both expected states before making another change. For manual recovery after a snapshot artifact expires, use the retained snapshot or the preceding verified hosting package and its upload plan. Verify every prerequisite and restore the saved entry last.
