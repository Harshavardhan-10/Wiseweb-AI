# Crawler

The crawler (`app/crawler/`) is deliberately **passive**: it only requests
public resources the way a browser would, never submits forms, never
authenticates, and never touches anything behind the site's `robots.txt`
rules.

## Components

```
url_validator.py   Scheme/host/credential checks + canonical URL normalization
ssrf.py            DNS + IP validation and the redirect guard (see security.md)
page_fetcher.py    httpx streaming fetcher: timeouts, size cap, semaphore, delay
robots.py          robots.txt fetch + path matching (with cache)
parser.py          BeautifulSoup: links, resources, metadata extraction
crawler.py         BFS orchestration: queue, depth, link extraction, probing
browser.py         Optional Playwright-based fetch (browser_enabled=False)
```

## URL handling

- **Normalization** (`app/utils/urls.py`): lowercase scheme/host, strip
  fragments, strip default ports, remove trailing slash on the root path,
  reject non-http(s) schemes and URLs with embedded credentials.
- **Scope:** only same-registrable-domain links are followed; external links
  are recorded but not crawled. Link `<a>` targets, canonical tags, and
  redirects are all re-validated.
- **Robots:** `robots.txt` is fetched once per domain and respected via
  path-matching rules for the crawler's user agent (`WisewebAI-Bot/1.0`). A
  disallowed base URL aborts the crawl with `robots_disallowed`.

## Fetching

- **Transport:** `httpx.AsyncClient` with a custom `RedirectGuardTransport`
  that validates every redirect hop against the SSRF policy (see
  security.md) before following it.
- **Streaming:** responses are streamed (httpx 0.28 semantics — manual
  `aiter_bytes()` + `aclose()`) and capped at
  `CRAWLER_MAX_PAGE_BYTES` (default 5 MB).
- **Politeness:** bounded concurrency (default 4) and an inter-request
  delay (default 0.25 s), all configurable via settings.
- **Timeouts:** connect/read/write timeouts from `CRAWLER_TIMEOUT` (15 s).
- **Resources:** discovered scripts/styles/images/etc. are probed with
  HEAD-style requests to capture `size_bytes`, `status_code`, and
  `load_time`; external resources are recorded but never followed.

## Safety caps (hard limits)

- `crawl_depth` is clamped to 1–5, `page_limit` to 1–200 at the API layer
  **and** in the crawler itself — config can never exceed these absolute
  caps.
- Page HTML stored in memory is truncated to 300 KB per page before
  analysis.
- The crawler will never attempt a private/loopback/link-local/cloud-metadata
  target (see security.md).

## Error handling

- Failed fetches (network errors, 4xx/5xx) are recorded per-page; the crawl
  continues.
- A completely failed crawl (no pages + an error) marks the scan `FAILED`
  with a short error message (truncated to 2000 chars).

## Tests

`backend/tests/crawler/` runs against a local `ThreadingHTTPServer` and
covers normalization, SSRF blocking, page/resource discovery, 404 handling,
robots compliance, and resource probing.
