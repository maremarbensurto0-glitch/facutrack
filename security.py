from __future__ import annotations

import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from .models import LoginAttempt

MAX_ATTEMPTS = getattr(settings, "LOGIN_MAX_ATTEMPTS", 5)
LOCKOUT_SECONDS = getattr(settings, "LOGIN_LOCKOUT_SECONDS", 15 * 60)
WINDOW_SECONDS = getattr(settings, "LOGIN_ATTEMPT_WINDOW", 15 * 60)
THROTTLE_KEY_PREFIX = "ft:login:"

@dataclass
class ThrottleResult:
    allowed: bool
    retry_after: int
    attempts: int

    def as_dict(self) -> dict:
        return {"allowed": self.allowed,
                "retry_after": self.retry_after,
                "attempts": self.attempts}


def _throttle_key(scope: str, identifier: str) -> str:
    safe_id = "".join(c for c in identifier.lower() if c.isalnum() or c in ".-_@")
    return f"{THROTTLE_KEY_PREFIX}{scope}:{safe_id}"


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def throttle_login(request, username: str = "") -> ThrottleResult:
    ip = get_client_ip(request)
    scope = f"ip:{ip}|user:{username or '-'}"
    cache_key = _throttle_key(scope, ip)

    entry = cache.get(cache_key)
    if entry is None:
        entry = {"count": 0, "first": time.time(), "locked_until": 0}

    now = time.time()
    if now - entry["first"] > WINDOW_SECONDS:
        entry = {"count": 0, "first": now, "locked_until": 0}

    if entry["locked_until"] > now:
        return ThrottleResult(False, int(entry["locked_until"] - now), entry["count"])

    entry["count"] += 1
    if entry["count"] > MAX_ATTEMPTS:
        entry["locked_until"] = now + LOCKOUT_SECONDS
    cache.set(cache_key, entry, LOCKOUT_SECONDS * 2)
    return ThrottleResult(True, 0, entry["count"])


def record_failed_login(request, username: str) -> None:
    try:
        LoginAttempt.objects.create(
            username=(username or "")[:150],
            ip_address=get_client_ip(request) or None,
            timestamp=timezone.now(),
        )
    except Exception:
        pass


def clear_login_throttle(request, username: str) -> None:
    ip = get_client_ip(request)
    cache.delete(_throttle_key(f"ip:{ip}|user:{username or '-'}", ip))

_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
    "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "connect-src 'self' https://cdn.jsdelivr.net; "
    "frame-ancestors 'none'"
)

_REFERRER = "strict-origin-when-cross-origin"
_PERMISSIONS = "geolocation=(), microphone=(), camera=(), payment=()"


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = _CSP
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Referrer-Policy", _REFERRER)
        response.setdefault("Permissions-Policy", _PERMISSIONS)
        response.setdefault("X-Content-Type-Options", "nosniff")
        if request.is_secure():
            response.setdefault("Strict-Transport-Security",
                               "max-age=31536000; includeSubDomains")
        return response
