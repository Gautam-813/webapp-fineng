import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import Settings, get_settings


logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
AUTH_COOKIE_NAME = "tfc_token"


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


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if (
            not self.settings.csrf_protection_enabled
            or request.method.upper() in SAFE_METHODS
            or _is_exempt_path(request.url.path, self.settings.csrf_exempt_path_list)
        ):
            return await call_next(request)

        origin = request.headers.get("origin")
        if origin:
            if _is_allowed_origin(origin, request, self.settings):
                return await call_next(request)
            return _csrf_rejected_response()

        referer = request.headers.get("referer")
        if referer:
            if _is_allowed_origin(referer, request, self.settings):
                return await call_next(request)
            return _csrf_rejected_response()

        if request.cookies.get(AUTH_COOKIE_NAME):
            return _csrf_rejected_response()

        return await call_next(request)


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


def _is_exempt_path(path: str, exempt_paths: list[str]) -> bool:
    return any(path == exempt_path or path.startswith(f"{exempt_path}/") for exempt_path in exempt_paths)


def _is_allowed_origin(value: str, request: Request, settings: Settings) -> bool:
    origin = _normalize_origin(value)
    if not origin:
        return False
    return origin in _allowed_origins(request, settings)


def _allowed_origins(request: Request, settings: Settings) -> set[str]:
    origins = {_normalize_origin(str(request.url))}
    origins.add(_normalize_origin(settings.site_url))
    origins.update(_normalize_origin(item) for item in settings.cors_origin_list)
    return {origin for origin in origins if origin}


def _normalize_origin(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlsplit(value.strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _csrf_rejected_response() -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"detail": "Cross-site request blocked"},
    )


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
    if not settings.csrf_protection_enabled:
        errors.append("CSRF_PROTECTION_ENABLED=true is required when ENVIRONMENT=production")
    if not settings.site_url.startswith("https://"):
        errors.append("SITE_URL must use https:// when ENVIRONMENT=production")
    if not settings.email_enabled:
        errors.append("EMAIL_ENABLED=true is required when ENVIRONMENT=production")
    if settings.email_enabled:
        if not settings.resend_api_key:
            errors.append("RESEND_API_KEY is required when EMAIL_ENABLED=true")
        if "@" not in settings.email_from_login:
            errors.append("EMAIL_FROM_LOGIN must be a valid sender email address")
        if not settings.registration_domain_list:
            errors.append("REGISTRATION_ALLOWED_DOMAINS must include at least one domain when EMAIL_ENABLED=true")

    if errors:
        raise RuntimeError("; ".join(errors))
