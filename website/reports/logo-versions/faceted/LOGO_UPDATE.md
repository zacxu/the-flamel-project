# Live logo update

Deployed and visually verified on **22 October 2026** at [The Flamel Project](https://theflamelproject.42web.io/). Active UI: **`ui-w6-b9a4161a2557c7e7620c`**. The research release remains **`data-v1-2a138b7808f0d12c5151`**.

The header mark now follows the supplied hexagonal reference: a bold rounded outer hexagon and six triangular facets. It keeps the existing copper colour (`#92522f`) and larger centre dot (`r=4`). The SVG remains decorative inside the existing accessible overview link.

The build and TypeScript checks passed, followed by **710 local integrity checks**. Desktop browser inspection confirmed the new source-bound UI identity, facet mask, copper colour and centre dot at the original **37 × 44 px** size. Mobile inspection confirmed **29 × 37 px** and no horizontal overflow at the observed 375 px document width. [Browser observations](LOGO_BROWSER_CHECKS.jsonl), [desktop screenshot](LOGO_LIVE_DESKTOP.jpg), [mobile screenshot](LOGO_LIVE_MOBILE.jpg) and [header close-up](LOGO_LIVE_HEADER.jpg) retain the evidence.

Exactly **five new immutable files** were uploaded first: three hashed JavaScript chunks and the new release manifest/CSV. The exact **1,150-byte `index.html`** was published last. [Deployment metadata](LOGO_DEPLOYMENT.json) and [staging inventory](LOGO_UPLOAD_STAGING.json) retain hashes and upload paths. No images, image sidecars, CSS, hosting configurations or credentials were changed. All frozen research, original releases and historical W1–W7 evidence remain intact.

The saved previous entry is [`deployment/logo-update/previous-dist/index.html`](../deployment/logo-update/previous-dist/index.html). To roll back this visual update, upload that file as `/htdocs/index.html`, retain both releases' immutable assets and existing image routing, then verify the public HTTPS page. The [historical W7 deployment record](../DEPLOYMENT_RECORD.md) retains the original image transport and placeholder recovery details.

Fresh live navigation also loaded the new Replay chart and interactive crystal viewer chunks successfully, retained the new logo on both routes and produced no captured console errors. The public versioned release manifest matched SHA-256 `28bcae1fc9d6d039f42cad79fad8bee508993dc3b55e343e274be180cd8d5a35`.

The targeted checks cover this visual update; the full historical W6/W7 test suite was not rerun.
