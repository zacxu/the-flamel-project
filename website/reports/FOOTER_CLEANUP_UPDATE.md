# Live footer cleanup

Deployed and verified on **23 October 2026 (Singapore)** at [The Flamel Project](https://theflamelproject.42web.io/). Active UI: **`ui-w6-066edb222a3354b8bced`**. Research remains **`data-v1-2a138b7808f0d12c5151`**.

Removed the bottom footer-note paragraph containing the frozen-study date, guided-presentation description and local-release text. The footer keeps its project name, research-prototype description, **Copy view link** and **Reset exploration** controls. The build identifier is retained only as nonvisible diagnostic metadata (`data-ui-build`). The logo and compact URL behavior are unchanged.

TypeScript checking and the production build passed, followed by **1,097 package/integrity checks**. All **7 targeted live browser checks passed**; [raw observations](FOOTER_CLEANUP_BROWSER_CHECKS.jsonl) and [deployment metadata](FOOTER_CLEANUP_DEPLOYMENT.json) retain acceptance details. This cosmetic change required no new tests or broad historical-suite rerun.

Live acceptance confirmed the removed text and footer-note element are absent on desktop and mobile, both footer controls remain, the homepage URL stays bare, mobile has no horizontal overflow and no captured console errors occurred. The public release manifest matched its expected hash. [Desktop](FOOTER_CLEANUP_LIVE_DESKTOP.jpg) and [mobile](FOOTER_CLEANUP_LIVE_MOBILE.jpg) screenshots retain the visible result.

Exactly **five immutable files** were uploaded first: three new hashed JavaScript chunks and the release manifest/CSV. The exact **1,150-byte `index.html`** was published last. UI manifest SHA-256: `af9c36fa3e1628c126bc17937a0b0c5a9182da958484cd849572cb09cb5d7576`. The [staging inventory](FOOTER_CLEANUP_UPLOAD_STAGING.json) retains exact file hashes. No CSS, research, images, sidecars, hosting configurations or credentials changed. Historical W1–W7, logo and short-URL evidence remain intact.

To restore the preceding release, upload [`deployment/footer-cleanup/previous-dist/index.html`](../deployment/footer-cleanup/previous-dist/index.html) as `/htdocs/index.html`, retain every immutable asset and the existing image routing, then verify HTTPS. That entry restores UI `ui-w6-37bfb28892a8c9f8cb22`.
