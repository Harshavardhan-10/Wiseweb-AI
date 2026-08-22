"""Safe robots.txt handling.

We fetch robots.txt ourselves (through the SSRF-guarded fetcher) and parse
it locally. If the site is unreachable or robots.txt is missing, crawling
proceeds for public pages (missing robots.txt is common and not an abuse
signal by itself).
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

WELENS_AGENT = "wisewebaibot"
DEFAULT_AGENT = "*"


@dataclass
class RobotsRules:
    base_url: str
    disallowed_paths: list[str] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)
    allow_paths: list[str] = field(default_factory=list)
    crawl_delay: float | None = None

    def can_fetch(self, url: str) -> bool:
        path = urlparse(url).path or "/"
        path = re.sub(r"/+", "/", path)
        for allowed in self.allow_paths:
            if path.startswith(allowed):
                return True
        for pattern in self.disallowed_paths:
            if pattern and path.startswith(pattern):
                return False
        return True


def parse_robots_txt(content: str, base_url: str) -> RobotsRules:
    """Parse a robots.txt body into rules for our user agent.

    We honor rules targeted at our agent, then the generic '*' group.
    Lines that only apply to other named agents are ignored.
    """
    rules = RobotsRules(base_url=base_url)
    current_agents: list[str] = []
    relevant = False
    delay_lines: list[str] = []

    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            current_agents = [a.lower() for a in value.split(",")]
            relevant = WELENS_AGENT in current_agents or DEFAULT_AGENT in current_agents
            continue
        if not relevant:
            continue
        if key == "disallow":
            if value:
                rules.disallowed_paths.append(value)
        elif key == "allow":
            if value:
                rules.allow_paths.append(value)
        elif key == "sitemap":
            rules.sitemaps.append(value)
        elif key == "crawl-delay":
            delay_lines.append(value)

    if delay_lines:
        try:
            rules.crawl_delay = max(0.0, float(delay_lines[0]))
        except ValueError:
            rules.crawl_delay = None

    # Resolve relative sitemap URLs.
    resolved = []
    for sm in rules.sitemaps:
        if sm.startswith(("http://", "https://")):
            resolved.append(sm)
        else:
            resolved.append(urljoin(base_url, sm))
    rules.sitemaps = resolved
    return rules
