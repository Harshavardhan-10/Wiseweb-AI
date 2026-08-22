"""Rule-based technology detection.

Sources of evidence: headers, cookies, HTML signatures, script names,
meta tags, resource URLs, framework-specific markers.

Confidence reflects evidence strength. Weak signals never claim certainty.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable

from app.analyzers.base import TechnologyDetection
from app.crawler.models import CrawledPage

logger = logging.getLogger("wisewebai.analyzers.technology")


@dataclass
class DetectionContext:
    pages: list[CrawledPage]
    headers: dict[str, str]
    cookies: list[dict]
    all_html: str = ""
    all_scripts: list[str] = field(default_factory=list)
    all_meta: list[tuple[str, str, str]] = field(default_factory=list)
    all_urls: list[str] = field(default_factory=list)

    @classmethod
    def build(cls, pages: list[CrawledPage]) -> "DetectionContext":
        headers: dict[str, str] = {}
        cookies: list[dict] = []
        html_chunks: list[str] = []
        scripts: list[str] = []
        meta: list[tuple[str, str, str]] = []
        urls: list[str] = []
        for page in pages:
            headers.update(page.headers)
            cookies.extend(page.cookies)
            if page.html:
                html_chunks.append(page.html[:200_000])
            for r in page.resources:
                urls.append(r.url)
                if r.resource_type == "JS":
                    scripts.append(r.url)
        return cls(
            pages=pages, headers=headers, cookies=cookies,
            all_html="\n".join(html_chunks), all_scripts=scripts,
            all_meta=[m for p in pages if p.html for m in _meta_of(p)],
            all_urls=urls,
        )


def _meta_of(page: CrawledPage) -> list[tuple[str, str, str]]:
    from app.crawler.parser import parse_html
    parsed = parse_html(page.html, page.url)
    return parsed.meta_tags() if parsed else []


def _h(headers: dict[str, str], key: str) -> str:
    for k, v in headers.items():
        if k.lower() == key.lower():
            return v
    return ""


def _has_cookie(cookies: list[dict], prefix: str) -> bool:
    return any(c.get("name", "").lower().startswith(prefix.lower()) for c in cookies)


# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------

def _match_meta(ctx: DetectionContext, name: str, value_contains: str) -> bool:
    for n, c, _p in ctx.all_meta:
        if n.lower() == name.lower() and value_contains.lower() in c.lower():
            return True
    return False


def _detect_wordpress(ctx: DetectionContext) -> str | None:
    html = ctx.all_html
    if "/wp-content/" in html or "/wp-includes/" in html or 'wp-emoji' in html:
        return "wp-content or wp-includes references"
    if _has_cookie(ctx.cookies, "wp-"):
        return "wp-* cookie"
    if "id=\"wpcontent\"" in html or 'class="wp-embed' in html:
        return "wordpress markup"
    return None


def _detect_nextjs(ctx: DetectionContext) -> str | None:
    if "__NEXT_DATA__" in ctx.all_html or "/_next/" in ctx.all_html:
        return "next.js markers"
    return None


def _detect_nuxt(ctx: DetectionContext) -> str | None:
    if "__NUXT__" in ctx.all_html or "_nuxt" in ctx.all_html:
        return "nuxt markers"
    return None


def _detect_react(ctx: DetectionContext) -> str | None:
    if "data-reactroot" in ctx.all_html or 'id="root"' in ctx.all_html:
        return "react root markup"
    if any("react" in s.lower() for s in ctx.all_scripts):
        return "react script"
    return None


def _detect_vue(ctx: DetectionContext) -> str | None:
    if "__VUE__" in ctx.all_html or "data-v-" in ctx.all_html:
        return "vue markers"
    return None


def _detect_jquery(ctx: DetectionContext) -> str | None:
    if any("jquery" in s.lower() for s in ctx.all_scripts):
        return "jquery script"
    return None


def _detect_bootstrap(ctx: DetectionContext) -> str | None:
    if any("bootstrap" in s.lower() for s in ctx.all_scripts):
        return "bootstrap script"
    if "bootstrap" in ctx.all_html.lower():
        return "bootstrap markup"
    return None


def _detect_tailwind(ctx: DetectionContext) -> str | None:
    if any("tailwind" in s.lower() for s in ctx.all_scripts):
        return "tailwind script"
    if "class=\"flex items-center" in ctx.all_html or "class=\"grid grid-cols" in ctx.all_html:
        return "tailwind-style classes"
    return None


def _detect_angular(ctx: DetectionContext) -> str | None:
    if "ng-app" in ctx.all_html or "ng-version" in ctx.all_html:
        return "angular markers"
    if any("angular" in s.lower() for s in ctx.all_scripts):
        return "angular script"
    return None


def _detect_google_analytics(ctx: DetectionContext) -> str | None:
    if any("gtag/js" in s or "googletagmanager" in s for s in ctx.all_scripts):
        return "gtag script"
    if "google-analytics" in ctx.all_html or "_ga" in _h(ctx.headers, "set-cookie"):
        return "analytics reference"
    if _has_cookie(ctx.cookies, "_ga"):
        return "ga cookie"
    return None


def _detect_cloudflare(ctx: DetectionContext) -> str | None:
    server = _h(ctx.headers, "server")
    if "cloudflare" in server.lower() or "cf-ray" in ctx.headers:
        return "cloudflare server header"
    return None


def _detect_nginx(ctx: DetectionContext) -> str | None:
    if "nginx" in _h(ctx.headers, "server").lower():
        return "nginx server header"
    return None


def _detect_apache(ctx: DetectionContext) -> str | None:
    if "apache" in _h(ctx.headers, "server").lower():
        return "apache server header"
    return None


def _detect_php(ctx: DetectionContext) -> str | None:
    if _has_cookie(ctx.cookies, "phpsessid"):
        return "php session cookie"
    if "x-powered-by" in ctx.headers and "php" in _h(ctx.headers, "x-powered-by").lower():
        return "x-powered-by header"
    return None


def _detect_django(ctx: DetectionContext) -> str | None:
    if _has_cookie(ctx.cookies, "csrftoken"):
        return "django csrf cookie"
    if "django" in _h(ctx.headers, "server").lower():
        return "server header"
    return None


def _detect_flask(ctx: DetectionContext) -> str | None:
    if "werkzeug" in _h(ctx.headers, "server").lower():
        return "werkzeug server header"
    return None


def _detect_express(ctx: DetectionContext) -> str | None:
    if "express" in _h(ctx.headers, "x-powered-by").lower():
        return "x-powered-by header"
    return None


def _detect_shopify(ctx: DetectionContext) -> str | None:
    if "/cdn/shop/" in ctx.all_html or "shopify" in ctx.all_html.lower():
        return "shopify markup"
    if _h(ctx.headers, "x-shopid"):
        return "shopify header"
    return None


def _detect_ghost(ctx: DetectionContext) -> str | None:
    if "ghost" in _h(ctx.headers, "server").lower():
        return "ghost server header"
    if "ghost-search" in ctx.all_html or "content=\"Ghost\"" in ctx.all_html:
        return "ghost markup"
    return None


def _detect_aspnet(ctx: DetectionContext) -> str | None:
    if "aspnet" in ctx.headers or _h(ctx.headers, "x-aspnet-version"):
        return "asp.net headers"
    if _has_cookie(ctx.cookies, "asp.net_sessionid"):
        return "asp.net session cookie"
    return None


def _detect_cloudfront(ctx: DetectionContext) -> str | None:
    if "cloudfront" in _h(ctx.headers, "via").lower() or "cloudfront" in ctx.headers.get("server", "").lower():
        return "cloudfront headers"
    return None


def _detect_google_fonts(ctx: DetectionContext) -> str | None:
    if any("fonts.googleapis.com" in u or "fonts.gstatic.com" in u for u in ctx.all_urls):
        return "google fonts resource"
    return None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DETECTORS: list[tuple[str, str, float, Callable[[DetectionContext], str | None]]] = [
    ("WordPress", "CMS", 0.85, _detect_wordpress),
    ("Next.js", "Frontend Framework", 0.91, _detect_nextjs),
    ("Nuxt.js", "Frontend Framework", 0.9, _detect_nuxt),
    ("React", "Frontend Framework", 0.7, _detect_react),
    ("Vue.js", "Frontend Framework", 0.7, _detect_vue),
    ("jQuery", "JavaScript Library", 0.9, _detect_jquery),
    ("Bootstrap", "CSS Framework", 0.8, _detect_bootstrap),
    ("Tailwind CSS", "CSS Framework", 0.65, _detect_tailwind),
    ("Angular", "Frontend Framework", 0.75, _detect_angular),
    ("Google Analytics", "Analytics", 0.85, _detect_google_analytics),
    ("Cloudflare", "CDN / Proxy", 0.95, _detect_cloudflare),
    ("Nginx", "Web Server", 1.0, _detect_nginx),
    ("Apache HTTP Server", "Web Server", 1.0, _detect_apache),
    ("PHP", "Backend Language", 0.85, _detect_php),
    ("Django", "Backend Framework", 0.8, _detect_django),
    ("Flask", "Backend Framework", 0.85, _detect_flask),
    ("Express", "Backend Framework", 0.8, _detect_express),
    ("Shopify", "E-commerce Platform", 0.8, _detect_shopify),
    ("Ghost", "CMS", 0.8, _detect_ghost),
    ("ASP.NET", "Backend Framework", 0.8, _detect_aspnet),
    ("Amazon CloudFront", "CDN", 0.9, _detect_cloudfront),
    ("Google Fonts", "Resource CDN", 0.9, _detect_google_fonts),
]


def detect_technologies(
    pages: list[CrawledPage],
    headers: dict[str, str] | None = None,
    cookies: list[dict] | None = None,
) -> list[TechnologyDetection]:
    """Run all detectors and return confident detections."""
    ctx = DetectionContext.build(pages)
    if headers:
        ctx.headers.update(headers)
    if cookies:
        ctx.cookies = cookies

    detections: list[TechnologyDetection] = []
    for name, category, base_confidence, detector in DETECTORS:
        try:
            evidence = detector(ctx)
        except Exception:  # noqa: BLE001
            logger.warning("technology detector %s raised", name, exc_info=True)
            continue
        if not evidence:
            continue
        confidence = base_confidence
        # Strong header-based evidence raises confidence.
        detections.append(
            TechnologyDetection(name=name, category=category, confidence=confidence, evidence=[evidence])
        )

    # De-duplicate by name, keep the strongest evidence.
    seen: dict[str, TechnologyDetection] = {}
    for det in detections:
        existing = seen.get(det.name)
        if existing is None:
            seen[det.name] = det
        else:
            existing.confidence = max(existing.confidence, det.confidence)
            existing.evidence.append(det.evidence[0])
    return list(seen.values())
