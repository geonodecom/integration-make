![Geonode for Make.com: Web Scraping & Data Extraction](assets/banner.svg)

# Geonode for Make.com: Web Scraping & Data Extraction

Give your Make.com agents and scenarios web content for research and automation. Extract pages, crawl sites, discover URLs and run batches, then pass results to AI, spreadsheet or CRM modules for summaries and record updates.

**[Try Geonode for free](https://app.geonode.com/sign-up)**

[Integrations page](https://geonode.com/integrations/integration-make) · [Geonode API docs](https://docs.geonode.com/docs/scraper-api) · [View source on GitHub](https://github.com/geonodecom/integration-make) · [Complete guide](docs/guide.md)

**Private app, access by request.** The existing Geonode app is deployed in Make's US2 zone as `scraper-api-production`. There is no public Make marketplace listing. This repository contains its Make Apps SDK source, not an npm or Python package.

<!-- BEGIN README NAV -->
[Set up the Make.com connector](#set-up-the-makecom-connector) · [Example: website content → Google Sheets](#example-website-content--google-sheets) · [All 15 Make modules](#all-15-make-modules) · [Common questions](#common-questions)
<!-- END README NAV -->

## Workflow ideas

- **Send website content to a spreadsheet.** Read a URL from your scenario, extract Markdown, then map the source URL and content into a Google Sheets row using a separate Sheets module.
- **Prepare pages for an AI summary.** Extract a page as Markdown, pass it to your chosen AI module, and save its summary with the source URL.
- **Refresh a collection of pages.** Submit a URL list as a batch, retain its job ID, and retrieve results before updating downstream records.

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

## Develop locally

Requires Python 3.10 or newer. The source uses JSON and IMLJSON; no dependency installation is needed.

```sh
python3 scripts/test_client_header.py
```

Edit shared request behavior in `base.imljson`, connection fields in `connections/api-key/`, and operation definitions in `modules/`. Each module declares metadata, input fields, request mapping, output fields and samples. The [full guide](docs/guide.md) describes the format and live scenario checks.

The publisher is available for maintainers as `scripts/publish.py`. Its default template name (`scraper-api`) and zone (`eu1`) do **not** identify the deployed production app. Existing CI supplies the real app name, US2 zone, and relevant team settings. Do not run a publish command as part of local testing.

## Source and releases

Connection and module keys and template metadata are kept stable. A change to the app definition merged to `main` is published to the existing private app by the `Publish` workflow.

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

MIT licensed. See [LICENSE](LICENSE).

**[Try Geonode for free](https://app.geonode.com/sign-up)**
