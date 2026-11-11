# Keep the submission link current

The permanent link saved in hackathon submission 7 is `https://theflamelproject.42web.io/refresh`. Preserve this address for future website updates. It must serve the **currently published** `index.html`, never a copied or dated release page.

Before publishing any website release:

- Run the publication guard in `deployment/latest-link/prepare-publication.mjs` with the new release's package record and `--stage`. Use the bundled Node runtime described in `README.md`. Resolve guard failures before publishing; do not bypass the checks or reuse a stage from a different build.
- Use its staged `.htaccess` and exact entry file. The accepted hosting policy is `deployment/cache-fix/.htaccess`; historical image-only recovery configurations remove the permanent link and must not replace it.
- Upload new immutable assets and release metadata first, update any changed mutable pointers listed in the plan, retain older assets and the existing image sidecars, apply the staged hosting configuration, then replace `/htdocs/index.html` last. Never clear the document root as part of an update.
- Open the website link from the saved submission after publication. Confirm that `/refresh` serves the staged build, its HTML response has `Cache-Control: no-store`, and the requested website features work. A successful upload or local build alone does not establish live acceptance.

Keep historical release and scientific evidence intact. Host-only deployment changes need no application rebuild when the prepared source identity and current release bytes remain unchanged. No recurring monitor is required by these instructions.
