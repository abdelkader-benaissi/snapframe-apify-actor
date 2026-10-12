# Snapframe — Website Screenshots & PDFs

Capture pixel-perfect website screenshots (**PNG/JPEG**) and print-ready **PDF documents** in a real Chromium browser. Built by the team behind the [Snapframe API](https://snapframe.mooo.com/demo/).

Feed it one or more URLs and get back files plus a clean dataset row per page: direct download link, file size, page title, HTTP status and load time. Batch up to 50 URLs per run.

## What it does

- **Screenshots** in PNG or JPEG — viewport or full-page, with device presets (desktop, laptop, tablet, mobile) or your own custom dimensions and scale factor.
- **PDFs** with paper size (A4/Letter/Legal), orientation, margins, background printing, and optional header/footer HTML templates with page numbers.
- **First-class Arabic/RTL rendering** — proper Arabic fonts ship in the image, so Arabic pages (invoices, articles, dashboards) render with real glyphs, not boxes.
- **Batch captures** — up to 50 URLs per run, each stored as its own file with a dataset record. One bad URL never kills the batch.
- **Authenticated pages** — pass custom request headers and cookies to capture pages behind a login.
- **Safe by default** — only public `http(s)` URLs are loaded; private, loopback and internal addresses are blocked.

## Input

| Field | Description |
|---|---|
| `urls` | URLs to capture (1–50, required) |
| `outputFormat` | `png`, `jpeg` or `pdf` |
| `devicePreset` | `desktop` (1920×1080), `laptop`, `tablet`, `mobile`, or `custom` |
| `viewportWidth` / `viewportHeight` / `deviceScaleFactor` | Used when the preset is `custom` |
| `fullPage` | Capture the whole scrollable page (images only; PDFs are always full) |
| `waitUntil` | `load`, `domcontentloaded`, `networkidle` or `commit` |
| `delayMs` | Extra pause after load for animations/lazy images |
| `timeoutMs` | Per-page load timeout |
| `jpegQuality` | JPEG quality 10–100 |
| `pdfFormat` / `pdfLandscape` / `pdfMargin` / `printBackground` | PDF layout |
| `displayHeaderFooter` / `headerTemplate` / `footerTemplate` | PDF header/footer HTML (`<span class="pageNumber">` supported) |
| `headers` | Extra HTTP headers, e.g. `{"Authorization": "Bearer ..."}` |
| `cookies` | Cookies injected before capture (each needs `name`, `value` and `domain` or `url`) |

Example input:

```json
{
  "urls": ["https://example.com", "https://news.ycombinator.com"],
  "outputFormat": "png",
  "devicePreset": "desktop",
  "fullPage": true,
  "waitUntil": "networkidle",
  "delayMs": 1000
}
```

PDF example:

```json
{
  "urls": ["https://example.com"],
  "outputFormat": "pdf",
  "pdfFormat": "A4",
  "pdfMargin": "0.4in",
  "printBackground": true,
  "displayHeaderFooter": true,
  "footerTemplate": "<div style=\"font-size:8px;width:100%;text-align:center;\">Page <span class=\"pageNumber\"></span> of <span class=\"totalPages\"></span></div>"
}
```

## Output

- **Files** — each capture is saved in the run's key-value store (`0000-example-com.png`, …) and stays downloadable via its direct URL.
- **Dataset** — one row per URL: `url`, `ok`, `outputFormat`, `fileName`, `fileUrl`, `bytes`, `title`, `statusCode`, `loadTimeMs`, and `reason` when a capture fails.
- **OUTPUT** — run summary: total / succeeded / failed counts and format.

## Pricing

Pay per event — you are charged only for successful captures:

| Event | Price |
|---|---|
| Screenshot captured (PNG/JPEG) | $0.003 |
| PDF captured | $0.005 |

Platform compute costs are passed through to the run (standard Apify compute units), so the event price is the whole story. Failed or blocked URLs are never charged.

## API examples

```bash
curl -X POST "https://api.apify.com/v2/acts/<your-username>~snapframe-screenshot-pdf/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"], "outputFormat": "pdf"}'
```

```python
from apify_client import ApifyClient

client = ApifyClient("YOUR_APIFY_TOKEN")
run = client.actor("<your-username>/snapframe-screenshot-pdf").call({
    "urls": ["https://example.com"],
    "outputFormat": "png",
    "devicePreset": "mobile",
})
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item["url"], "->", item["fileUrl"])
```

AI agents can also discover and call this actor through the Apify MCP server — the input schema is written to be agent-friendly.

## Limits

- 50 URLs per run; schedule runs for larger batches.
- Pages behind logins need the `headers`/`cookies` inputs — there is no interactive login.
- Sites with aggressive bot protection may serve a challenge page; that is captured faithfully as what an anonymous visitor sees.
- Very long pages (tens of thousands of pixels) can exceed browser capture limits — use a tall custom viewport with `fullPage: false` for those.

## Support

Issues: open one on the actor page. This actor is maintained by Snapframe — the same capture engine powers our hosted API.
