"""HTTP page fetching with mandatory SSRF validation on every request."""

import asyncio
import logging
import time
from urllib.parse import urlparse

import httpx

from app.config.settings import settings
from app.core.exceptions import ValidationError
from app.security.ssrf import RedirectGuardTransport, validate_url_target

logger = logging.getLogger("wisewebai.crawler.fetcher")


class PageFetcher:
    """Async HTTP client used for crawling.

    - Every request (including every redirect hop) is DNS + IP validated.
    - Uses a shared httpx.AsyncClient for connection pooling.
    - Low concurrency, configurable delay, hard timeouts.
    """

    def __init__(
        self,
        timeout: float | None = None,
        concurrency: int | None = None,
        delay: float | None = None,
        user_agent: str | None = None,
        allow_internal: bool = False,
    ):
        self.timeout = timeout if timeout is not None else settings.crawler_timeout
        self.concurrency = concurrency or settings.crawler_concurrency
        self.delay = delay if delay is not None else settings.crawler_delay
        self.user_agent = user_agent or settings.crawler_user_agent
        self.allow_internal = allow_internal
        self._semaphore = asyncio.Semaphore(max(1, self.concurrency))
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            transport = RedirectGuardTransport(
                httpx.AsyncHTTPTransport(
                    retries=0,
                    verify=False,  # opportunistic content fetch only
                ),
                allow_internal=self.allow_internal,
            )
            self._client = httpx.AsyncClient(
                transport=transport,
                timeout=httpx.Timeout(self.timeout, connect=8.0),
                follow_redirects=True,
                headers={"User-Agent": self.user_agent, "Accept": "*/*"},
                max_redirects=10,
            )
        return self._client

    async def fetch(
        self, url: str, method: str = "GET", stream: bool = False
    ) -> httpx.Response | None:
        """Fetch a URL with concurrency + delay limiting.

        Returns None if the URL is not fetchable (validation error, network
        failure, or server error).
        """
        if not self.allow_internal:
            try:
                validate_url_target(url)
            except ValidationError as exc:
                logger.info("blocked URL %s: %s", url, exc)
                return None

        async with self._semaphore:
            if self.delay:
                await asyncio.sleep(self.delay)
            client = await self._get_client()
            start = time.monotonic()
            try:
                if stream:
                    return await client.stream(method, url)
                return await client.request(method, url)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                logger.debug("fetch failed for %s: %s", url, exc)
                return None
            finally:
                elapsed = time.monotonic() - start
                logger.debug(
                    "fetched %s in %.2fs", url, elapsed, extra={"url": url}
                )

    async def fetch_html(self, url: str) -> httpx.Response | None:
        """Fetch a page as HTML (bounded by max page bytes)."""
        if not self.allow_internal:
            try:
                validate_url_target(url)
            except ValidationError as exc:
                logger.info("blocked URL %s: %s", url, exc)
                return None

        async with self._semaphore:
            if self.delay:
                await asyncio.sleep(self.delay)
            client = await self._get_client()
            try:
                request = client.build_request("GET", url)
                request.headers["Accept"] = "text/html,application/xhtml+xml"
                response = await client.send(request, stream=True)
                try:
                    total = 0
                    chunks: list[bytes] = []
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > settings.crawler_max_page_bytes:
                            logger.info(
                                "page too large, truncated: %s (%d bytes)",
                                url, total,
                            )
                            break
                        chunks.append(chunk)
                    response_content = b"".join(chunks)
                    # aiter_bytes() already returns decoded bytes, but the
                    # original headers still advertise Content-Encoding (e.g.
                    # gzip/br). Strip it (and Content-Length, which no longer
                    # matches) so the rebuilt response is not decompressed again.
                    headers = response.headers
                    headers.pop("content-encoding", None)
                    headers.pop("content-length", None)
                    # Rebuild a plain response so callers get .status_code/.headers/.text
                    return httpx.Response(
                        status_code=response.status_code,
                        headers=headers,
                        content=response_content,
                        request=request,
                    )
                finally:
                    await response.aclose()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                logger.debug("fetch failed for %s: %s", url, exc)
                return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    def is_html_response(self, response: httpx.Response) -> bool:
        ctype = response.headers.get("content-type", "")
        return "html" in ctype.lower()
