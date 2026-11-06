# Changelog

All notable changes to the Make app will be documented in this file. Make app versions are majors; changes inside a major are listed by date. Earlier changes are not listed.

## Unreleased (app version 1)

- New **Make an API call** module (`make-api-call`). It sends any request to a path on `https://scraper.geonode.io` with the connection's API key and returns the status code, headers and body.

- The three wait modules now use Make's `repeat` directive. They check the job every 3 seconds for up to about 20 seconds, to stay inside Make's 40-second module limit. If the job is still running, they return its current status and job ID instead of an error. The **Poll Interval** and **Max Poll Attempts** inputs are gone, because Make needs fixed values for `repeat`.

- Module labels and descriptions follow Make's naming rules: sentence case, a verb first, and "Search" for list modules with filters. Module, connection and field keys are unchanged, so existing scenarios keep working.

- Date inputs of **Get usage statistics** and **Search extraction jobs** are sent as ISO 8601 UTC dates with `formatDate`.

- The connection check hides the API key in Make's logs, like the app base already does.

- The app label is now "Geonode" and the theme colour is `#0d0c21`, the colour of the Geonode symbol.

- `scripts/publish.py` no longer creates a new Make app when it cannot find the existing one. It stops with an error, unless `MAKE_ALLOW_CREATE=1` is set. `MAKE_DRY_RUN=1` works like `--dry-run`, and the publisher now also syncs labels and descriptions of existing modules. The `Publish` workflow runs as a dry run unless it is started by hand with **dry_run** unticked, or the `MAKE_PUBLISH_ON_PUSH` variable is `true`.

- README and guide: new module names, a clearer private-app note, and a fixed link in the guide.

- The integrations page link and package homepage point to this integration's own page.

- Removed the internal repository preparation notes and links to the old monorepo.

- README: the base URL note now matches `base.imljson`, and a step about Basic Auth is gone. The connection sends only `X-Api-Key`, which is all the API needs.

## 2026-10-19 (app version 1)

- Every request, including the connection check, sends `X-Geonode-Client: make/1`, so the API can tell Make traffic apart. Make sets its own User-Agent, which is why this is a separate header. `scripts/test_client_header.py` keeps the header equal to the app version in `metadata.json`.
