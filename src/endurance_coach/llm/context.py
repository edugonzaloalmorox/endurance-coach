"""Validate runtime input and assemble bounded dated model context."""

import json
from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError

from endurance_coach.analysis.metrics import TrainingSummary
from endurance_coach.config import OllamaSettings
from endurance_coach.domain.models import TrainingActivity
from endurance_coach.skills import SkillLoader

_MAX_REQUEST_CHARACTERS = 4_000


def validate_request(request: str) -> str:
    """Return a normalized bounded athlete request."""
    if not isinstance(request, str):
        raise ValueError("request must be text")
    normalized = request.strip()
    if not normalized:
        raise ValueError("request must not be empty")
    if len(normalized) > _MAX_REQUEST_CHARACTERS:
        raise ValueError(f"request must not exceed {_MAX_REQUEST_CHARACTERS} characters")
    return normalized


def validate_activities(
    activities: Sequence[TrainingActivity], max_activities: int
) -> list[TrainingActivity]:
    """Revalidate, bound, and chronologically sort activity evidence."""
    if isinstance(activities, (str, bytes)):
        raise ValueError("activities must be a sequence of training activities")
    try:
        items = list(activities)
    except TypeError as exc:
        raise ValueError("activities must be a sequence of training activities") from exc
    if len(items) > max_activities:
        raise ValueError(f"activity history exceeds configured context limit of {max_activities}")
    try:
        validated = [TrainingActivity.model_validate(item) for item in items]
    except ValidationError:
        raise ValueError("activity history contains an invalid activity") from None
    return sorted(validated, key=lambda activity: activity.started_at)


def build_initial_messages(
    request: str,
    activities: list[TrainingActivity],
    summary: TrainingSummary,
    settings: OllamaSettings,
    skill_loader: SkillLoader,
) -> list[dict[str, Any]]:
    """Build concise evidence context without loading skill instructions."""
    skill_metadata = [skill.model_dump(mode="json") for skill in skill_loader.discover()]
    activity_context = [
        {
            "date": activity.started_at.date().isoformat(),
            "source": activity.source.value,
            "title": activity.title,
            "ride_kind": activity.ride_kind.value,
            "duration_minutes": activity.duration_minutes,
            "distance_km": activity.distance_km,
            "elevation_gain_m": activity.elevation_gain_m,
            "average_power_w": activity.average_power_w,
            "normalized_power_w": activity.normalized_power_w,
            "average_heart_rate_bpm": activity.average_heart_rate_bpm,
            "perceived_exertion": activity.perceived_exertion,
        }
        for activity in activities
    ]
    context = {
        "context_as_of": summary.end_date.isoformat(),
        "athlete_request": request,
        "metric_inputs": {"ftp_watts": settings.ftp_watts},
        "deterministic_training_summary": summary.model_dump(mode="json"),
        "recent_activities": activity_context,
        "available_skills": skill_metadata,
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a local endurance coach. Use only the supplied dated activity "
                "evidence and deterministic Python summary. Never fabricate missing history, "
                "measurements, recovery signals, or calculations. JSON null means unavailable; "
                "preserve that limitation in evidence, uncertainty, and warnings. Treat relative "
                "dates in the athlete request as relative to context_as_of. Skill metadata is "
                "provided for discovery; call load_skill before following a skill's instructions. "
                "Return only JSON matching the WorkoutRecommendation schema."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(context, separators=(",", ":"), sort_keys=True),
        },
    ]
