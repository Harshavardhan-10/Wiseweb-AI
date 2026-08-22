"""The safe crawler.

Flow:
1. Validate the base URL (structural + SSRF/DNS).
2. Fetch /robots.txt and honor it.
3. BFS crawl with depth + page caps and per-URL SSRF validation.
4. Parse HTML, extract internal links and resources.
5. Deduplicate; continue until the queue is exhausted or limits hit.

Only HTTP GET requests, bounded concurrency, configurable delay.
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone

import httpx

from app.config.settings import settings
from app.core.exceptions import ValidationError
from app.crawler.models import CrawledPage, CrawlResult, CrawledResource
from app.crawler.page_fetcher import PageFetcher
from app.crawler.parser import parse_html
from app.crawler.robots import RobotsRules, parse_robots_txt
from app.crawler.url_validator import validate_crawl_url
from app.security.ssrf import validate_url_target
from app.utils.urls import hostname_of, join_url

logger = logging.getLogger("wisewebai.crawler")

MAX_PAGES = 200
MAX_DEPTH = 5
RESOURCE_PROBE_TIMEOUT = 8.0


class Crawler:
    def __init__(
        self,
        max_pages: int | None = None,
        max_depth: int | None = None,
        timeout: float | None = None,
        concurrency: int | None = None,
        delay: float | None = None,
        respect_robots: bool = True,
        allow_internal: bool = False,
    ):
        # Hard caps: never exceed the configured absolute maximum.
        self.max_pages = min(max_pages or settings.crawler_max_pages, MAX_PAGES)
        self.max_depth = min(max_depth or settings.crawler_max_depth, MAX_DEPTH)
        self.respect_robots = respect_robots
        self.allow_internal = allow_internal
        self.fetcher = PageFetcher(
            timeout=timeout, concurrency=concurrency, delay=delay,
            allow_internal=allow_internal,
        )
        self._robots: RobotsRules | None = None
        self._robots_fetched = False
        self._base_hostname = ""

    async def crawl(self, base_url: str) -> CrawlResult:
        started = datetime.now(timezone.utc)
        result = CrawlResult(base_url=base_url, started_at=started)
        try:
            base_url = validate_crawl_url(base_url, allow_internal=self.allow_internal)
        except ValidationError as exc:
            result.error = str(exc)
            result.completed_at = datetime.now(timezone.utc)
            return result

        self._base_hostname = hostname_of(base_url)

        if self.respect_robots:
            await self._load_robots(base_url)
            if self._robots and not self._robots.can_fetch(base_url):
                result.robots_disallowed = True
                result.error = "robots.txt disallows crawling this URL."
                result.completed_at = datetime.now(timezone.utc)
                await self.fetcher.close()
                return result

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        queue.append((base_url, 0))

        # Probe the first page synchronously to fail fast on unreachable sites.
        first = await self._crawl_page(base_url, 0)
        if first is None:
            result.error = "Could not fetch the base URL."
            result.completed_at = datetime.now(timezone.utc)
            await self.fetcher.close()
            return result
        result.pages.append(first)
        visited.add(base_url)
        self._enqueue_links(first, queue)

        while queue and len(result.pages) < self.max_pages:
            url, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            page = await self._crawl_page(url, depth)
            if page is not None:
                result.pages.append(page)
                self._enqueue_links(page, queue)

        result.completed_at = datetime.now(timezone.utc)
        await self.fetcher.close()
        logger.info(
            "crawl complete: %d pages for %s", len(result.pages), base_url,
            extra={"pages": len(result.pages)},
        )
        return result

    def _enqueue_links(self, page: CrawledPage, queue: deque[tuple[str, int]]) -> None:
        if page.depth >= self.max_depth:
            return
        for link in page.internal_links:
            if not self.allow_internal:
                try:
                    validate_url_target(link)
                except ValidationError:
                    continue
            if self._robots and not self._robots.can_fetch(link):
                continue
            queue.append((link, page.depth + 1))

    async def _load_robots(self, base_url: str) -> None:
        if self._robots_fetched:
            return
        self._robots_fetched = True
        robots_url = join_url(base_url, "/robots.txt")
        try:
            response = await self.fetcher.fetch_html(robots_url)
        except Exception:  # noqa: BLE001
            return
        if response is None or response.status_code >= 400:
            return
        body = response.text[:512_000]
        self._robots = parse_robots_txt(body, base_url)

    async def _crawl_page(self, url: str, depth: int) -> CrawledPage | None:
        if self._robots and not self._robots.can_fetch(url):
            page = CrawledPage(url=url, depth=depth, robots_blocked=True)
            page.internal_links = []
            page.resources = []
            return None

        try:
            if not self.allow_internal:
                validate_url_target(url)
        except ValidationError as exc:
            logger.debug("skipping blocked URL %s: %s", url, exc)
            return None

        start = time.monotonic()
        response = await self.fetcher.fetch_html(url)
        if response is None:
            return None
        load_time = time.monotonic() - start

        headers = {k.lower(): v for k, v in response.headers.items()}
        cookies = [
            {"name": c.name, "value": c.value[:500], "domain": c.domain,
             "path": c.path, "secure": c.secure, "httponly": c.has_nonstandard_attr("HttpOnly")}
            for c in response.cookies.jar
        ]

        final_url = str(response.url)
        content_type = response.headers.get("content-type")

        parsed = parse_html(response.text, final_url) if "html" in (content_type or "").lower() else None

        page = CrawledPage(
            url=url,
            status_code=response.status_code,
            content_type=content_type,
            final_url=final_url,
            depth=depth,
            html_size=len(response.content),
            load_time=load_time,
            headers=headers,
            cookies=cookies,
        )

        if parsed:
            page.title = parsed.title()
            page.meta_description = parsed.meta_description()
            page.canonical_url = parsed.canonical_url()
            page.internal_links = parsed.internal_links(self._base_hostname)
            page.text = parsed.visible_text(response.text)
            page.word_count = parsed.count_words(page.text)
            page.html = response.text[:300_000]

            for r in parsed.resources(self._base_hostname):
                page.resources.append(
                    CrawledResource(
                        url=r["url"], resource_type=r["resource_type"],
                        is_external=r["is_external"], domain=r["domain"],
                    )
                )
            # Attach small inline scripts for the technology detector.
            inline = parsed.inline_scripts(final_url)
            for script_url, content in inline[:20]:
                page.resources.append(
                    CrawledResource(
                        url=script_url, resource_type="JS", is_external=False,
                        domain=self._base_hostname, inline_content=content,
                    )
                )
            await self._probe_resources(page)

        return page

    async def _probe_resources(self, page: CrawledPage) -> None:
        """Probe resource URLs with HEAD requests (GET fallback), bounded."""
        probeable = [r for r in page.resources if r.inline_content is None]
        # Probe at most N resources per page to bound crawl cost.
        probeable = probeable[:60]

        async def probe(resource: CrawledResource) -> None:
            if not self.allow_internal:
                try:
                    validate_url_target(resource.url)
                except ValidationError:
                    return
            start = time.monotonic()
            response = await self.fetcher.fetch(resource.url, method="HEAD")
            if response is not None and response.status_code not in (405, 501):
                resource.status_code = response.status_code
                length = response.headers.get("content-length")
                if length and length.isdigit():
                    resource.size_bytes = int(length)
                resource.mime_type = response.headers.get("content-type")
                resource.load_time = time.monotonic() - start
                return
            # HEAD unsupported: GET but only read headers, then abort body.
            response = await self.fetcher.fetch(resource.url, method="GET")
            if response is not None:
                resource.status_code = response.status_code
                length = response.headers.get("content-length")
                if length and length.isdigit():
                    resource.size_bytes = int(length)
                resource.mime_type = response.headers.get("content-type")
                resource.load_time = time.monotonic() - start

        await asyncio.gather(*(probe(r) for r in probeable))


async def crawl_website(base_url: str, **kwargs) -> CrawlResult:
    crawler = Crawler(**kwargs)
    return await crawler.crawl(base_url)
