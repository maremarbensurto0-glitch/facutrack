from __future__ import annotations

import logging

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .models import VisitorLog

logger = logging.getLogger(__name__)

_EXCLUDED_PREFIXES = (
"/static/",
"/media/",
"/admin/",
"/favicon.ico",
)


def _get_client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class VisitorTrackingMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if not getattr(settings, "DEBUG", False) and not getattr(
            settings, "ENABLE_VISITOR_LOG", True
        ):
            return response

        try:
            path = request.path or "/"
            if any(path.startswith(p) for p in _EXCLUDED_PREFIXES):
                return response

            if response.status_code >= 400:
                return response

            VisitorLog.objects.create(
                ip_address=_get_client_ip(request),
                visited_page=path[:255],
            )
        except Exception:
            logger.exception("VisitorTrackingMiddleware failed")

        return response
