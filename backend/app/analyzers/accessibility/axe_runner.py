"""axe-core integration through Playwright (optional).

axe-core is loaded from the official CDN inside the rendered page and runs
read-only checks. This is disabled by default because it requires the
optional Playwright browsers and the axe source to be available.
"""

import logging

from app.config.settings import settings

logger = logging.getLogger("wisewebai.analyzers.axe")

AXE_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"


async def run_axe(page_html: str, page_url: str) -> list[dict]:
    """Run axe-core against a rendered page.

    Returns a list of violation dicts, or [] when unavailable/disabled.
    """
    if not getattr(settings, "axe_enabled", False):
        return []
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        logger.info("axe-core unavailable: playwright not installed")
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(page_html)
            await page.add_script_tag(url=AXE_CDN_URL)
            results = await page.evaluate("() => axe.run().then(r => r.violations)")
            return results or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("axe run failed for %s: %s", page_url, exc)
            return []
        finally:
            await browser.close()
