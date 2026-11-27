"""Pure, deterministic cycling training metrics."""

from collections.abc import Iterable
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from endurance_coach.domain.models import ActivitySource, TrainingActivity


class MissingTrainingDataError(ValueError):
    """Raised when a summary cannot be calculated without activities."""


class LoadCompleteness(StrEnum):
    """Whether a load measure covers all activities in its dated window."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class LoadSourceCount(BaseModel):
    """Count of activities from one source included in a load measure."""

    model_config = ConfigDict(extra="forbid")

    source: ActivitySource
    activity_count: int = Field(gt=0)


class TrainingLoadMeasure(BaseModel):
    """One deterministic load result with coverage and provenance."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    value: float | None = Field(default=None, ge=0)
    unit: str = Field(min_length=1)
    calculation: str = Field(min_length=1)
    sample_size: int = Field(ge=0)
    missing_activity_count: int = Field(ge=0)
    completeness: LoadCompleteness
    sources: list[LoadSourceCount]
    limitations: list[str]

    @model_validator(mode="after")
    def availability_is_consistent(self) -> "TrainingLoadMeasure":
        """Keep nullability and coverage status internally consistent."""
        if self.completeness is LoadCompleteness.UNAVAILABLE:
            if self.value is not None or self.sample_size != 0 or self.sources:
                raise ValueError("unavailable load must have no value, samples, or sources")
        elif self.value is None or self.sample_size == 0:
            raise ValueError("available load must have a value and at least one sample")
        if sum(item.activity_count for item in self.sources) != self.sample_size:
            raise ValueError("source activity counts must equal sample_size")
        return self


class TrainingLoadReport(BaseModel):
    """Deterministic load measures for an explicit activity window."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    activity_count: int = Field(gt=0)
    ftp_watts: int = Field(gt=0)
    power_tss: TrainingLoadMeasure
    session_rpe_load: TrainingLoadMeasure

    @model_validator(mode="after")
    def coverage_matches_activity_window(self) -> "TrainingLoadReport":
        """Require every measure to account for every activity in the report."""
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot precede start_date")
        for measure in (self.power_tss, self.session_rpe_load):
            if measure.sample_size + measure.missing_activity_count != self.activity_count:
                raise ValueError("load measure coverage must equal activity_count")
            expected = (
                LoadCompleteness.UNAVAILABLE
                if measure.sample_size == 0
                else LoadCompleteness.COMPLETE
                if measure.missing_activity_count == 0
                else LoadCompleteness.PARTIAL
            )
            if measure.completeness is not expected:
                raise ValueError("load measure completeness does not match its coverage")
        return self


class TrainingSummary(BaseModel):
    """Deterministic aggregate for a dated training window."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    activity_count: int = Field(gt=0)
    total_duration_minutes: int = Field(gt=0)
    total_distance_km: float = Field(ge=0)
    total_elevation_gain_m: int = Field(ge=0)
    total_tss: float | None
    activities_missing_power: int = Field(ge=0)
    activities_missing_distance: int = Field(ge=0)
    activities_missing_elevation: int = Field(ge=0)
    activities_missing_perceived_exertion: int = Field(ge=0)
    training_load: TrainingLoadReport


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


def session_rpe_load(activity: TrainingActivity) -> int | None:
    """Return duration multiplied by session RPE, or None when RPE is absent."""
    if activity.perceived_exertion is None:
        return None
    return activity.duration_minutes * activity.perceived_exertion


def _source_counts(
    activities: list[TrainingActivity], values: list[float | int | None]
) -> list[LoadSourceCount]:
    counts: dict[ActivitySource, int] = {}
    for activity, value in zip(activities, values, strict=True):
        if value is not None:
            counts[activity.source] = counts.get(activity.source, 0) + 1
    return [
        LoadSourceCount(source=source, activity_count=count)
        for source, count in sorted(counts.items(), key=lambda item: item[0].value)
    ]


def _load_measure(
    *,
    name: str,
    unit: str,
    calculation: str,
    missing_field: str,
    activities: list[TrainingActivity],
    values: list[float | int | None],
) -> TrainingLoadMeasure:
    available = [value for value in values if value is not None]
    missing_count = len(values) - len(available)
    if not available:
        completeness = LoadCompleteness.UNAVAILABLE
        value = None
        limitations = [
            f"All {len(values)} activities lack {missing_field}; this load is unavailable."
        ]
    else:
        completeness = (
            LoadCompleteness.COMPLETE
            if missing_count == 0
            else LoadCompleteness.PARTIAL
        )
        value = round(sum(available), 1)
        limitations = (
            []
            if missing_count == 0
            else [
                f"{missing_count} of {len(values)} activities lack {missing_field} and are "
                "excluded from this load."
            ]
        )
    return TrainingLoadMeasure(
        name=name,
        value=value,
        unit=unit,
        calculation=calculation,
        sample_size=len(available),
        missing_activity_count=missing_count,
        completeness=completeness,
        sources=_source_counts(activities, values),
        limitations=limitations,
    )


def calculate_training_load(
    activities: Iterable[TrainingActivity], ftp_watts: int
) -> TrainingLoadReport:
    """Calculate supported load measures without imputing missing inputs.

    Args:
        activities: Validated activities in the requested analysis window.
        ftp_watts: Positive functional threshold power used for power-based TSS.

    Returns:
        Dated power and perceived-exertion load measures with sample coverage and
        source-system provenance.

    Raises:
        MissingTrainingDataError: If no activities are supplied.
        ValueError: If ``ftp_watts`` is not positive.
    """
    items = list(activities)
    if not items:
        raise MissingTrainingDataError("at least one training activity is required")
    if ftp_watts <= 0:
        raise ValueError("ftp_watts must be positive")

    power_scores = [training_stress_score(activity, ftp_watts) for activity in items]
    rpe_scores = [session_rpe_load(activity) for activity in items]
    dates = [activity.started_at.date() for activity in items]
    return TrainingLoadReport(
        start_date=min(dates),
        end_date=max(dates),
        activity_count=len(items),
        ftp_watts=ftp_watts,
        power_tss=_load_measure(
            name="power_tss",
            unit="TSS",
            calculation="duration_hours * (normalized_power_w / ftp_watts)^2 * 100",
            missing_field="normalized power",
            activities=items,
            values=power_scores,
        ),
        session_rpe_load=_load_measure(
            name="session_rpe_load",
            unit="arbitrary units",
            calculation="duration_minutes * perceived_exertion",
            missing_field="perceived exertion",
            activities=items,
            values=rpe_scores,
        ),
    )


def summarize_training(activities: Iterable[TrainingActivity], ftp_watts: int) -> TrainingSummary:
    """Aggregate activities while explicitly counting missing power data."""
    items = list(activities)
    if not items:
        raise MissingTrainingDataError("at least one training activity is required")

    load = calculate_training_load(items, ftp_watts)
    dates = [activity.started_at.date() for activity in items]
    return TrainingSummary(
        start_date=min(dates),
        end_date=max(dates),
        activity_count=len(items),
        total_duration_minutes=sum(activity.duration_minutes for activity in items),
        total_distance_km=round(
            sum(activity.distance_km for activity in items if activity.distance_km is not None),
            1,
        ),
        total_elevation_gain_m=sum(
            activity.elevation_gain_m
            for activity in items
            if activity.elevation_gain_m is not None
        ),
        total_tss=load.power_tss.value,
        activities_missing_power=load.power_tss.missing_activity_count,
        activities_missing_distance=sum(activity.distance_km is None for activity in items),
        activities_missing_elevation=sum(
            activity.elevation_gain_m is None for activity in items
        ),
        activities_missing_perceived_exertion=sum(
            activity.perceived_exertion is None for activity in items
        ),
        training_load=load,
    )
