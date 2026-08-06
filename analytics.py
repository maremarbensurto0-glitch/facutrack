from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable

from django.db.models import Avg, Count
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from .models import (
    Department,
    Evaluation,
    EvaluationAnswer,
    UserProfile,
    VisitorLog,
)


PERFORMANCE_BANDS = (
    ("excellent", "Excellent", 95, 100),
    ("very_good", "Very Good", 85, 94.99),
    ("good", "Good", 75, 84.99),
    ("fair", "Fair", 60, 74.99),
    ("poor", "Poor", 0, 59.99),
)


def performance_band(percentage: float) -> str:
    for key, _label, low, high in PERFORMANCE_BANDS:
        if low <= percentage <= high:
            return key
    return "poor"


def performance_label(percentage: float) -> str:
    for _key, label, low, high in PERFORMANCE_BANDS:
        if low <= percentage <= high:
            return label
    return "Poor"

DATE_FILTERS = {
    "1y":  ("1 Year",   timedelta(days=365)),
    "6m":  ("6 Months", timedelta(days=180)),
    "3m":  ("3 Months", timedelta(days=90)),
    "1m":  ("1 Month",  timedelta(days=30)),
    "15d": ("15 Days",  timedelta(days=15)),
    "7d":  ("7 Days",   timedelta(days=7)),
    "3d":  ("3 Days",   timedelta(days=3)),
    "1d":  ("Today",    timedelta(days=1)),
    "all": ("All Time", None),
}


def resolve_date_filter(key: str | None) -> tuple[str, datetime | None]:
    if not key or key not in DATE_FILTERS:
        key = "all"
    label, delta = DATE_FILTERS[key]
    start = timezone.now() - delta if delta else None
    return key, start

@dataclass
class DashboardKPIs:
    total_faculty: int = 0
    total_departments: int = 0
    overall_rating_percent: float = 0.0
    daily_visitors: int = 0

    def as_dict(self) -> dict:
        return {
            "total_faculty": self.total_faculty,
            "total_departments": self.total_departments,
            "overall_rating_percent": round(self.overall_rating_percent, 1),
            "daily_visitors": self.daily_visitors,
        }


def compute_dashboard_kpis() -> DashboardKPIs:
    total_faculty = UserProfile.objects.filter(role="staff").count()
    total_departments = Department.objects.count()
    avg = EvaluationAnswer.objects.aggregate(v=Avg("rating"))["v"] or 0
    overall_rating_percent = round((avg / 5) * 100, 1) if avg else 0
    since = timezone.now() - timedelta(days=1)
    daily_visitors = VisitorLog.objects.filter(timestamp__gte=since).count()
    return DashboardKPIs(
        total_faculty=total_faculty,
        total_departments=total_departments,
        overall_rating_percent=overall_rating_percent,
        daily_visitors=daily_visitors,
    )


def evaluations_timeseries(start=None, end=None, bucket: str = "day") -> list[dict]:
    qs = Evaluation.objects.all()
    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end)

    if bucket == "month":
        grouped = (
            qs.annotate(b=TruncMonth("created_at"))
              .values("b")
              .annotate(c=Count("id"))
              .order_by("b")
        )
        out = []
        for row in grouped:
            month_avg = (
                EvaluationAnswer.objects
                .filter(evaluation__created_at__year=row["b"].year,
                        evaluation__created_at__month=row["b"].month)
                .aggregate(v=Avg("rating"))["v"] or 0
            )
            out.append({
                "label": row["b"].strftime("%b %Y"),
                "count": row["c"],
                "average": round(month_avg, 2),
            })
        return out

    grouped = (
        qs.annotate(b=TruncDate("created_at"))
          .values("b")
          .annotate(c=Count("id"))
          .order_by("b")
    )
    out = []
    for row in grouped:
        day_avg = (
            EvaluationAnswer.objects
            .filter(evaluation__created_at__date=row["b"])
            .aggregate(v=Avg("rating"))["v"] or 0
        )
        out.append({
            "label": row["b"].strftime("%b %d"),
            "count": row["c"],
            "average": round(day_avg, 2),
        })
    return out


def visitor_timeseries(start=None) -> list[dict]:
    qs = VisitorLog.objects.all()
    if start:
        qs = qs.filter(timestamp__gte=start)
    qs = qs.annotate(d=TruncDate("timestamp")).values("d").annotate(c=Count("id")).order_by("d")
    return [{"label": row["d"].strftime("%b %d"), "count": row["c"]} for row in qs]


def evaluations_daily_counts(days: int = 14) -> list[dict]:
    today = timezone.now().date()
    buckets = []
    for offset in range(days - 1, -1, -1):
        d = today - timedelta(days=offset)
        c = Evaluation.objects.filter(created_at__date=d).count()
        buckets.append({"label": d.strftime("%b %d"), "count": c})
    return buckets

@dataclass
class FacultyScore:
    faculty_id: int
    full_name: str
    username: str
    department: str
    average: float
    percentage: float
    evaluations: int
    band: str = "poor"
    label: str = "Poor"

    def to_dict(self) -> dict:
        return {
            "faculty_id": self.faculty_id,
            "full_name": self.full_name,
            "username": self.username,
            "department": self.department,
            "average": round(self.average, 2),
            "percentage": round(self.percentage, 1),
            "evaluations": self.evaluations,
            "band": self.band,
            "label": self.label,
        }


def faculty_rankings(department: Department | None = None,
                     search: str = "") -> list[dict]:
    qs = (
        UserProfile.objects
        .filter(role="staff")
        .select_related("user", "department")
    )
    if department:
        qs = qs.filter(department=department)
    if search:
        qs = qs.filter(
            user__username__icontains=search
        ) | qs.filter(full_name__icontains=search)

    rows: list[FacultyScore] = []
    for profile in qs:
        answers = EvaluationAnswer.objects.filter(evaluation__faculty=profile.user)
        agg = answers.aggregate(v=Avg("rating"))
        avg = agg["v"] or 0
        pct = (avg / 5) * 100 if avg else 0
        eval_count = Evaluation.objects.filter(faculty=profile.user).count()
        rows.append(FacultyScore(
            faculty_id=profile.user_id,
            full_name=profile.display_name(),
            username=profile.user.username,
            department=profile.department.department_name if profile.department else "—",
            average=avg,
            percentage=pct,
            evaluations=eval_count,
            band=performance_band(pct),
            label=performance_label(pct),
        ))
    rows.sort(key=lambda r: r.percentage, reverse=True)
    return [r.to_dict() for r in rows]


def department_rankings() -> list[dict]:
    rows = []
    for dept in Department.objects.all():
        members = UserProfile.objects.filter(role="staff", department=dept)
        member_ids = list(members.values_list("user_id", flat=True))
        agg = EvaluationAnswer.objects.filter(evaluation__faculty_id__in=member_ids) \
                                     .aggregate(v=Avg("rating"))
        avg = agg["v"] or 0
        pct = (avg / 5) * 100 if avg else 0
        eval_count = Evaluation.objects.filter(faculty_id__in=member_ids).count()
        rows.append({
            "department_id": dept.id,
            "department_name": dept.department_name,
            "faculty_count": members.count(),
            "average": round(avg, 2),
            "percentage": round(pct, 1),
            "evaluations": eval_count,
            "band": performance_band(pct),
            "label": performance_label(pct),
        })
    rows.sort(key=lambda r: r["percentage"], reverse=True)
    return rows

def rating_distribution(faculty_user=None) -> dict:
    qs = EvaluationAnswer.objects.all()
    if faculty_user is not None:
        qs = qs.filter(evaluation__faculty=faculty_user)
    agg = qs.values("rating").annotate(c=Count("id"))
    distribution = {i: 0 for i in range(1, 6)}
    for row in agg:
        distribution[row["rating"]] = row["c"]
    return distribution

@dataclass
class FacultySummary:
    faculty_id: int
    full_name: str
    department: str
    average: float
    percentage: float
    total_evaluations: int
    distribution: dict = field(default_factory=dict)
    band: str = "poor"
    label: str = "Poor"
    status_message: str = ""

    def to_dict(self) -> dict:
        return {
            "faculty_id": self.faculty_id,
            "full_name": self.full_name,
            "department": self.department,
            "average": round(self.average, 2),
            "percentage": round(self.percentage, 1),
            "total_evaluations": self.total_evaluations,
            "distribution": self.distribution,
            "band": self.band,
            "label": self.label,
            "status_message": self.status_message,
        }


def faculty_summary(profile: UserProfile) -> dict:
    avg_qs = EvaluationAnswer.objects.filter(evaluation__faculty=profile.user)
    agg = avg_qs.aggregate(v=Avg("rating"))
    avg = agg["v"] or 0
    pct = (avg / 5) * 100 if avg else 0
    total_evaluations = Evaluation.objects.filter(faculty=profile.user).count()
    distribution = rating_distribution(profile.user)
    one_star, five_star = distribution[1], distribution[5]
    if one_star and five_star and one_star > five_star:
        status = "Failed Performance – focus on areas of improvement."
    elif five_star > one_star:
        status = "Passed Performance – keep up the excellent work."
    else:
        status = "Steady Performance – maintain consistency."

    return FacultySummary(
        faculty_id=profile.user_id,
        full_name=profile.display_name(),
        department=profile.department.department_name if profile.department else "—",
        average=avg,
        percentage=pct,
        total_evaluations=total_evaluations,
        distribution=distribution,
        band=performance_band(pct),
        label=performance_label(pct),
        status_message=status,
    ).to_dict()
