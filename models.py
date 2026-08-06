from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

class UserRole(models.TextChoices):
    ADMIN = "admin", "Administrator"
    STAFF = "staff", "Faculty / Staff"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class Rating(models.IntegerChoices):
    VERY_DISSATISFIED = 1, "1 – Very Dissatisfied"
    DISSATISFIED = 2, "2 – Dissatisfied"
    NEUTRAL = 3, "3 – Neutral"
    SATISFIED = 4, "4 – Satisfied"
    VERY_SATISFIED = 5, "5 – Very Satisfied"


class HttpMethod(models.TextChoices):
    GET = "GET", "GET"
    POST = "POST", "POST"


def profile_image_upload_to(instance: "UserProfile", filename: str) -> str:
    return f"profile_images/{instance.user_id}/{filename}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=16,
        choices=UserRole.choices,
        default=UserRole.STAFF,
        db_index=True,
    )
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True,
    )
    department = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    profile_image = models.ImageField(
        upload_to=profile_image_upload_to,
        blank=True,
        null=True,
    )
    temp_password = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__username",)
        verbose_name = "User profile"
        verbose_name_plural = "User profiles"

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_staff_member(self) -> bool:
        return self.role == UserRole.STAFF

    def display_name(self) -> str:
        return self.full_name or self.user.get_full_name() or self.user.username

    def __str__(self) -> str:
        return f"{self.user.username} ({self.get_role_display()})"


class Department(models.Model):
    department_name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("department_name",)
        verbose_name_plural = "Departments"

    def __str__(self) -> str:
        return self.department_name

class Questionnaire(models.Model):
    question = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return self.question

class Evaluation(models.Model):
    email = models.EmailField(db_index=True)
    full_name = models.CharField(max_length=150, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations",
    )
    course_section = models.CharField(max_length=50, blank=True)
    comments = models.TextField(blank=True, default="")
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations_received",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("faculty", "created_at")),
            models.Index(fields=("department", "created_at")),
        ]

    def __str__(self) -> str:
        return f"Evaluation #{self.pk} – {self.email}"

    @property
    def average_rating(self) -> float:
        values = self.answers.values_list("rating", flat=True)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def receipt_code(self) -> str:
        return f"FT-{self.pk:06d}"


class EvaluationAnswer(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.PROTECT,
        related_name="answers",
    )
    rating = models.PositiveSmallIntegerField(choices=Rating.choices)

    class Meta:
        unique_together = (("evaluation", "questionnaire"),)
        ordering = ("questionnaire__id",)

    def __str__(self) -> str:
        return f"{self.evaluation_id} → Q{self.questionnaire_id} = {self.rating}"

class DraftEvaluation(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    saved_progress = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Draft evaluations"

    def __str__(self) -> str:
        return f"Draft({self.email})"

class ActivityLog(models.Model):
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    method = models.CharField(max_length=8, choices=HttpMethod.choices)
    endpoint = models.CharField(max_length=255)
    response_status = models.PositiveSmallIntegerField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=("user", "timestamp")),
            models.Index(fields=("endpoint", "timestamp")),
        ]

    def __str__(self) -> str:
        return f"{self.method} {self.endpoint} ({self.response_status})"


class VisitorLog(models.Model):
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    visited_page = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-timestamp",)
        verbose_name_plural = "Visitor logs"

    def __str__(self) -> str:
        return f"{self.ip_address} → {self.visited_page}"


class RecentActivity(models.Model):
    activity = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recent_activities",
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-timestamp",)
        verbose_name_plural = "Recent activities"

    def __str__(self) -> str:
        return self.activity

class LoginAttempt(models.Model):
    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-timestamp",)
        verbose_name = "Failed login attempt"
        verbose_name_plural = "Failed login attempts"
        indexes = [
            models.Index(fields=("ip_address", "timestamp")),
            models.Index(fields=("username", "timestamp")),
        ]

    def __str__(self) -> str:
        return f"{self.username} from {self.ip_address or '?'} @ {self.timestamp:%Y-%m-%d %H:%M}"

def get_user_profile(user) -> UserProfile | None:
    if user is None or not user.is_authenticated:
        return None
    return getattr(user, "profile", None)
