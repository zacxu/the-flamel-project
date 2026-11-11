# Live logo outline update

Deployed and verified on **23 October 2026 (Singapore)** at [The Flamel Project](https://theflamelproject.42web.io/). Active UI: **`ui-w6-61a05eb4a69162cc438b`**. The research release remains **`data-v1-2a138b7808f0d12c5151`**.

The header logo now has the homepage paper background (`#f6f2e9`), copper hexagon/cube linework (`#92522f`) and the larger copper centre dot (`r=4`). The hexagon has no coloured interior fill. The existing accessible overview link, responsive sizes and CSS are retained. This replaces the earlier filled-facet interpretation; its [report](LOGO_UPDATE.md), [archived evidence](logo-versions/faceted/) and release remain preserved.

TypeScript checking and the production build passed, followed by **832 local integrity checks**. Targeted live browser observations are retained in [LOGO_OUTLINE_BROWSER_CHECKS.jsonl](LOGO_OUTLINE_BROWSER_CHECKS.jsonl). Desktop inspection confirmed the active UI identity, paper background, copper linework/dot and original **37 × 44 px** size. [Desktop](LOGO_OUTLINE_LIVE_DESKTOP.jpg), [mobile](LOGO_OUTLINE_LIVE_MOBILE.jpg) and [header](LOGO_OUTLINE_LIVE_HEADER.jpg) screenshots retain the visual result. [Deployment metadata](LOGO_OUTLINE_DEPLOYMENT.json) records the final observed checks.

Exactly **five new immutable files** were uploaded first: three hashed JavaScript chunks and the versioned manifest/CSV. The exact **1,150-byte `index.html`** was published last. The [staging inventory](LOGO_OUTLINE_UPLOAD_STAGING.json) retains all hashes and paths; the UI manifest SHA-256 is `d6efa01c80d69a6bc9084936e3efb8254c3bafec9971312127155a020fe1ef35`. No images, sidecars, CSS, hosting configurations or credentials were changed. Frozen research, historical W1–W7 evidence and the prior logo release remain unchanged.

To restore the preceding faceted-logo release, upload [`deployment/logo-outline-update/previous-dist/index.html`](../deployment/logo-outline-update/previous-dist/index.html) as `/htdocs/index.html`, keep every immutable asset and the existing image routing, and verify HTTPS. That entry restores UI `ui-w6-b9a4161a2557c7e7620c`. The [historical W7 deployment record](../DEPLOYMENT_RECORD.md) retains original hosting recovery details.

All **seven final live checks passed**, including desktop/mobile appearance, release identity, the Replay chart, the interactive crystal viewer, zero captured console errors and the exact public release-manifest hash.

These targeted checks cover the visual revision; the full historical W6/W7 test suite was not rerun.
