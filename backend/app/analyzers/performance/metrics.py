"""Performance metrics aggregation.

Core Web Vitals are ONLY reported when actually measured (browser-based).
Without browser measurement, values are returned as "Not available".
"""


def summarize_metrics(resources, pages) -> dict:
    total_size = sum(r.size_bytes or 0 for r in resources)
    js_size = sum(r.size_bytes or 0 for r in resources if r.resource_type == "JS")
    css_size = sum(r.size_bytes or 0 for r in resources if r.resource_type == "CSS")
    image_size = sum(r.size_bytes or 0 for r in resources if r.resource_type == "IMAGE")
    font_size = sum(r.size_bytes or 0 for r in resources if r.resource_type == "FONT")
    other_size = total_size - js_size - css_size - image_size - font_size
    external = [r for r in resources if r.is_external]
    redirects = sum(1 for p in pages if p.url != p.final_url and p.status_code in (301, 302, 307, 308))
    avg_load = None
    loads = [p.load_time for p in pages if p.load_time is not None]
    if loads:
        avg_load = round(sum(loads) / len(loads), 3)

    return {
        "total_resource_bytes": total_size,
        "js_bytes": js_size,
        "css_bytes": css_size,
        "image_bytes": image_size,
        "font_bytes": font_size,
        "other_bytes": other_size,
        "request_count": len(resources),
        "third_party_request_count": len(external),
        "page_count": len(pages),
        "avg_page_load_seconds": avg_load,
        "redirect_count": redirects,
        # Core Web Vitals are only reported when a real browser measurement
        # has been performed; otherwise explicitly "Not available".
        "lcp_seconds": None,
        "cls_score": None,
        "inp_milliseconds": None,
        "core_web_vitals_measured": False,
    }
