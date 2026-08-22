"""Simple in-process rate limiter for API endpoints.

Production deployments should replace this with a Redis-backed limiter
(Redis is already available in the stack); the interface is kept minimal
so the swap is trivial.
"""

import time
import threading
from collections import defaultdict, deque

from fastapi import Request, status
from fastapi.responses import JSONResponse


class TokenBucketLimiter:
    """Per-key token bucket with sliding refill.

    key: usually the client IP; limit: max requests per window seconds.
    """

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True

    async def __call__(self, request: Request) -> None:
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        if not self.allow(ip):
            raise RateLimitExceeded()


class RateLimitExceeded(Exception):
    pass


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:  # noqa: ARG001
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please try again later.",
                "details": {},
            }
        },
    )


# One limiter for scan creation (conservative — scans are expensive).
scan_limiter = TokenBucketLimiter(limit=10, window_seconds=60)
