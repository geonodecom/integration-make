# Scraper API: Make.com Custom App

[Integrations page](https://geonode.com/integrations/integration-make) · [Geonode API docs](https://docs.geonode.com/docs/scraper-api) · [GitHub source](https://github.com/geonodecom/integration-make) · [Repository overview](../README.md)

Make.com (formerly Integromat) custom app for the Scraper API, built using the
Make Apps SDK (IMLJSON) format. Covers `/extract`, `/crawl`, `/batch`, `/map`,
and `/statistics`. Webhook endpoints are intentionally excluded.

## Status

**Private app, access by request.** The existing Geonode app is deployed as `scraper-api-production` in the US2 zone. There is no public marketplace listing. The source template retains its `scraper-api` metadata identifier; the existing CI supplies the deployed app name and zone. See [release migration](release-migration.md) before running publisher commands.

## Set up the Make.com connector

1. [Request private app access](https://geonode.com/contact). Tell Geonode which Make organization and zone you use; accept the supplied invitation before searching for the app in the scenario editor. There is no public install link yet.
2. Create an API key under **API Keys** in the [Geonode dashboard](https://app.geonode.com/).
3. Create a scenario, add the Geonode app supplied through the invitation, and choose **Extract a URL (Sync)**.
4. Create an **API Key** connection and paste your Geonode key. The connection sends `X-Api-Key` and checks authenticated usage statistics.
5. Enter `https://example.com` in **URL** and select **Markdown** in **Output Formats**. The module defaults to HTML, so select Markdown explicitly.
6. Choose **Run once**. Inspect the output bundle: **Extracted Data → Markdown** (`data.markdown`) should contain page text and **Metadata → URL** (`metadata.url`) should identify the source.
7. Add your destination module and map those fields. Run the complete scenario once before turning on its schedule.

A successful connection test checks authentication; the extraction output confirms that the scenario actually retrieved a page. Keep the API key in the connection, not in scenario descriptions or exported examples.

## Example: website content → Google Sheets

Use a URL from your scenario → **Extract a URL (Sync)** → **Google Sheets: Add a Row**. Create columns named `Source URL`, `Content`, and `Usage`, then map `metadata.url`, `data.markdown`, and `tokens_charged` into them.

The Geonode module retrieves content. Google Sheets is a separate Make module with its own connection. For an AI summary, insert your chosen AI module between extraction and Sheets, and pass it the Markdown plus source URL. These are workflow recipes, not preinstalled or live-tested scenario blueprints.

## All 15 Make modules

| Capability | Modules | What you get |
| --- | --- | --- |
| Extract a page now | **Extract a URL (Sync)** | Markdown and/or HTML in the same operation. |
| Extract in the background | **Extract a URL (Async)**; **Get an Extraction Job**; **List Extraction Jobs** | A job ID, subsequent status/results, or one bundle per listed job. |
| Wait for a short extraction | **Extract a URL (Wait for Completion)** | Starts extraction and polls within the module. |
| Crawl a website | **Start a Crawl**; **Get Crawl Status**; **Cancel a Crawl**; **Start a Crawl (Wait for Completion)** | Collect linked pages within configured depth and page limits. |
| Process a URL list | **Start a Batch Extraction**; **Get Batch Status**; **Cancel a Batch**; **Start a Batch (Wait for Completion)** | Submit a list, follow its progress and retrieve results. |
| Discover links | **Map URLs from a Site** | One bundle per discovered URL, with its discovery source. |
| Check account usage | **Get Usage Statistics** | Usage information for the connected account. |

### Control how pages are retrieved

Extraction, batch and crawl inputs expose **Render JavaScript**, browser wait settings, and proxy controls where defined by the module. Wait for a page lifecycle event or a CSS selector/XPath before capture. Setting a wait option enables JavaScript rendering. Country and proxy-type settings let you configure the request; rendering and account usage remain subject to your Geonode plan.

For longer jobs, save the returned job ID and use separate start/status steps with bounded polling. The wait helpers hold the operation open and suit shorter tasks; configure their interval and maximum attempts. Do not resubmit a job just because a polling step times out.

### Know which output to map

| Output | Use it for |
| --- | --- |
| `data.markdown` / `data.html` | Page content from a completed extraction. |
| `metadata.url` | Preserve the original source alongside derived content. |
| `metadata.http_status` | Inspect the target page's HTTP response status. |
| `tokens_charged` | Review the reported usage for this extraction. |
| `job_id` | Retrieve a background job later; it is not the final page content. |
| `url` / `source` | Link and discovery source from the Map module. |

## Common questions

**Why can't I find Geonode in Make?** It is a private app. Confirm that you accepted the supplied access for the correct organization and zone; a Geonode account alone does not install it in Make.

**Why is Markdown empty?** Explicitly select Markdown in Output Formats, inspect the source URL and status, and confirm that an asynchronous job has completed before mapping content. Enable rendering when the page depends on JavaScript.

**Can this monitor prices or extract product fields?** It retrieves page content. Add your own parsing or AI step to turn that content into product fields, and a storage/comparison step to detect changes. This connector does not promise a ready-made product schema or change detector.

**Is this an MCP connector?** This repository provides native Make scenario modules. For an AI assistant that uses the Model Context Protocol, use the separate [Geonode MCP server](https://docs.geonode.com/docs/scraper-api/guides/mcp/00_overview).

**Does it include web search or webhook triggers?** Those modules are not defined in this Make source. Use the listed modules or evaluate a separate Geonode API or workflow integration for those needs.

The module names and fields above were reviewed against this repository's source. Live Make scenario execution and parity with the app deployed in your account have not been verified in this review.

## Layout

```
./
  metadata.json                   app-level metadata (name, label, theme)
  base.imljson                    shared baseUrl, headers, error mapping
  connections/
    api-key/                      "API Key" connection (X-Api-Key header)
      metadata.json
      parameters.imljson          fields shown when user creates the connection
      common.imljson              shared data exposed to modules
      api.imljson                 connection test request (calls GET /statistics)
  modules/
    extract-url/                  POST /extract (sync) — returns the result inline
    extract-url-async/            POST /extract (async) — returns job_id
    extract-wait/                 helper: async start + poll until done
    extract-get-job/              GET /extract/{job_id}
    extract-list-jobs/            GET /extract/jobs (search — one bundle per job)
    crawl-start/                  POST /crawl
    crawl-get-status/             GET /crawl/{job_id}
    crawl-cancel/                 DELETE /crawl/{job_id}
    crawl-wait/                   helper: start + poll until terminal state
    batch-start/                  POST /batch
    batch-get-status/             GET /batch/{job_id}
    batch-cancel/                 DELETE /batch/{job_id}
    batch-wait/                   helper: start + poll until terminal state
    map-urls/                     POST /map (search — one bundle per link)
    get-statistics/               GET /statistics
```

Each module directory contains:

| File | Purpose |
| --- | --- |
| `metadata.json` | label, description, `typeId` (4 = action, 9 = search), action type |
| `api.imljson` | request/response mapping (URL, method, body, qs, output, polling) |
| `expect.imljson` | mappable input fields shown in the scenario editor |
| `interface.imljson` | output schema rendered as mappable fields downstream |
| `samples.imljson` | sample output used during scenario design |

## Before publishing

1. **Base URL** — `base.imljson` points at the production API,
   `https://scraper.geonode.io/v1`. If you want per-deployment overrides, add a
   `baseUrl` field to `connections/api-key/parameters.imljson` and switch
   `base.imljson` to read `{{connection.baseUrl}}`.
2. **App version + icon** — `metadata.json` declares `version: 1`. Bump on each
   publish. Add an `app.png` (512x512) and reference it via the Developer Hub
   when uploading.

## Authentication

The connection collects a single field, **API Key** (stored as
`connection.apiKey`), and sends it as `X-Api-Key` on every request via
`base.imljson`. The connection test (`connections/api-key/api.imljson`) hits
`GET /statistics`, which is a cheap, authenticated read.

## Long-running jobs (extract async / crawl / batch)

Two patterns are exposed for every async-style endpoint:

- **Primitives** — `*-start`, `*-get-status`, `*-cancel`. The user composes the
  poll loop themselves with native Make modules (Sleep, Repeater, router).
  Recommended for production scenarios because it returns control to Make
  between polls.
- **`*-wait` helper** — single module that starts the job and then polls
  internally using Make's `response.valid.condition` + `response.wait`
  retry mechanism. Returns the final result in one operation. Convenient for
  ad-hoc work but holds a scenario operation open for the entire polling
  window, so use only for short jobs.

For each `*-wait` module, the user controls polling cadence via:

- `poll_interval_seconds` (default 5–10s)
- `max_attempts` (default 60)

Total wait window ≈ `poll_interval_seconds × max_attempts`. When the cap is
exceeded the request fails with the last-observed status in the error message.

## Browser wait configuration

The `/extract` (sync + async), `/batch`, and `/crawl` modules expose three
optional **wait** fields that map to the API's `wait_config` object, controlling
how long the headless browser settles before the DOM is captured:

- **Wait Until** (`wait_until`) — lifecycle event to wait for: `commit`,
  `domcontentloaded`, `load`, or `networkidle`.
- **Wait For Selector** (`wait_for`) — a CSS selector or XPath expression to
  wait for before extracting.
- **Wait Timeout (ms)** (`wait_timeout`) — an exact post-ready delay in
  milliseconds (`0`–`30000`).

Notes on behaviour, mirroring the API contract:

- Wait options only apply when a browser runs. Setting **any** wait field
  **auto-enables Render JavaScript** in the request body (`render_js` is forced
  to `true`), because the API rejects `render_js=false` combined with explicit
  wait values as ambiguous. Leaving all wait fields empty sends no wait policy,
  so the default `Render JavaScript` toggle is honoured as-is.
- Empty wait fields are pruned from the request, so they count as "not
  provided" and the server falls back to its adaptive default settle policy.
- The persisted wait policy is surfaced back on the status/result modules under
  `metadata.wait_config` (extract) and `*_config.wait_config` (batch / crawl).

## Publishing reference (maintainers only)

These commands describe the publisher. They are not part of local validation; production publishing goes through the `Publish` workflow. That workflow sets `--app-name scraper-api-production` and `--zone-url https://us2.make.com`; never rely on the template defaults for that app.

## Publishing to Make

Three workflows, in order of recommendation for ongoing maintenance:

### 1. `scripts/publish.py` (this repo)

Bulk-pushes the whole local tree to Make via the SDK REST API. Idempotent —
re-run any time to sync local edits up to Make. Uses only the Python
standard library (no `pip install` needed); requires Python 3.10+.

Get an API token at Make → Profile → **API/MCP access** → **Add token**.
Required scopes: `apps:read`, `apps:write`.

All settings are passed as command-line arguments. Run
`python scripts/publish.py --help` for the full list.

| Argument | Default | Notes |
| --- | --- | --- |
| `--token` | _(required)_ | Personal API token |
| `--app-name` | `metadata.json::name` | Override app name |
| `--app-version` | `metadata.json::version` | Override app version |
| `--zone-url` | `https://eu1.make.com` | Make zone base URL |
| `--team-id` | _(none)_ | Required if your token is team-scoped |
| `--user-agent` | browser-like UA | Override UA (Cloudflare blocks Python-urllib) |
| `--dry-run` | off | Preview the planned requests without writing |
| `--verbose` | off | Log every request + payload |

**PowerShell (Windows):**

```powershell
python scripts/publish.py --token "your-token"

# With optional overrides
python scripts/publish.py `
    --token "your-token" `
    --app-name "scraper-api" `
    --app-version "1" `
    --zone-url "https://eu1.make.com" `
    --team-id "123456" `
    --user-agent "Mozilla/5.0 ..."
```

**Bash (macOS/Linux):**

```bash
python3 scripts/publish.py --token "your-token"

# With optional overrides
python3 scripts/publish.py \
    --token "your-token" \
    --app-name scraper-api \
    --app-version 1 \
    --zone-url https://eu1.make.com \
    --team-id 123456
```

**Recommended first run** — dry-run with verbose to inspect what will be sent:

```powershell
python scripts/publish.py --token "your-token" --dry-run --verbose
```

Then drop the `--dry-run` flag and re-run to actually publish:

```powershell
python scripts/publish.py --token "your-token"
```

What it does:

1. Reads `metadata.json` for app name/version/label/theme/etc.
2. `GET /apps/{name}/{version}` — if 404, `POST /apps` to create; otherwise
   `PATCH` label/description/theme.
3. `PUT /apps/{name}/{version}/base` with `base.imljson`.
4. For every directory under `connections/`, creates the connection (if new)
   then PUTs whichever of `api`, `common`, `parameters`, `scope`, `scopes`,
   `installSpec`, `install`, `uninstall` `.imljson` files exist.
5. For every directory under `modules/`, creates the module (if new) with
   `name`, `label`, `description`, `typeId`, `actionType`, `connection`
   from its `metadata.json`, then PUTs whichever of `api`, `parameters`,
   `expect`, `interface`, `samples`, `scope`, `epoch`, `attach`, `detach`,
   `update` `.imljson` files exist.

Caveats:

- Make's SDK REST endpoint shapes can vary between zone versions. If a step
  fails the script prints the HTTP status and response body — adjust the
  endpoint in `publish.py` and re-run.
- 409 (already exists) on create is treated as success.
- The script never deletes anything on Make — if you remove a module locally,
  delete it manually in the Developer Hub.
- Make's API is fronted by Cloudflare and returns **HTTP 403 / error 1010
  (`browser_signature_banned`)** to the default `Python-urllib/x.y` user
  agent. The script ships a browser-like User-Agent so this works out of
  the box; override via `--user-agent` if needed.
- **`HTTP 403 / SC403 "Access denied or App not found"`** from Make
  itself (different from Cloudflare 1010 above) means one of:
  1. The app doesn't exist yet — the script treats 403 the same as 404
     on the initial GET and tries to create. If the create then returns
     409, it surfaces a clear error.
  2. The token belongs to a different team than the app — find your
     team ID in any Make URL (`/team/{id}/...`) and pass `--team-id`.
  3. The token is missing scopes. Required: `apps:read`, `apps:write`,
     `app-development`.

### 2. VS Code extension: "Make Apps Editor"

Edit any file → save → auto-upload. After install:

1. Open **Settings (User, JSON)** and add:
   ```json
   "apps-sdk.environments": [
       { "name": "Make EU1", "url": "https://eu1.make.com", "apikey": "YOUR_TOKEN" }
   ],
   "apps-sdk.login": "Make EU1"
   ```
2. Reload window, click the Make icon in the Activity Bar.
3. Open the app from the tree; files appear as temp files synced to Make.

The extension is a remote editor — it does NOT push the local `./`
folder, it edits files stored on Make's servers. Use the `publish.py` script
above for "push local folder up" semantics.

### 3. Make Developer Hub (web UI)

Manual paste, file by file. Works without any local tooling. Useful for
inspecting what's currently deployed.

1. Open <https://eu1.make.com> (or your zone) → Profile → enable Developer mode.
2. **Custom Apps** in the left nav → **Create a new app** → fill in
   name/label/theme from `metadata.json`.
3. Paste `base.imljson` into the **Base** tab.
4. Create the connection, paste each file from `connections/api-key/`.
5. For each module under `modules/`, create a module of the correct type
   (typeId 4 = Action, 9 = Search) and paste each `.imljson` into the
   matching tab.

## Testing checklist

Before publishing, verify in a Make scenario:

- [ ] Create connection — succeeds, fails clearly with bad key (401).
- [ ] `Extract a URL (Sync)` — happy path on `https://example.com`.
- [ ] `Extract a URL (Async)` → `Get an Extraction Job` chain.
- [ ] `Extract a URL (Wait for Completion)` — finishes within budget.
- [ ] `List Extraction Jobs` — pagination iterates all pages.
- [ ] `Start a Crawl` → `Get Crawl Status` → `Cancel a Crawl` lifecycle.
- [ ] `Start a Batch` → `Get Batch Status` lifecycle.
- [ ] `Map URLs from a Site` — emits a bundle per discovered link.
- [ ] `Get Usage Statistics` — date range filter works.
- [ ] A 401 / 402 / 422 / 429 from the API maps to the right Make error type
      (see `base.imljson::response.error.type`).

## What is intentionally not included

- **Webhooks (`/v1/webhooks/*`)** — out of scope for this pass.
- **Health endpoint** — internal-only, no scenario value.
- **Job-result download endpoints / signed URLs** — none exist on the API
  surface today; add when the API does.
