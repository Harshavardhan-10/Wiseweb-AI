"""Optional browser-based rendering (Playwright).

Used ONLY where real browser rendering is required (e.g. screenshot capture
for UX analysis). The module is import-safe without Playwright installed;
each call site must guard with ``BrowserRenderer.available``.

Never used for bulk crawling.
"""

import logging
from dataclasses import dataclass, field

from app.config.settings import settings

logger = logging.getLogger("wisewebai.crawler.browser")

try:  # pragma: no cover - depends on optional system packages
    from playwright.async_api import async_playwright  # type: ignore
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PLAYWRIGHT_AVAILABLE = False


@dataclass
class BrowserSnapshot:
    url: str
    screenshot_png: bytes | None = None
    rendered_text: str = ""
    rendered_title: str | None = None
    measured: dict = field(default_factory=dict)
    error: str | None = None


class BrowserRenderer:
    available = _PLAYWRIGHT_AVAILABLE

    @classmethod
    async def capture(
        cls,
        url: str,
        screenshot: bool = True,
        width: int = 1366,
        height: int = 900,
        wait_ms: int = 2500,
    ) -> BrowserSnapshot:
        """Render a single URL in a headless browser.

        Disabled by default (``WISEWEB_AI_BROWSER_ENABLED=false``) because
        Playwright browsers are an optional dependency.
        """
        if not cls.available:
            return BrowserSnapshot(url=url, error="Playwright is not installed.")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = await browser.new_page(viewport={"width": width, "height": height})
                await page.goto(url, wait_until="load", timeout=settings.crawler_timeout * 1000)
                await page.wait_for_timeout(wait_ms)
                png = await page.screenshot(type="png", full_page=False) if screenshot else None
                text = await page.evaluate("document.body ? document.body.innerText : ''")
                title = await page.title()
                return BrowserSnapshot(
                    url=url,
                    screenshot_png=png,
                    rendered_text=(text or "")[:30000],
                    rendered_title=title,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("browser capture failed for %s: %s", url, exc)
                return BrowserSnapshot(url=url, error=str(exc))
            finally:
                await browser.close()
