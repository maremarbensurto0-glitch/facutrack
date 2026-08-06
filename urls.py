from __future__ import annotations

from django.urls import path

from . import views

app_name = "facutrack_app"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("rate/", views.ratepage, name="ratepage"),
    path("rate/autosave/", views.autosave_draft, name="autosave_draft"),
    path("rate/api/faculty/", views.faculty_by_department, name="faculty_by_department"),
    path("receipt/<str:receipt_code>/", views.receipt, name="receipt"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    path("admin/users/", views.user_management, name="user_management"),
    path("admin/users/new/", views.user_create, name="user_create"),
    path("admin/users/<int:user_id>/edit/", views.user_edit, name="user_edit"),
    path("admin/users/<int:user_id>/delete/", views.user_delete, name="user_delete"),
    path("admin/users/<int:user_id>/resend/", views.user_resend_credentials, name="user_resend_credentials"),
    path("admin/users/smtp-test/", views.smtp_test, name="smtp_test"),

    path("admin/departments/", views.department_management, name="department_management"),
    path("admin/departments/new/", views.department_create, name="department_create"),
    path("admin/departments/<int:department_id>/edit/", views.department_edit, name="department_edit"),
    path("admin/departments/<int:department_id>/delete/", views.department_delete, name="department_delete"),

    path("admin/questionnaire/", views.questionnaire_management, name="questionnaire_management"),
    path("admin/questionnaire/new/", views.questionnaire_create, name="questionnaire_create"),
    path("admin/questionnaire/<int:questionnaire_id>/edit/", views.questionnaire_edit, name="questionnaire_edit"),
    path("admin/questionnaire/<int:questionnaire_id>/delete/", views.questionnaire_delete, name="questionnaire_delete"),

    path("admin/rankings/", views.faculty_rankings, name="faculty_rankings"),

    path("admin/reports/", views.reports_page, name="reports_page"),
    path("admin/reports/download/", views.download_report, name="download_report"),

    path("admin/logs/", views.system_logs, name="system_logs"),
    path("admin/logs/json/", views.logs_json, name="logs_json"),
    path("admin/logs/clear/", views.clear_logs, name="clear_logs"),

    path("admin/analytics/", views.analytics_hub, name="analytics_hub"),
    path("admin/analytics/insights/", views.ai_insights_view, name="ai_insights"),
    path("admin/analytics/insights/<int:faculty_id>/", views.ai_faculty_report, name="ai_faculty_report"),
    path("admin/analytics/departments/", views.department_comparison, name="department_comparison"),
    path("admin/analytics/predictive/", views.predictive_analytics, name="predictive_analytics"),

    path("faculty/dashboard/", views.faculty_dashboard, name="faculty_dashboard"),
    path("faculty/feedback/", views.faculty_feedback, name="faculty_feedback"),
    path("faculty/feedback/<int:evaluation_id>/", views.faculty_feedback_detail, name="faculty_feedback_detail"),
    path("faculty/settings/", views.faculty_settings, name="faculty_settings"),
]
