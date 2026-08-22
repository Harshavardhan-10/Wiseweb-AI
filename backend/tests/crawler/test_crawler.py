"""Crawler integration tests against a local HTTP server (allow_internal)."""

import asyncio
import gzip
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.crawler.crawler import Crawler
from app.crawler.page_fetcher import PageFetcher

INDEX_HTML = """<!doctype html>
<html>
<head><title>Test Site</title></head>
<body>
  <h1>Welcome</h1>
  <a href="/about.html">About</a>
  <a href="/missing.html">Missing</a>
  <a href="https://external.example.com/">External</a>
  <img src="/assets/logo.png" alt="logo">
  <script src="/assets/app.js"></script>
  <script>var inline = "x";</script>
</body>
</html>"""

ABOUT_HTML = """<!doctype html>
<html>
<head><title>About</title></head>
<body>
  <h1>About us</h1>
  <a href="/index.html">Home</a>
</body>
</html>"""

ROBOTS = """User-agent: *
Disallow: /private/
"""


GZIP_HTML = "<!doctype html><html><head><title>Gzip Page</title></head><body><h1>compressed</h1></body></html>"
GZIP_BODY = gzip.compress(GZIP_HTML.encode())


class SiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        routes = {
            "/": (200, "text/html; charset=utf-8", INDEX_HTML),
            "/index.html": (200, "text/html; charset=utf-8", INDEX_HTML),
            "/about.html": (200, "text/html; charset=utf-8", ABOUT_HTML),
            "/robots.txt": (200, "text/plain; charset=utf-8", ROBOTS),
            "/private/secret.html": (200, "text/html; charset=utf-8", "<h1>secret</h1>"),
            "/gzip.html": (200, "text/html; charset=utf-8", GZIP_HTML, GZIP_BODY),
        }
        if self.path in routes:
            entry = routes[self.path]
            code, content_type, text = entry[0], entry[1], entry[2]
            wire_body = GZIP_BODY if len(entry) > 3 else text.encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(wire_body)))
            if len(entry) > 3:
                self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            self.wfile.write(wire_body)
            return
        if self.path.startswith("/assets/"):
            body = b""
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", "1234")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_HEAD = do_GET  # noqa: N815

    def log_message(self, fmt, *args):  # noqa: ARG002
        pass


@pytest.fixture(scope="module")
def demo_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), SiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_ssrf_blocks_localhost_crawl():
    result = asyncio.run(Crawler(allow_internal=False).crawl("http://127.0.0.1:9/"))
    assert result.error is not None
    assert result.pages == []


def test_crawls_pages_links_and_resources(demo_server):
    result = asyncio.run(Crawler(allow_internal=True, respect_robots=False).crawl(demo_server + "/"))
    assert result.error is None
    urls = {p.url for p in result.pages}
    assert demo_server + "/" in urls
    assert demo_server + "/index.html" in urls
    assert demo_server + "/about.html" in urls

    about = next(p for p in result.pages if p.url.endswith("/about.html"))
    assert about.title == "About"


def test_missing_page_and_broken_links_recorded(demo_server):
    result = asyncio.run(Crawler(allow_internal=True, respect_robots=False).crawl(demo_server + "/"))
    broken = [p for p in result.pages if p.status_code == 404]
    assert any(p.url.endswith("/missing.html") for p in broken)


def test_resources_probed(demo_server):
    result = asyncio.run(Crawler(allow_internal=True, respect_robots=False).crawl(demo_server + "/"))
    resources = result.all_resources
    image = next(r for r in resources if r.url.endswith("/assets/logo.png"))
    assert image.status_code == 200
    assert image.size_bytes == 1234
    script = next(r for r in resources if r.url.endswith("/assets/app.js"))
    assert script.resource_type == "JS"


def test_robots_respected(demo_server):
    # robots.txt disallows /private/ — that page must not be crawled.
    result = asyncio.run(Crawler(allow_internal=True, respect_robots=True).crawl(demo_server + "/"))
    urls = {p.url for p in result.pages}
    assert not any("/private/" in u for u in urls)


def test_robots_disallow_base_url(demo_server):
    result = asyncio.run(
        Crawler(allow_internal=True, respect_robots=True).crawl(demo_server + "/private/secret.html")
    )
    assert result.robots_disallowed is True


def test_gzip_encoded_page_is_not_decompressed_twice(demo_server):
    # Regression: Google serves gzip/br. The fetcher's stream path previously
    # rebuilt the response with the original Content-Encoding header, causing
    # httpx to decompress the already-decoded body (DecodingError).
    resp = asyncio.run(
        PageFetcher(timeout=5.0, delay=0, allow_internal=True).fetch_html(
            demo_server + "/gzip.html"
        )
    )
    assert resp is not None
    assert resp.status_code == 200
    assert "compressed" in resp.text
    assert resp.headers.get("content-encoding") is None


def test_gzip_page_crawled_without_error(demo_server):
    result = asyncio.run(
        Crawler(allow_internal=True, respect_robots=False, delay=0).crawl(
            demo_server + "/gzip.html"
        )
    )
    assert result.error is None
    pages = {p.url for p in result.pages}
    assert demo_server + "/gzip.html" in pages
