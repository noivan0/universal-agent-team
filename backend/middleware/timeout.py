"""
Request timeout middleware to prevent hanging requests.

Enforces a maximum request duration to prevent resource exhaustion
and improve user experience with timeout notifications.

Example:
    app.middleware("http")(timeout_middleware)
"""

import asyncio
import logging
from fastapi import Request
from starlette.responses import JSONResponse
from typing import Callable

logger = logging.getLogger(__name__)

# Default request timeout in seconds
DEFAULT_REQUEST_TIMEOUT = 60


async def timeout_middleware(
    request: Request,
    call_next: Callable,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT,
) -> JSONResponse:
    """
    Enforce request timeout.

    Args:
        request: HTTP request
        call_next: Next middleware/handler
        timeout_seconds: Request timeout in seconds

    Returns:
        Response or timeout error
    """
    try:
        # Enforce timeout for request processing
        response = await asyncio.wait_for(
            call_next(request),
            timeout=timeout_seconds,
        )
        return response

    except asyncio.TimeoutError:
        logger.warning(
            f"Request timeout: {request.method} {request.url.path} "
            f"(timeout: {timeout_seconds}s)"
        )

        return JSONResponse(
            status_code=504,
            content={
                "error_code": "REQUEST_TIMEOUT",
                "message": "Request took too long to complete",
                "guidance": "Try with a smaller request or simpler query",
                "timeout_seconds": timeout_seconds,
            },
        )

    except Exception as exc:
        # Other errors should be handled by existing exception handlers
        logger.error(f"Unexpected error in timeout middleware: {exc}")
        raise


def create_timeout_middleware(timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT):
    """
    Create a timeout middleware with custom timeout.

    Args:
        timeout_seconds: Request timeout in seconds

    Returns:
        Middleware function
    """

    async def middleware(request: Request, call_next: Callable):
        return await timeout_middleware(request, call_next, timeout_seconds)

    return middleware
