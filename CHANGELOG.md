# Changelog

All notable changes to the Make app will be documented in this file. Make app versions are majors; changes inside a major are listed by date. Earlier changes are not listed.

## Unreleased (app version 1)

- The integrations page link and package homepage point to this integration's own page.

- Removed the internal repository preparation notes and links to the old monorepo.

- README: the base URL note now matches `base.imljson`, and a step about Basic Auth is gone. The connection sends only `X-Api-Key`, which is all the API needs.

## 2026-10-19 (app version 1)

- Every request, including the connection check, sends `X-Geonode-Client: make/1`, so the API can tell Make traffic apart. Make sets its own User-Agent, which is why this is a separate header. `scripts/test_client_header.py` keeps the header equal to the app version in `metadata.json`.
