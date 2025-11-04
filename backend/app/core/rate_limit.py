"""
Rate limiting middleware
"""

import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from loguru import logger

from app.core.config import settings
from app.core.redis import get_redis


def _get_client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For if present
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # use first IP in list
        return xff.split(",")[0].strip()
    # fallback to direct client
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path
        # Exclude paths
        for exclude in settings.RATE_LIMIT_EXCLUDE_PATHS:
            if path.startswith(exclude):
                return await call_next(request)

        client_ip = _get_client_ip(request)
        if client_ip and client_ip in settings.RATE_LIMIT_WHITELIST:
            return await call_next(request)

        try:
            redis_client = await get_redis()
            window = settings.RATE_LIMIT_WINDOW_SECONDS
            max_requests = settings.RATE_LIMIT_MAX_REQUESTS

            # Use a time-bucketed key to count requests within the window
            bucket = int(time.time() // window)
            key = f"rate:{client_ip}:{bucket}"

            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, window)

            remaining = max(0, max_requests - int(count))

            # Set rate limit headers
            # Note: Starlette Response doesn't allow setting headers before call_next; we will add headers to response
            if count > max_requests:
                logger.warning(f"Rate limit exceeded: ip={client_ip} path={path} count={count}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too Many Requests",
                        "message": "请求过于频繁，请稍后再试",
                        "rate_limit": {
                            "window_seconds": window,
                            "max_requests": max_requests
                        }
                    }
                )

            # Proceed with request
            response = await call_next(request)
            try:
                # Attach headers
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Window"] = str(window)
            except Exception:
                pass
            return response
        except Exception as e:
            # On Redis failure, do not block requests; log the error
            logger.error(f"RateLimit middleware error: {e}")
            return await call_next(request)