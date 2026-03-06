"""
Request idempotency middleware for safe retries.

Implements idempotency key support to allow clients to safely retry
requests without causing duplicate operations.

Follows RFC 7231 and Idempotency-Key header spec:
https://tools.ietf.org/id/draft-idempotency-header-last-call.html

Example:
    POST /api/projects
    Idempotency-Key: project-123-v1

    If called twice with same key, returns same response without
    creating project twice.
"""

import json
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, Optional, Tuple
from fastapi import Request, Header
from starlette.responses import Response

logger = logging.getLogger(__name__)


class IdempotencyCache:
    """Cache for idempotent request responses."""

    def __init__(self, max_age_minutes: int = 60):
        """
        Initialize idempotency cache.

        Args:
            max_age_minutes: How long to keep responses in cache
        """
        self.max_age = timedelta(minutes=max_age_minutes)
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._lock = threading.Lock()

    def get(self, idempotency_key: str) -> Optional[Any]:
        """
        Get cached response for idempotency key.

        Args:
            idempotency_key: Idempotency key

        Returns:
            Cached response or None if not found or expired
        """
        with self._lock:
            if idempotency_key not in self._cache:
                return None

            response, timestamp = self._cache[idempotency_key]

            # Check if expired
            if datetime.now(timezone.utc) - timestamp > self.max_age:
                del self._cache[idempotency_key]
                logger.debug(f"Idempotency cache expired for {idempotency_key}")
                return None

            logger.debug(f"Idempotency cache hit for {idempotency_key}")
            return response

    def set(self, idempotency_key: str, response: Any) -> None:
        """
        Cache response for idempotency key.

        Args:
            idempotency_key: Idempotency key
            response: Response to cache
        """
        with self._lock:
            self._cache[idempotency_key] = (response, datetime.now(timezone.utc))
            logger.debug(f"Cached response for idempotency key: {idempotency_key}")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = datetime.now(timezone.utc)
        with self._lock:
            expired_keys = [
                key
                for key, (_, timestamp) in self._cache.items()
                if now - timestamp > self.max_age
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "total_cached": len(self._cache),
                "max_age_minutes": self.max_age.total_seconds() / 60,
            }


# Global idempotency cache
_idempotency_cache = IdempotencyCache()


async def idempotency_middleware(
    request: Request,
    call_next: Callable,
) -> Response:
    """
    Middleware to enforce idempotency for safe retries.

    Supports Idempotency-Key header for POST/PUT/PATCH requests.
    If same key is used within max_age, returns cached response.

    Args:
        request: HTTP request
        call_next: Next middleware/handler

    Returns:
        Response (cached or new)
    """
    # Only process POST, PUT, PATCH (idempotent methods)
    if request.method not in ["POST", "PUT", "PATCH"]:
        return await call_next(request)

    # Get idempotency key from header
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        # Idempotency key optional, but recommended for these methods
        logger.debug(f"Missing Idempotency-Key for {request.method} {request.url.path}")
        return await call_next(request)

    # Check cache for existing response
    cached_response = _idempotency_cache.get(idempotency_key)
    if cached_response is not None:
        logger.info(f"Returning cached response for idempotency key: {idempotency_key}")

        # Return cached response with appropriate headers
        response = Response(
            content=cached_response["body"],
            status_code=cached_response["status_code"],
            headers=dict(cached_response.get("headers", {})),
        )
        response.headers["Idempotency-Replay"] = "true"
        return response

    # Execute request and cache response
    response = await call_next(request)

    # Cache successful responses (2xx status codes)
    if 200 <= response.status_code < 300:
        # Extract response body for caching
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        cached_response_data = {
            "body": response_body.decode() if response_body else "",
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }

        _idempotency_cache.set(idempotency_key, cached_response_data)
        logger.info(f"Cached idempotent response for key: {idempotency_key}")

        # Return new response (body already consumed)
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    # Don't cache error responses
    return response


def get_idempotency_cache() -> IdempotencyCache:
    """Get global idempotency cache."""
    return _idempotency_cache
