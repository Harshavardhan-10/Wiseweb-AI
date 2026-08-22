"""TLS / certificate observations (passive, defensive).

Only checks what is already observable via a normal TLS handshake; never
attempts to exploit or bypass TLS.
"""

import asyncio
import ssl
from dataclasses import dataclass


@dataclass
class TlsObservation:
    valid_certificate: bool
    certificate_subject: str | None = None
    certificate_issuer: str | None = None
    error: str | None = None


async def observe_tls(hostname: str, port: int = 443, timeout: float = 6.0) -> TlsObservation:
    """Connect and verify the server certificate chain (normal validation).

    Returns an observation; failures are reported as observations, never
    used to trigger exploit behavior.
    """
    loop = asyncio.get_running_loop()

    def _check() -> TlsObservation:
        ctx = ssl.create_default_context()
        try:
            with ctx.wrap_socket(ssl.socket(), server_hostname=hostname) as sock:
                sock.settimeout(timeout)
                sock.connect((hostname, port))
                cert = sock.getpeercert()
                if not cert:
                    return TlsObservation(valid_certificate=False, error="no certificate returned")
                subject = dict(x[0] for x in cert.get("subject", []))
                issuer = dict(x[0] for x in cert.get("issuer", []))
                return TlsObservation(
                    valid_certificate=True,
                    certificate_subject=subject.get("commonName"),
                    certificate_issuer=issuer.get("commonName"),
                )
        except (ssl.SSLError, OSError) as exc:
            return TlsObservation(valid_certificate=False, error=str(exc))

    return await asyncio.wait_for(loop.run_in_executor(None, _check), timeout=timeout + 2.0)
