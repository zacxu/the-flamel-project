# Permanent submission link

Share **https://theflamelproject.42web.io/refresh**. The accepted root policy internally serves the current `index.html` at that address and sends no-store headers. It does not refer to a dated release copy. Keep this address in the hackathon submission after future updates.

The publication guard checks the prepared source identity, current release package, every `dist` file/hash, release manifest, runtime CSV, emitted asset references and the accepted cache/image policy. It is outside `scripts/` so this workflow addition does not change the current application fingerprint. No build, upload, network request or research run is performed by the guard.

Run these from `website/` with Node 24 (or the bundled Node executable):

```powershell
# Read-only by default. Always name the package produced for the next publication.
node deployment/latest-link/prepare-publication.mjs --package=reports/CRYSTAL_LAB_RELEASE_PACKAGE.json

# Exercise positive and adversarial temporary fixtures.
node deployment/latest-link/test.mjs

# Explicitly stage the verified current root policy, exact entry and upload plan.
node deployment/latest-link/prepare-publication.mjs --package=reports/CRYSTAL_LAB_RELEASE_PACKAGE.json --stage
```

Replace the example `--package` with the actual package record created by a future release. There is deliberately no historical package default. New prepared UI identities are supported; packages or entries from a different identity are rejected.

Staging writes only `deployment/latest-link/staged/<uiBuildId>/host/.htaccess`, `entry-last/index.html` and `upload-plan.json`. The staged entry retains the exact `index.html` basename for File Manager upload. An identical stage can be reused; a different existing stage is never overwritten. Nothing in `dist/`, the prepared identity, historical reports or live hosting is modified.

Follow the generated plan: upload/verify new immutable files first and retain old versioned assets and all existing scientific image sidecars. Update changed mutable pointers such as `research/manifest.json` before publishing the entry, even when their paths already exist. Preserve the accepted root/child configuration, and publish the exact staged entry as `/htdocs/index.html` last. Never replace a versioned path with different bytes or replace the current root policy with the historical image-only adapter. The accepted root policy hash is `cfec2cddb8cbbf215fbe2ee17593a20f8b470d80071648ddb6d79004a8bbd149`.

After publication, click the link from the actual submission, confirm its UI build identity and release-manifest hash, and inspect that `/refresh` serves the new entry with no-store headers. A local gate cannot establish remote publication success or refresh a tab that remains open without navigation. Browsers or third-party applications outside the site's control can still retain a previous display; do not promise automatic replacement of already-open pages.
