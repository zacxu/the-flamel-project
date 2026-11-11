# Live compact URL update

Deployed and verified on **23 October 2026 (Singapore)** at [The Flamel Project](https://theflamelproject.42web.io/). Active UI: **`ui-w6-37bfb28892a8c9f8cb22`**. The research release remains **`data-v1-2a138b7808f0d12c5151`**.

The default homepage now stays at the bare website address. Default section links are `#/workflow`, `#/replay`, `#/crystals`, `#/findings` and `#/evidence`. The serializer omits default selections and derived values. Changed controls can still add the minimal parameters needed to restore their state; for example, `#/replay?mode=seed&seed=20261024&budget=0&batch=1` preserves that saved replay preview. Existing long links normalize to compact links. The existing **Copy view** feature remains available; no separate Share feature was added.

TypeScript checking and the production build passed. The [shared state suite](SHORT_URL_STATE_VALIDATION.json) passed **606 checks**, the [compact URL regression](SHORT_URL_COMPACT_URL_VALIDATION.json) passed **76,491 checks**, and [release integrity/staging](SHORT_URL_UPLOAD_STAGING.json) passed **984 checks**. All **nine live browser checks passed**: bare homepage, default links, Replay navigation, custom split/budget reload, native Back/Forward, reset, crystal viewer, zero captured console errors and exact release-manifest hash. [Raw observations](SHORT_URL_BROWSER_CHECKS.jsonl), [homepage screenshot](SHORT_URL_LIVE_HOME.jpg) and [final URL state](SHORT_URL_LIVE_STATE.txt) retain the evidence.

Exactly **five immutable files** were uploaded first: three new hashed JavaScript chunks and the release manifest/CSV. The exact **1,150-byte `index.html`** was published last. The UI manifest SHA-256 is `1f9401f753210707e088213f740a7e842b6cf10473c35a721c671cbf037af235`. [Deployment metadata](SHORT_URL_DEPLOYMENT.json) records hashes, paths and acceptance. Research, the [paper/copper outline logo](LOGO_OUTLINE_UPDATE.md), CSS, images, sidecars, hosting configurations and credentials are unchanged. All historical W1–W7 and prior logo evidence remain preserved.

To restore the preceding outline-logo release, upload [`deployment/short-url-update/previous-dist/index.html`](../deployment/short-url-update/previous-dist/index.html) as `/htdocs/index.html`, retain all immutable assets and existing image routing, then verify HTTPS. That entry restores UI `ui-w6-61a05eb4a69162cc438b`.

These are targeted URL/state checks; the full historical W6/W7 suite was not rerun.
