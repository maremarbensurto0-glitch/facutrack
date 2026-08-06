from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import (
    ActivityLog,
    Department,
    DraftEvaluation,
    Evaluation,
    EvaluationAnswer,
    Questionnaire,
    RecentActivity,
    UserProfile,
    VisitorLog,
    LoginAttempt,
)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fk_name = "user"


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "role", "department", "created_at")
    list_filter = ("role", "gender", "department")
    search_fields = ("user__username", "user__email", "full_name")
    autocomplete_fields = ("user", "department")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("department_name", "created_at")
    search_fields = ("department_name",)


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "created_at")
    search_fields = ("question",)


class EvaluationAnswerInline(admin.TabularInline):
    model = EvaluationAnswer
    extra = 0


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "full_name", "department",
                    "faculty", "created_at")
    list_filter = ("department", "faculty")
    search_fields = ("email", "full_name", "course_section")
    inlines = (EvaluationAnswerInline,)


@admin.register(EvaluationAnswer)
class EvaluationAnswerAdmin(admin.ModelAdmin):
    list_display = ("evaluation", "questionnaire", "rating")
    list_filter = ("rating",)
    search_fields = ("evaluation__email",)


@admin.register(DraftEvaluation)
class DraftEvaluationAdmin(admin.ModelAdmin):
    list_display = ("email", "updated_at")
    search_fields = ("email",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "method", "endpoint",
                    "response_status", "ip_address")
    list_filter = ("method", "response_status")
    search_fields = ("endpoint", "ip_address", "user__username")
    readonly_fields = ("timestamp",)


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "ip_address", "visited_page")
    search_fields = ("visited_page", "ip_address")
    readonly_fields = ("timestamp",)


@admin.register(RecentActivity)
class RecentActivityAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "activity")
    search_fields = ("activity", "user__username")
    readonly_fields = ("timestamp",)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "username", "ip_address")
    list_filter = ("ip_address",)
    search_fields = ("username", "ip_address")
    readonly_fields = ("timestamp",)
    date_hierarchy = "timestamp"
