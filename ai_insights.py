from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from statistics import mean

from django.db.models import Avg
from django.utils import timezone

from .analytics import (
    faculty_summary,
    performance_band,
    performance_label,
)
from .models import Department, EvaluationAnswer, UserProfile



_STRENGTHS_HIGH_SATISFACTION = (
    "Strong communication skills.",
    "High classroom engagement.",
    "Excellent responsiveness to students.",
    "Well-organised course delivery.",
    "Clear and fair assessment standards.",
)

_STRENGTHS_BALANCED = (
    "Consistent teaching quality.",
    "Reliable presence and punctuality.",
    "Reasonable responsiveness.",
)

_WEAKNESSES_LOW = (
    "Low student satisfaction.",
    "Inconsistent evaluation scores.",
    "Poor consultation availability.",
    "Limited student engagement.",
    "Communication gaps with learners.",
)

_RECOMMENDATIONS = {
    "excellent": (
        "Mentor junior faculty.",
        "Lead teaching workshops.",
        "Maintain the current quality bar.",
    ),
    "very_good": (
        "Attend a public-speaking refresher.",
        "Solicit detailed student feedback for finer improvements.",
    ),
    "good": (
        "Hold a one-on-one review with the department head.",
        "Diversify classroom activities.",
    ),
    "fair": (
        "Attend teaching workshops.",
        "Increase student engagement activities.",
        "Schedule weekly office hours.",
    ),
    "poor": (
        "Pair with a senior mentor.",
        "Complete a teaching methodology course.",
        "Implement student feedback in next semester planning.",
    ),
}


@dataclass
class Insight:
    faculty_id: int
    full_name: str
    department: str
    percentage: float
    label: str
    band: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    executive_summary: str = ""
    rating_trend: list[dict] = field(default_factory=list)
    distribution: dict = field(default_factory=dict)
    total_evaluations: int = 0

    def to_dict(self) -> dict:
        return {
            "faculty_id": self.faculty_id,
            "full_name": self.full_name,
            "department": self.department,
            "percentage": round(self.percentage, 1),
            "label": self.label,
            "band": self.band,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "executive_summary": self.executive_summary,
            "rating_trend": self.rating_trend,
            "distribution": self.distribution,
            "total_evaluations": self.total_evaluations,
        }


def analyse_faculty(profile: UserProfile) -> dict:
    summary = faculty_summary(profile)
    distribution = summary["distribution"]
    total = sum(distribution.values()) or 1
    pct = summary["percentage"]
    band = performance_band(pct)
    label = performance_label(pct)

    four_five = distribution[4] + distribution[5]
    one_two = distribution[1] + distribution[2]

    strengths = list(_STRENGTHS_HIGH_SATISFACTION) if (four_five / total) >= 0.7 \
        else list(_STRENGTHS_BALANCED) if (four_five / total) >= 0.5 \
        else []
    weaknesses = list(_WEAKNESSES_LOW) if (one_two / total) >= 0.3 else []

    recs = list(_RECOMMENDATIONS.get(band, ()))

    summary_text = (
        f"{summary['full_name']} currently sits in the {label} band with a "
        f"{pct:.1f}% satisfaction rating from {summary['total_evaluations']} "
        f"evaluations. {'Continue the strong practices.' if pct >= 75 else 'Targeted improvements recommended.'}"
    )

    insight = Insight(
        faculty_id=summary["faculty_id"],
        full_name=summary["full_name"],
        department=summary["department"],
        percentage=pct,
        label=label,
        band=band,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recs,
        executive_summary=summary_text,
        rating_trend=_rating_trend(profile),
        distribution=distribution,
        total_evaluations=summary["total_evaluations"],
    )
    return insight.to_dict()


def analyse_all_faculty(department: Department | None = None,
                       search: str = "") -> list[dict]:
    qs = UserProfile.objects.filter(role="staff").select_related("user", "department")
    if department:
        qs = qs.filter(department=department)
    if search:
        qs = qs.filter(user__username__icontains=search) | qs.filter(full_name__icontains=search)
    return [analyse_faculty(p) for p in qs]


def highest_and_lowest(department: Department | None = None) -> dict:
    rows = analyse_all_faculty(department=department)
    if not rows:
        return {
            "highest": None, "lowest": None,
            "most_improved": None, "needs_improvement": None,
        }
    sorted_rows = sorted(rows, key=lambda r: r["percentage"], reverse=True)
    highest = sorted_rows[0]
    lowest = sorted_rows[-1]

    def _delta(faculty_id: int) -> float:
        now = timezone.now()
        recent = EvaluationAnswer.objects.filter(
            evaluation__faculty_id=faculty_id,
            evaluation__created_at__gte=now - timedelta(days=30),
        ).aggregate(v=Avg("rating"))["v"] or 0
        previous = EvaluationAnswer.objects.filter(
            evaluation__faculty_id=faculty_id,
            evaluation__created_at__gte=now - timedelta(days=60),
            evaluation__created_at__lt=now - timedelta(days=30),
        ).aggregate(v=Avg("rating"))["v"] or 0
        return recent - previous

    deltas = [(row, _delta(row["faculty_id"])) for row in rows]
    most_improved = max(deltas, key=lambda t: t[1])[0]
    return {
        "highest": highest,
        "lowest": lowest,
        "most_improved": most_improved,
        "needs_improvement": lowest,
    }


def _rating_trend(profile: UserProfile, months: int = 6) -> list[dict]:
    now = timezone.now()
    points = []
    for offset in range(months - 1, -1, -1):
        start = (now - timedelta(days=30 * (offset + 1)))
        end = (now - timedelta(days=30 * offset))
        avg = EvaluationAnswer.objects.filter(
            evaluation__faculty=profile.user,
            evaluation__created_at__gte=start,
            evaluation__created_at__lt=end,
        ).aggregate(v=Avg("rating"))["v"] or 0
        points.append({
            "label": start.strftime("%b %Y"),
            "average": round(avg, 2),
        })
    return points

def predict_next_period(profile: UserProfile, periods: int = 3) -> dict:
    trend = _rating_trend(profile, months=6)
    if not trend:
        return {"labels": [], "history": [], "forecast": [],
                "delta": 0.0, "confidence": "Low"}

    values = [row["average"] for row in trend]
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    avg_delta = mean(deltas) if deltas else 0
    last = values[-1]

    future_labels = []
    future_values = []
    for i in range(1, periods + 1):
        future_labels.append(f"Month +{i}")
        future_values.append(round(last + avg_delta * i, 2))

    confidence = "High" if len(values) >= 5 else "Medium" if len(values) >= 3 else "Low"
    return {
        "labels": [row["label"] for row in trend] + future_labels,
        "history": values,
        "forecast": [None] * len(values) + future_values,
        "delta": round(avg_delta, 3),
        "confidence": confidence,
    }


def department_forecast(department: Department, periods: int = 3) -> dict:
    member_ids = list(department.members.filter(role="staff").values_list("user_id", flat=True))
    if not member_ids:
        return {"labels": [], "history": [], "forecast": [], "delta": 0.0, "confidence": "Low"}

    now = timezone.now()
    history = []
    for offset in range(5, -1, -1):
        start = now - timedelta(days=30 * (offset + 1))
        end = now - timedelta(days=30 * offset)
        avg = EvaluationAnswer.objects.filter(
            evaluation__faculty_id__in=member_ids,
            evaluation__created_at__gte=start,
            evaluation__created_at__lt=end,
        ).aggregate(v=Avg("rating"))["v"] or 0
        history.append(round(avg, 2))

    deltas = [history[i] - history[i - 1] for i in range(1, len(history))]
    avg_delta = mean(deltas) if deltas else 0
    forecast = [round((history[-1] or 0) + avg_delta * i, 2) for i in range(1, periods + 1)]

    return {
        "labels": [f"M-{i}" for i in range(len(history) - 1, -1, -1)] + [f"M+{i}" for i in range(1, periods + 1)],
        "history": history + [None] * periods,
        "forecast": [None] * len(history) + forecast,
        "delta": round(avg_delta, 3),
    }


def system_wide_forecast() -> dict:
    now = timezone.now()
    history = []
    for offset in range(5, -1, -1):
        start = now - timedelta(days=30 * (offset + 1))
        end = now - timedelta(days=30 * offset)
        avg = EvaluationAnswer.objects.filter(
            evaluation__created_at__gte=start,
            evaluation__created_at__lt=end,
        ).aggregate(v=Avg("rating"))["v"] or 0
        history.append((avg / 5) * 100 if avg else 0)
    deltas = [history[i] - history[i - 1] for i in range(1, len(history))]
    avg_delta = mean(deltas) if deltas else 0
    predicted = (history[-1] or 0) + avg_delta
    return {
        "history": [round(v, 1) for v in history],
        "predicted": round(predicted, 1),
        "delta": round(avg_delta, 2),
    }
