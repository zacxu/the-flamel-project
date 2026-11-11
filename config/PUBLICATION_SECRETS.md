# Local configuration and credentials

The two adjacent *.env.example files contain placeholders only. They are documentation templates, not a newly implemented application config loader. The website/research tools already accept FLAMEL_PYTHON and FLAMEL_NODE as shell environment overrides. Optional CrystalFormer MCP paths are separate from this project's frozen research run.

Local .env, .env.*, environment directories, .npmrc, private key files and deployment credentials stay outside the selected Git paths. The private original vendor MCP .env remains backed up. Examples ending in .env.example are intentionally eligible for review.

Before any first commit, scan the exact Git allowlist and intended release archives. Do not upload scanner raw findings or private audit logs. Only the hash-bound local-worker UUID findings in publication/phase3/secret-review-exceptions.json have been reviewed as non-service credentials. A new or changed match requires review. Never force-add a directory to bypass a security exclusion.

No reusable personal/service credential was identified in the Phase 3 publication scan. The original HTTP header receipt contains an expired signed public-data redirect plus a cookie header; it is withheld entirely, with an explicitly sanitized derivative for provenance. The signed redirect expired in October 2026 and was not a reusable personal account secret. This does not imply arbitrary future logs are safe. Revoke/rotate an actual exposed credential before publishing it or rewriting Git history.

Use encrypted GitHub environment/repository secrets for any future approved deployment transport; define their exact names and permissions in Phase 8. Current Phase 3 work does not configure or use deployment authentication.
