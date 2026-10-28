# Contributing

Please open an issue describing the workflow or bug before a substantial change. Never include API keys, customer page content, private webhook URLs, or account credentials. Contact [Geonode support](https://geonode.com/contact) privately for security-sensitive reports.

## Local checks

Run from the repository root:

```sh
python3 scripts/test_client_header.py
```

Keep existing package names, node/credential identifiers, module keys, and connection fields compatible. Add or update focused tests when behavior changes. Document user-facing changes in `CHANGELOG.md`. Live platform tests need a separate test account and explicit release coordination; passing local checks is not a live integration test.

## Releases

A change to the app definition merged to `main` is published to Make by the `Publish` workflow, so review app changes before merging.
