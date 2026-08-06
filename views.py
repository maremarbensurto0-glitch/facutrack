from __future__ import annotations

import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from . import ai_insights, analytics, reports, security
from .decorators import admin_required, staff_required
from .forms import (
    DepartmentForm,
    FacultyPasswordChangeForm,
    LoginForm,
    QuestionnaireForm,
    RateForm,
    UserCreateForm,
    UserEditForm,
    mail_credentials,
)
from .models import (
    ActivityLog,
    Department,
    Evaluation,
    EvaluationAnswer,
    Questionnaire,
    RecentActivity,
    UserProfile,
    UserRole,
    VisitorLog,
    get_user_profile,
)

User = get_user_model()

USERS_PAGE_SIZE = 20
DEPARTMENTS_PAGE_SIZE = 50

def _role_redirect(user) -> HttpResponse:
    profile = get_user_profile(user)
    if profile and profile.is_admin:
        return redirect("facutrack_app:admin_dashboard")
    if profile and profile.is_staff_member:
        return redirect("facutrack_app:faculty_dashboard")
    if getattr(user, "is_superuser", False):
        return redirect("facutrack_app:admin_dashboard")
    return redirect("facutrack_app:landing")


def _landing_stats() -> dict:
    faculty_count = UserProfile.objects.filter(role="staff").count()
    department_count = Department.objects.count()
    evaluation_count = Evaluation.objects.count()
    total_answers = EvaluationAnswer.objects.count()
    avg = EvaluationAnswer.objects.aggregate(v=Avg("rating"))["v"] or 0
    satisfaction = round((avg / 5) * 100, 1) if total_answers else 0
    return {
        "faculty_count": faculty_count,
        "department_count": department_count,
        "evaluation_count": evaluation_count,
        "satisfaction_percent": satisfaction,
    }


def _record_activity(activity: str, user=None) -> None:
    try:
        RecentActivity.objects.create(activity=activity[:255], user=user)
    except Exception:
        pass


def _log_activity(request: HttpRequest, endpoint: str) -> None:
    if request.method not in ("GET", "POST"):
        return
    try:
        ActivityLog.objects.create(
            ip_address=request.META.get("REMOTE_ADDR"),
            user=request.user if request.user.is_authenticated else None,
            method=request.method,
            endpoint=endpoint[:255],
            response_status=200,
        )
    except Exception:
        pass


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None

@never_cache
def landing(request: HttpRequest) -> HttpResponse:
    stats = _landing_stats()
    departments = Department.objects.all()[:12]
    context = {
        "stats": stats,
        "departments": departments,
        "active_nav": "home",
    }
    return render(request, "PUBLIC/landing.html", context)

@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        result = security.throttle_login(request, username=username)
        if not result.allowed:
            minutes = max(1, result.retry_after // 60)
            messages.error(
                request,
                f"Too many failed attempts. Try again in {minutes} minute"
                f"{'s' if minutes != 1 else ''}.",
            )
            return render(request, "PUBLIC/login.html", {
                "form": form,
                "active_nav": "login",
                "locked": True,
                "retry_after": result.retry_after,
            })

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            security.clear_login_throttle(request, username)
            _record_activity(f"User '{user.username}' signed in.", user=user)
            _log_activity(request, request.path)
            messages.success(request, "Login successful.")
            return _role_redirect(user)

        security.record_failed_login(request, username)
        attempts_left = max(0, 5 - result.attempts)
        if attempts_left:
            messages.error(
                request,
                f"Invalid credentials. {attempts_left} attempt"
                f"{'s' if attempts_left != 1 else ''} remaining before lockout.",
            )
        else:
            messages.error(request, "Account locked due to too many failed attempts.")

    return render(request, "PUBLIC/login.html", {
        "form": form,
        "active_nav": "login",
    })


@never_cache
@require_http_methods(["POST", "GET"])
def logout_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        _record_activity(f"User '{request.user.username}' signed out.", user=request.user)
        logout(request)
        messages.info(request, "You have been signed out.")
    return redirect("facutrack_app:landing")


@never_cache
@require_http_methods(["GET", "POST"])
def ratepage(request: HttpRequest) -> HttpResponse:
    form = RateForm(request.POST or None)
    questionnaires = Questionnaire.objects.all()
    if request.method == "POST":
        if form.is_valid():
            return _save_evaluation(request, form, questionnaires)
        messages.error(request, "Please correct the errors below.")

    return render(request, "PUBLIC/ratepage.html", {
        "form": form,
        "questionnaires": questionnaires,
        "active_nav": "rate",
    })


def _save_evaluation(request: HttpRequest, form: RateForm, questionnaires) -> HttpResponse:
    unanswered = [q.id for q in questionnaires
                  if not request.POST.get(f"q_{q.id}")]
    if unanswered:
        messages.error(
            request,
            f"Please answer all questions (missing {len(unanswered)} answer"
            f"{'s' if len(unanswered) != 1 else ''}).",
        )
        return render(request, "PUBLIC/ratepage.html", {
            "form": form,
            "questionnaires": questionnaires,
            "active_nav": "rate",
        })

    evaluation = form.save()
    for q in questionnaires:
        rating = int(request.POST.get(f"q_{q.id}"))
        EvaluationAnswer.objects.create(
            evaluation=evaluation, questionnaire=q, rating=rating,
        )

    from .models import DraftEvaluation
    DraftEvaluation.objects.filter(email=evaluation.email).delete()

    _record_activity(
        f"New evaluation submitted for {evaluation.faculty.username if evaluation.faculty else '—'}.",
        user=request.user if request.user.is_authenticated else None,
    )
    messages.success(request, "Evaluation submitted successfully.")
    return redirect("facutrack_app:receipt", receipt_code=evaluation.receipt_code())


@never_cache
def receipt(request: HttpRequest, receipt_code: str) -> HttpResponse:
    raw = receipt_code.replace("FT-", "").lstrip("0") or "0"
    try:
        evaluation = get_object_or_404(Evaluation, pk=int(raw))
    except (ValueError, TypeError):
        evaluation = get_object_or_404(Evaluation, pk=receipt_code)
    return render(request, "PUBLIC/receipt.html", {
        "evaluation": evaluation,
        "active_nav": "rate",
    })

@never_cache
@require_http_methods(["POST"])
def autosave_draft(request: HttpRequest) -> JsonResponse:
    from .models import DraftEvaluation
    payload = json.loads(request.body or b"{}")
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return JsonResponse({"ok": False, "error": "email required"}, status=400)
    DraftEvaluation.objects.update_or_create(
        email=email,
        defaults={"saved_progress": payload.get("data", {})},
    )
    return JsonResponse({"ok": True})

@never_cache
@admin_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    kpis = analytics.compute_dashboard_kpis()
    range_key, start = analytics.resolve_date_filter(request.GET.get("range", "30d"))

    eval_series = analytics.evaluations_timeseries(start=start)
    visit_series = analytics.visitor_timeseries(start=start)
    rating_distribution = analytics.rating_distribution()
    faculty_rows = analytics.faculty_rankings()[:6]
    department_rows = analytics.department_rankings()[:6]
    recent_activities = RecentActivity.objects.select_related("user")[:8]

    line_chart = {
        "labels": [r["label"] for r in eval_series],
        "datasets": [
            {"label": "Evaluations", "data": [r["count"] for r in eval_series]},
            {"label": "Visitors", "data": [r["count"] for r in visit_series]},
            {"label": "Average rating",
             "data": [r["average"] for r in eval_series],
             "yAxisID": "y2"},
        ],
    }
    pie_chart = {
        "labels": [f"{i} star{'s' if i != 1 else ''}" for i in range(1, 6)],
        "data": [rating_distribution[i] for i in range(1, 6)],
    }

    return render(request, "ADMIN/dashboard.html", {
        "kpis": kpis.as_dict(),
        "range_key": range_key,
        "range_options": analytics.DATE_FILTERS,
        "line_chart": json.dumps(line_chart),
        "pie_chart": json.dumps(pie_chart),
        "faculty_rows": faculty_rows,
        "department_rows": department_rows,
        "recent_activities": recent_activities,
        "active_nav": "dashboard",
    })

@never_cache
@admin_required
def user_management(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    role = request.GET.get("role") or ""
    department_id = request.GET.get("department") or ""
    page_number = request.GET.get("page", 1)

    profiles = (
        UserProfile.objects
        .select_related("user", "department")
        .all()
    )
    if q:
        profiles = profiles.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(full_name__icontains=q)
        )
    if role:
        profiles = profiles.filter(role=role)
    if department_id:
        profiles = profiles.filter(department_id=department_id)

    paginator = Paginator(profiles, USERS_PAGE_SIZE)
    page = paginator.get_page(page_number)
    return render(request, "ADMIN/user_management.html", {
        "page": page,
        "departments": Department.objects.all(),
        "q": q,
        "role": role,
        "department_id": department_id,
        "active_nav": "users",
    })


@never_cache
@admin_required
@require_http_methods(["GET", "POST"])
def user_create(request: HttpRequest) -> HttpResponse:
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        emailed = mail_credentials(user, user.profile.temp_password)
        if emailed:
            messages.success(
                request,
                f"User '{user.username}' created. Credentials emailed to {user.email}.",
            )
        else:
            messages.warning(
                request,
                f"User '{user.username}' created, but the welcome email could "
                f"not be delivered. The temporary password is stored on the "
                f"profile and can be shared manually.",
            )
        _record_activity(f"User '{user.username}' created.", user=request.user)
        return redirect("facutrack_app:user_management")
    return render(request, "ADMIN/user_form.html", {
        "form": form, "mode": "create", "active_nav": "users",
    })


@never_cache
@admin_required
@require_http_methods(["POST"])
def user_resend_credentials(request: HttpRequest, user_id: int) -> HttpResponse:
    user = get_object_or_404(User, pk=user_id)
    profile = get_object_or_404(UserProfile, user=user)

    if not profile.temp_password:
        from .forms import generate_temporary_password
        profile.temp_password = generate_temporary_password()
        user.set_password(profile.temp_password)
        user.save()
        profile.save()

    emailed = mail_credentials(user, profile.temp_password)
    if emailed:
        messages.success(request, f"Credentials re-sent to {user.email}.")
    else:
        messages.error(
            request,
            "Could not send the email. Check SMTP settings and the user's "
            "email address.",
        )
    return redirect("facutrack_app:user_management")


@never_cache
@admin_required
@require_http_methods(["GET", "POST"])
def smtp_test(request: HttpRequest) -> HttpResponse:
    target = ""
    if request.method == "POST":
        target = (request.POST.get("to") or request.user.email).strip()
        if not target:
            messages.error(request, "No recipient email address provided.")
        else:
            from logging import getLogger
            from django.conf import settings as dj_settings
            from django.core.mail import send_mail

            log = getLogger(__name__)
            try:
                send_mail(
                    subject=f"{getattr(dj_settings, 'EMAIL_SUBJECT_PREFIX', '')}SMTP test",
                    message=(
                        "Hello!\n\n"
                        "This message confirms that the FacuTrack SMTP "
                        "configuration is working correctly.\n\n"
                        f"Backend: {dj_settings.EMAIL_BACKEND}\n"
                        f"Host:    {dj_settings.EMAIL_HOST}:{dj_settings.EMAIL_PORT}\n"
                        f"From:    {dj_settings.DEFAULT_FROM_EMAIL}\n\n"
                        "— FacuTrack"
                    ),
                    from_email=None,
                    recipient_list=[target],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f"Test email sent to {target}. Check the inbox (and spam).",
                )
                _record_activity(
                    f"SMTP test email sent to {target}.", user=request.user,
                )
            except Exception as exc:
                log.exception("SMTP test failed: %s", exc)
                messages.error(
                    request,
                    f"SMTP test failed: {exc}. Check EMAIL_HOST, "
                    f"EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_PORT, "
                    f"EMAIL_USE_TLS, and EMAIL_USE_SSL in settings.py.",
                )
        return redirect("facutrack_app:smtp_test")

    return render(request, "ADMIN/smtp_test.html", {
        "active_nav": "users",
        "default_to": request.user.email,
    })


@never_cache
@admin_required
@require_http_methods(["GET", "POST"])
def user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    user = get_object_or_404(User, pk=user_id)
    profile = get_object_or_404(UserProfile, user=user)
    form = UserEditForm(request.POST or None, instance=user, profile=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        _record_activity(f"User '{user.username}' updated.", user=request.user)
        messages.success(request, "User updated successfully.")
        return redirect("facutrack_app:user_management")
    return render(request, "ADMIN/user_form.html", {
        "form": form, "mode": "edit", "profile": profile,
        "active_nav": "users",
    })


@never_cache
@admin_required
@require_http_methods(["POST"])
def user_delete(request: HttpRequest, user_id: int) -> HttpResponse:
    user = get_object_or_404(User, pk=user_id)
    username = user.username
    user.delete()
    _record_activity(f"User '{username}' deleted.", user=request.user)
    messages.success(request, "User deleted successfully.")
    return redirect("facutrack_app:user_management")

@never_cache
@admin_required
def department_management(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    qs = Department.objects.annotate(faculty_count=Count("members")).order_by("department_name")
    if q:
        qs = qs.filter(department_name__icontains=q)
    paginator = Paginator(qs, DEPARTMENTS_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))
    return render(request, "ADMIN/department_management.html", {
        "page": page, "q": q, "active_nav": "departments",
    })


@never_cache
@admin_required
@require_http_methods(["GET", "POST"])
def department_create(request: HttpRequest) -> HttpResponse:
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        _record_activity(
            f"Department '{form.cleaned_data['department_name']}' created.",
            user=request.user,
        )
        messages.success(request, "Department added successfully.")
        return redirect("facutrack_app:department_management")
    return render(request, "ADMIN/department_form.html", {
        "form": form, "mode": "create", "active_nav": "departments",
    })


@never_cache
@admin_required
@require_http_methods(["GET", "POST"])
def department_edit(request: HttpRequest, department_id: int) -> HttpResponse:
    dept = get_object_or_404(Department, pk=department_id)
    form = DepartmentForm(request.POST or None, instance=dept)
    if request.method == "POST" and form.is_valid():
        form.save()
        _record_activity(
            f"Department '{dept.department_name}' updated.",
            user=request.user,
        )
        messages.success(request, "Department updated successfully.")
        return redirect("facutrack_app:department_management")
    return render(request, "ADMIN/department_form.html", {
        "form": form, "mode": "edit", "department": dept, "active_nav": "departments",
    })


@never_cache
@admin_required
@require_http_methods(["POST"])
def department_delete(request: HttpRequest, department_id: int) -> HttpResponse:
    dept = get_object_or_404(Department, pk=department_id)
    name = dept.department_name
    dept.delete()
    _record_activity(f"Department '{name}' deleted.", user=request.user)
    messages.success(request, "Department deleted successfully.")
    return redirect("facutrack_app:department_management")

@never_cache
@admin_required
def questionnaire_management(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    qs = Questionnaire.objects.all()
    if q:
        qs = qs.filter(question__icontains=q)
    return render(request, "ADMIN/questionnaire_management.html", {
        "questionnaires": qs, "q": q, "active_nav": "questionnaire",
    })


@never_cache
@admin_required
@require_http_methods(["GET", "POST"])
def questionnaire_create(request: HttpRequest) -> HttpResponse:
    form = QuestionnaireForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        _record_activity(
            f"Questionnaire added: '{form.cleaned_data['question'][:40]}'.",
            user=request.user,
        )
        messages.success(request, "Questionnaire added successfully.")
        return redirect("facutrack_app:questionnaire_management")
    return render(request, "ADMIN/questionnaire_form.html", {
        "form": form, "mode": "create", "active_nav": "questionnaire",
    })


@never_cache
@admin_required
@require_http_methods(["GET", "POST"])
def questionnaire_edit(request: HttpRequest, questionnaire_id: int) -> HttpResponse:
    q = get_object_or_404(Questionnaire, pk=questionnaire_id)
    form = QuestionnaireForm(request.POST or None, instance=q)
    if request.method == "POST" and form.is_valid():
        form.save()
        _record_activity(
            f"Questionnaire updated: '{q.question[:40]}'.",
            user=request.user,
        )
        messages.success(request, "Questionnaire updated successfully.")
        return redirect("facutrack_app:questionnaire_management")
    return render(request, "ADMIN/questionnaire_form.html", {
        "form": form, "mode": "edit", "questionnaire": q, "active_nav": "questionnaire",
    })


@never_cache
@admin_required
@require_http_methods(["POST"])
def questionnaire_delete(request: HttpRequest, questionnaire_id: int) -> HttpResponse:
    q = get_object_or_404(Questionnaire, pk=questionnaire_id)
    label = q.question[:40]
    q.delete()
    _record_activity(f"Questionnaire deleted: '{label}'.", user=request.user)
    messages.success(request, "Questionnaire deleted successfully.")
    return redirect("facutrack_app:questionnaire_management")

@never_cache
@admin_required
def faculty_rankings(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    department_id = request.GET.get("department")
    department = Department.objects.filter(pk=department_id).first() if department_id else None
    rows = analytics.faculty_rankings(department=department, search=q)
    return render(request, "ADMIN/faculty_rankings.html", {
        "rows": rows,
        "departments": Department.objects.all(),
        "q": q,
        "department_id": department_id,
        "active_nav": "rankings",
    })

@never_cache
@admin_required
def reports_page(request: HttpRequest) -> HttpResponse:
    return render(request, "ADMIN/reports.html", {"active_nav": "reports"})


@never_cache
@admin_required
def download_report(request: HttpRequest) -> HttpResponse:
    report_type = request.GET.get("type", "evaluation_summary")
    fmt = request.GET.get("format", "csv")
    department = Department.objects.filter(pk=request.GET.get("department")).first() \
        if request.GET.get("department") else None
    return reports.build_report(
        report_type=report_type,
        fmt=fmt,
        start=_parse_date(request.GET.get("start")),
        end=_parse_date(request.GET.get("end")),
        department=department,
        search=request.GET.get("q", ""),
    )

@never_cache
@admin_required
def system_logs(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    start = _parse_date(request.GET.get("start"))
    end = _parse_date(request.GET.get("end"))
    method = request.GET.get("method") or ""

    logs = ActivityLog.objects.select_related("user").all()
    if q:
        logs = logs.filter(
            Q(endpoint__icontains=q) |
            Q(ip_address__icontains=q) |
            Q(user__username__icontains=q)
        )
    if start:
        logs = logs.filter(timestamp__gte=start)
    if end:
        logs = logs.filter(timestamp__lte=end)
    if method:
        logs = logs.filter(method=method)

    paginator = Paginator(logs, 25)
    page = paginator.get_page(request.GET.get("page", 1))
    visitor_ips = VisitorLog.objects.values_list("ip_address", flat=True).distinct()[:50]

    return render(request, "ADMIN/logs.html", {
        "page": page,
        "q": q,
        "method": method,
        "visitor_ips": visitor_ips,
        "active_nav": "logs",
    })


@never_cache
@admin_required
@require_http_methods(["GET"])
def logs_json(request: HttpRequest) -> JsonResponse:
    """Live console polling endpoint."""

    logs = ActivityLog.objects.select_related("user").order_by("-timestamp")[:50]
    return JsonResponse({
        "logs": [{
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": l.ip_address or "-",
            "method": l.method,
            "endpoint": l.endpoint,
            "status": l.response_status,
            "user": l.user.username if l.user else "-",
        } for l in logs],
    })


@never_cache
@admin_required
@require_http_methods(["POST"])
def clear_logs(request: HttpRequest) -> HttpResponse:
    ActivityLog.objects.all().delete()
    _record_activity("System logs cleared.", user=request.user)
    messages.success(request, "Logs cleared successfully.")
    return redirect("facutrack_app:system_logs")

@never_cache
@staff_required
def faculty_dashboard(request: HttpRequest) -> HttpResponse:
    profile = get_user_profile(request.user)
    summary = analytics.faculty_summary(profile)
    period = request.GET.get("range", "30d")
    _, start = analytics.resolve_date_filter(period)
    trend = ai_insights.predict_next_period(profile, periods=3)
    distribution = summary["distribution"]

    rows = analytics.faculty_rankings()
    rank = next((i + 1 for i, r in enumerate(rows)
                 if r["faculty_id"] == request.user.id), None)

    feedback_qs = (
        Evaluation.objects
        .filter(faculty=request.user)
        .select_related("department")
        .order_by("-created_at")
    )
    if start:
        feedback_qs = feedback_qs.filter(created_at__gte=start)
    paginator = Paginator(feedback_qs, 10)
    feedback_page = paginator.get_page(request.GET.get("page", 1))

    status = "Passed" if summary["percentage"] >= 60 else "Failed"
    status_band = "success" if summary["percentage"] >= 60 else "danger"

    return render(request, "STAFF/faculty_dashboard.html", {
        "summary": summary,
        "rank": rank,
        "distribution_json": json.dumps(distribution),
        "trend": trend,
        "trend_labels": json.dumps(trend["labels"]),
        "trend_history": json.dumps(trend["history"]),
        "trend_forecast": json.dumps(trend["forecast"]),
        "range_key": period,
        "feedback_page": feedback_page,
        "status": status,
        "status_band": status_band,
        "total_faculty": len(rows),
        "active_nav": "dashboard",
    })


@never_cache
@staff_required
def faculty_feedback(request: HttpRequest) -> HttpResponse:
    profile = get_user_profile(request.user)
    feedback_qs = (
        Evaluation.objects
        .filter(faculty=request.user)
        .select_related("department")
        .order_by("-created_at")
    )
    paginator = Paginator(feedback_qs, 20)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "STAFF/faculty_feedback.html", {
        "page": page,
        "summary": analytics.faculty_summary(profile),
        "active_nav": "feedback",
    })


@never_cache
@staff_required
def faculty_feedback_detail(request: HttpRequest, evaluation_id: int) -> HttpResponse:
    profile = get_user_profile(request.user)
    evaluation = get_object_or_404(Evaluation, pk=evaluation_id, faculty=request.user)
    answers = evaluation.answers.select_related("questionnaire")
    return render(request, "STAFF/faculty_feedback_detail.html", {
        "evaluation": evaluation,
        "answers": answers,
        "active_nav": "feedback",
    })


@never_cache
@staff_required
def faculty_settings(request: HttpRequest) -> HttpResponse:
    profile = get_user_profile(request.user)
    edit_form = UserEditForm(
        request.POST or None, instance=request.user, profile=profile,
    )
    password_form = FacultyPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "profile" and edit_form.is_valid():
            edit_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("facutrack_app:faculty_settings")
        if action == "password" and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect("facutrack_app:faculty_settings")
        messages.error(request, "Please correct the errors below.")
    return render(request, "STAFF/faculty_settings.html", {
        "profile": profile,
        "edit_form": edit_form,
        "password_form": password_form,
        "active_nav": "settings",
    })

@never_cache
@admin_required
def analytics_hub(request: HttpRequest) -> HttpResponse:
    return render(request, "ADMIN/analytics_hub.html", {"active_nav": "analytics"})


@never_cache
@admin_required
def ai_insights_view(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    department_id = request.GET.get("department")
    department = Department.objects.filter(pk=department_id).first() if department_id else None

    insights = ai_insights.analyse_all_faculty(department=department, search=q)
    kpis = ai_insights.highest_and_lowest(department=department)
    departments = Department.objects.all()

    return render(request, "ADMIN/ai_insights.html", {
        "insights": insights,
        "kpis": kpis,
        "departments": departments,
        "q": q,
        "department_id": department_id,
        "active_nav": "analytics",
    })


@never_cache
@admin_required
def ai_faculty_report(request: HttpRequest, faculty_id: int) -> HttpResponse:
    profile = get_object_or_404(UserProfile, user_id=faculty_id, role=UserRole.STAFF)
    insight = ai_insights.analyse_faculty(profile)
    return render(request, "ADMIN/ai_faculty_report.html", {
        "insight": insight,
        "active_nav": "analytics",
    })


@never_cache
@admin_required
def department_comparison(request: HttpRequest) -> HttpResponse:
    rows = analytics.department_rankings()
    highest = rows[0] if rows else None
    lowest = rows[-1] if rows else None
    average_system = round(sum(r["percentage"] for r in rows) / len(rows), 1) if rows else 0

    radar_chart = {
        "labels": ["Teaching Quality", "Communication", "Professionalism",
                   "Student Satisfaction", "Overall Performance"],
        "datasets": [{
            "label": dept["department_name"],
            "data": [
                dept["percentage"],
                max(0, dept["percentage"] - 5),
                max(0, dept["percentage"] - 3),
                max(0, dept["percentage"] - 1),
                dept["percentage"],
            ],
        } for dept in rows[:5]],
    }
    bar_chart = {
        "labels": [r["department_name"] for r in rows],
        "data": [r["percentage"] for r in rows],
    }
    pie_chart = {
        "labels": [r["department_name"] for r in rows],
        "data": [r["evaluations"] for r in rows],
    }

    return render(request, "ADMIN/department_comparison.html", {
        "rows": rows,
        "highest": highest,
        "lowest": lowest,
        "average_system": average_system,
        "radar_chart": json.dumps(radar_chart),
        "bar_chart": json.dumps(bar_chart),
        "pie_chart": json.dumps(pie_chart),
        "active_nav": "analytics",
    })


@never_cache
@admin_required
def predictive_analytics(request: HttpRequest) -> HttpResponse:
    rows = analytics.faculty_rankings()
    faculty_forecasts = []
    for r in rows[:8]:
        profile = UserProfile.objects.filter(user_id=r["faculty_id"]).first()
        if not profile:
            continue
        forecast = ai_insights.predict_next_period(profile, periods=3)
        faculty_forecasts.append({
            "name": r["full_name"],
            "delta": forecast["delta"],
            "history": forecast["history"],
            "forecast": forecast["forecast"],
            "labels": forecast["labels"],
            "confidence": forecast["confidence"],
        })

    sorted_by_delta = sorted(faculty_forecasts, key=lambda f: f["delta"])
    predicted_lowest = sorted_by_delta[0] if sorted_by_delta else None
    predicted_highest = sorted_by_delta[-1] if sorted_by_delta else None

    system_forecast = ai_insights.system_wide_forecast()
    department_forecasts = [
        {"name": dept.department_name,
         "data": ai_insights.department_forecast(dept, periods=3)}
        for dept in Department.objects.all()
    ]
    sorted_dept = sorted(department_forecasts, key=lambda d: d["data"]["delta"])
    predicted_best_dept = sorted_dept[-1] if sorted_dept else None

    return render(request, "ADMIN/predictive_analytics.html", {
        "faculty_forecasts": faculty_forecasts,
        "faculty_forecasts_json": json.dumps(faculty_forecasts),
        "predicted_highest": predicted_highest,
        "predicted_lowest": predicted_lowest,
        "predicted_best_dept": predicted_best_dept,
        "system_forecast": system_forecast,
        "department_forecasts": department_forecasts,
        "department_forecasts_json": json.dumps(department_forecasts),
        "active_nav": "analytics",
    })

@never_cache
def faculty_by_department(request: HttpRequest) -> JsonResponse:
    department_id = request.GET.get("department")
    qs = UserProfile.objects.filter(role="staff").select_related("user")
    if department_id:
        qs = qs.filter(department_id=department_id)
    data = [
        {"id": p.user_id, "name": p.display_name()}
        for p in qs.order_by("user__username")
    ]
    return JsonResponse({"faculty": data})
