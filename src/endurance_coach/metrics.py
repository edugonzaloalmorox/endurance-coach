"""Pure, deterministic cycling training metrics."""

from collections.abc import Iterable
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from endurance_coach.models import TrainingActivity


class MissingTrainingDataError(ValueError):
    """Raised when a summary cannot be calculated without activities."""


class TrainingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    activity_count: int = Field(gt=0)
    total_duration_minutes: int = Field(gt=0)
    total_distance_km: float = Field(gt=0)
    total_elevation_gain_m: int = Field(ge=0)
    total_tss: float
    activities_missing_power: int = Field(ge=0)


def intensity_factor(activity: TrainingActivity, ftp_watts: int) -> float | None:
    """Return normalized power divided by FTP, or None when power is absent."""
    if ftp_watts <= 0:
        raise ValueError("ftp_watts must be positive")
    if activity.normalized_power_w is None:
        return None
    return round(activity.normalized_power_w / ftp_watts, 3)


def training_stress_score(activity: TrainingActivity, ftp_watts: int) -> float | None:
    """Calculate power-based TSS, or None when normalized power is absent."""
    factor = intensity_factor(activity, ftp_watts)
    if factor is None:
        return None
    duration_hours = activity.duration_minutes / 60
    return round(duration_hours * factor**2 * 100, 1)


def summarize_training(activities: Iterable[TrainingActivity], ftp_watts: int) -> TrainingSummary:
    """Aggregate activities while explicitly counting missing power data."""
    items = list(activities)
    if not items:
        raise MissingTrainingDataError("at least one training activity is required")

    scores = [training_stress_score(activity, ftp_watts) for activity in items]
    dates = [activity.started_at.date() for activity in items]
    return TrainingSummary(
        start_date=min(dates),
        end_date=max(dates),
        activity_count=len(items),
        total_duration_minutes=sum(activity.duration_minutes for activity in items),
        total_distance_km=round(sum(activity.distance_km for activity in items), 1),
        total_elevation_gain_m=sum(activity.elevation_gain_m for activity in items),
        total_tss=round(sum(score for score in scores if score is not None), 1),
        activities_missing_power=sum(score is None for score in scores),
    )
