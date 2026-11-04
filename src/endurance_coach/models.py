"""Validated data exchanged by the coach's boundaries."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base contract that rejects misspelled or unexpected fields."""

    model_config = ConfigDict(extra="forbid")


class RideKind(StrEnum):
    RECOVERY = "recovery"
    ENDURANCE = "endurance"
    TEMPO = "tempo"
    INTERVALS = "intervals"
    LONG_RIDE = "long_ride"


class TrainingActivity(StrictModel):
    """A completed cycling activity; power and heart-rate data are optional."""

    activity_id: str = Field(min_length=1)
    started_at: datetime
    title: str = Field(min_length=1)
    ride_kind: RideKind
    duration_minutes: int = Field(gt=0, le=1_440)
    distance_km: float = Field(gt=0)
    elevation_gain_m: int = Field(ge=0)
    average_power_w: int | None = Field(default=None, gt=0)
    normalized_power_w: int | None = Field(default=None, gt=0)
    average_heart_rate_bpm: int | None = Field(default=None, ge=40, le=230)
    perceived_exertion: int = Field(ge=1, le=10)

    @model_validator(mode="after")
    def normalized_power_is_not_below_average(self) -> "TrainingActivity":
        if (
            self.average_power_w is not None
            and self.normalized_power_w is not None
            and self.normalized_power_w < self.average_power_w
        ):
            raise ValueError("normalized_power_w must be at least average_power_w")
        return self


class SkillMetadata(StrictModel):
    """Small skill representation suitable for startup-time discovery."""

    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    description: str = Field(min_length=1, max_length=1_024)


class LoadedSkill(SkillMetadata):
    """A skill after its full instructions have been requested."""

    instructions: str = Field(min_length=1)


class WorkoutStep(StrictModel):
    name: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0)
    intensity: str = Field(min_length=1)


class WorkoutRecommendation(StrictModel):
    """Structured output required from the future agent runtime."""

    workout_date: date
    title: str = Field(min_length=1)
    ride_kind: RideKind
    duration_minutes: int = Field(gt=0, le=360)
    rationale: str = Field(min_length=1)
    steps: list[WorkoutStep] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    source_skill: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    @model_validator(mode="after")
    def steps_match_total_duration(self) -> "WorkoutRecommendation":
        step_total = sum(step.duration_minutes for step in self.steps)
        if step_total != self.duration_minutes:
            raise ValueError("step durations must sum to duration_minutes")
        return self
