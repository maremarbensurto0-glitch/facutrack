from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import get_user_profile


def _role_gate(role_check, view_name, message, allow_superuser=False):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url=view_name)
        def _wrapped(request, *args, **kwargs):
            profile = get_user_profile(request.user)
            if allow_superuser and getattr(request.user, "is_superuser", False):
                return view_func(request, *args, **kwargs)
            if not profile or not role_check(profile):
                messages.warning(request, message)
                return _role_redirect(request.user)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def _role_redirect(user):
    profile = get_user_profile(user)
    if profile and profile.is_admin:
        return redirect("facutrack_app:admin_dashboard")
    if profile and profile.is_staff_member:
        return redirect("facutrack_app:faculty_dashboard")
    if getattr(user, "is_superuser", False):
        return redirect("facutrack_app:admin_dashboard")
    return redirect("facutrack_app:landing")

admin_required = _role_gate(
    lambda p: p.is_admin,
    "facutrack_app:login",
    "Administrator privileges required.",
    allow_superuser=True,
)

staff_required = _role_gate(
    lambda p: p.is_staff_member,
    "facutrack_app:login",
    "Faculty access required.",
)
