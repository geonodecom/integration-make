# Contributing

Please open an issue describing the workflow or bug before a substantial change. Never include API keys, customer page content, private webhook URLs, or account credentials. Contact [Geonode support](https://geonode.com/contact) privately for security-sensitive reports.

## Local checks

Run from the repository root:

```sh
python3 scripts/test_client_header.py
```

Keep existing package names, node/credential identifiers, module keys, and connection fields compatible. Add or update focused tests when behavior changes. Document user-facing changes in `CHANGELOG.md`. Live platform tests need a separate test account and explicit release coordination; passing local checks is not a live integration test.

## Releases

Do not publish from this repository yet. Read [release migration](docs/release-migration.md) for the current publishing location and the remaining handover checks.
