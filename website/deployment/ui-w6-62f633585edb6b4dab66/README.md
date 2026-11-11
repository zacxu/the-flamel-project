# W7 local upload staging

This folder stages the exact verified W6 release. It has not been deployed by the staging script.

1. Inspect the authenticated account, verify the assigned document root and back up existing files.
2. Upload and extract `immutable-first.zip` into that document root. Its 87 files exclude `index.html`. Preserve existing unrelated and predecessor immutable paths.
3. Verify those 87 paths and then publish `index-last.html` under the remote filename `index.html`. It is byte-identical to the packaged production index.
4. Verify fresh HTTPS operation and record W7 evidence.

Do not upload this README, local reports, source, dependencies, credentials, the W6 ZIP itself or a nested dist folder as website content.
