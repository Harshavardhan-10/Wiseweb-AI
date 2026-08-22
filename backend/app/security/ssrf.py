"""SSRF protection.

Mandatory before ANY outbound request:

1. Parse hostname from the URL.
2. Resolve DNS for the hostname.
3. Reject if ANY resolved IP is private/internal/link-local/special.
4. Reject localhost, cloud metadata endpoints, internal hostnames.
5. Re-validate on every redirect (never trust only the initial URL).

This is a defensive guard: Wiseweb-AI only ever contacts public internet
hosts. Everything else is refused with a clear error.
"""

import ipaddress
import logging
from functools import lru_cache
from urllib.parse import urlparse

import dns.resolver
import httpx
import tldextract

from app.config.settings import settings
from app.core.exceptions import ValidationError

logger = logging.getLogger("wisewebai.ssrf")

CLOUD_METADATA_HOSTS = (
    "169.254.169.254",      # AWS / GCP / Azure / OCI metadata
    "169.254.170.2",        # AWS ECS container metadata
    "metadata.google.internal",
    "metadata.azure.internal",
    "metadata.internal",
)

PRIVATE_SUFFIXES = (".internal", ".local", ".localhost", ".lan", ".home.arpa")

# Well-known internal hostnames that must never resolve into a crawl.
BLOCKED_HOSTNAMES = {
    "localhost", "localhost.localdomain", "localhost4", "localhost6",
    "metadata.google.internal", "metadata.azure.internal", "metadata.internal",
    "instance-data", "instance-data.ec2.internal",
}

_SCHEMES = ("http", "https")


def validate_resolved_ip(ip_address: str) -> None:
    """Raise ValidationError if the IP is not a public, routable address."""
    try:
        addr = ipaddress.ip_address(ip_address)
    except ValueError:
        raise ValidationError(f"Invalid IP address: {ip_address}") from None

    if addr.is_private or addr.is_loopback or addr.is_link_local:
        raise ValidationError(f"Refusing private/internal address: {ip_address}")
    if addr.is_reserved or addr.is_multicast or addr.is_unspecified:
        raise ValidationError(f"Refusing reserved address: {ip_address}")
    # Covers 169.254.169.254 and IPv6 equivalents like ::ffff:169.254.169.254
    if addr in ipaddress.ip_network("169.254.0.0/16"):
        raise ValidationError(f"Refusing link-local address: {ip_address}")


def _hostname_is_blocked(hostname: str) -> bool:
    lowered = hostname.lower()
    if lowered in BLOCKED_HOSTNAMES:
        return True
    # Single-label hostnames (e.g. "intranet", "db", "admin") are not
    # crawlable public targets — always refuse.
    if "." not in lowered:
        return True
    ext = tldextract.extract(lowered)
    domain = ext.domain
    if not domain:
        # Hostnames with no extractable domain are not crawlable targets.
        return True
    if lowered.endswith(PRIVATE_SUFFIXES):
        return True
    if domain in ("local", "internal", "home", "lan", "corp", "intranet", "office"):
        return True
    return False


def check_hostname_safety(hostname: str) -> None:
    if not hostname:
        raise ValidationError("URL has no hostname.")
    if _hostname_is_blocked(hostname):
        raise ValidationError(f"Hostname is not a public internet host: {hostname}")


@lru_cache(maxsize=2048)
def resolve_host_ips(hostname: str) -> list[str]:
    """Resolve all A/AAAA records for a hostname (defensive)."""
    ips: list[str] = []
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 5.0
    for record_type in ("A", "AAAA"):
        try:
            answers = resolver.resolve(hostname, record_type)
            for answer in answers:
                ips.append(str(answer.address if record_type == "A" else answer))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
                dns.resolver.NoNameservers, dns.resolver.LifetimeTimeout):
            continue
    return ips


def validate_url_target(url: str) -> str:
    """Validate that a URL is an http(s) public target.

    Performs hostname + DNS checks and returns the parsed, normalized URL.
    Used before ANY request (initial fetch and every redirect).
    """
    parsed = urlparse(url)
    if parsed.scheme not in _SCHEMES:
        raise ValidationError("Only http and https URLs are supported.")
    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("URL has no hostname.")

    check_hostname_safety(hostname)

    # Resolve DNS and verify every address is public.
    ips = resolve_host_ips(hostname)
    if not ips:
        raise ValidationError(f"Could not resolve hostname: {hostname}")
    for ip in ips:
        validate_resolved_ip(ip)

    return url


async def is_safe_public_url(url: str) -> bool:
    """Async convenience wrapper around validate_url_target."""
    try:
        validate_url_target(url)
        return True
    except ValidationError:
        return False


class RedirectGuardTransport(httpx.BaseTransport, httpx.AsyncBaseTransport):
    """httpx transport wrapper that validates the URL of every request
    (including each redirect hop) before it is sent.

    Supports both sync (handle_request) and async (handle_async_request)
    clients. Every hop's hostname is DNS-checked and refused if it resolves
    to a private/internal address.

    ``allow_internal=True`` is the DEMO-ONLY escape hatch used by the seed
    script; it is never enabled from the API layer.
    """

    def __init__(self, inner: httpx.BaseTransport, allow_internal: bool = False):
        self._inner = inner
        self.allow_internal = allow_internal

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if not self.allow_internal:
            validate_url_target(str(request.url))
        return self._inner.handle_request(request)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if not self.allow_internal:
            validate_url_target(str(request.url))
        return await self._inner.handle_async_request(request)
