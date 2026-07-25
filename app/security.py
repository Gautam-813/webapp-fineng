import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import Settings, get_settings


logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';",
        )
        if self.settings.secure_cookies:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def dependency(self, bucket: str, limit: int, window_seconds: int):
        async def check(request: Request) -> None:
            settings = get_settings()
            if not settings.rate_limit_enabled:
                return

            now = time.monotonic()
            key = f"{bucket}:{_client_ip(request)}"
            hits = self._hits[key]

            while hits and now - hits[0] > window_seconds:
                hits.popleft()

            if len(hits) >= limit:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please wait and try again.",
                    headers={"Retry-After": str(retry_after)},
                )

            hits.append(now)

        return check


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


rate_limiter = InMemoryRateLimiter()
rate_limit = rate_limiter.dependency


def validate_runtime_security(settings: Settings) -> None:
    if not settings.is_production:
        return

    errors = []
    if settings.debug:
        errors.append("DEBUG=false is required when ENVIRONMENT=production")
    if settings.auto_create_tables:
        errors.append("AUTO_CREATE_TABLES=false is required when ENVIRONMENT=production")
    if settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32:
        errors.append("SECRET_KEY must be changed and at least 32 characters when ENVIRONMENT=production")
    if settings.secure_cookies is not True:
        errors.append("SECURE_COOKIES=true is required when ENVIRONMENT=production")
    if settings.allowed_hosts.strip() == "*":
        errors.append("ALLOWED_HOSTS must be restricted when ENVIRONMENT=production")

    if errors:
        raise RuntimeError("; ".join(errors))
