from __future__ import annotations

from .models import get_user_profile


def global_ui(request):
    user = getattr(request, "user", None)
    profile = get_user_profile(user) if user is not None else None

    return {
        "user_profile": profile,
        "is_admin_user": bool(profile and profile.is_admin),
        "is_staff_user": bool(profile and profile.is_staff_member),
        "active_theme": "editorial-dark",
    }
