# Local release ui-w6-37bfb28892a8c9f8cb22

This archive contains the exact production document-root files, including the versioned release manifest. It does not contain source, dependencies, scientific environments, credentials or a study archive. It has not been deployed.

For a local HTTP preview, run the pinned Node executable with `scripts/qa-server.mjs --port 4175` from `website/`, then open `http://127.0.0.1:4175/`. Alternatively run `scripts/npm.ps1 run preview -- --port 4175`. Do not open index.html with file://.

W7 must inspect the authenticated account, confirm document root and HTTPS, back up current files, upload immutable files and manifest first, preserve predecessor immutable assets, replace index.html last, then verify in a fresh normal browser. The local ZIP is a handoff artifact, not a substitute for those checks.
