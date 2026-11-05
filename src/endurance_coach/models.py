"""Validated data exchanged by the coach's boundaries."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

type JsonValue = (
    str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
)


class StrictModel(BaseModel):
    """Base contract that rejects misspelled or unexpected fields."""

    model_config = ConfigDict(extra="forbid")


class RideKind(StrEnum):
    """Supported cycling workout intensity categories."""

    RECOVERY = "recovery"
    ENDURANCE = "endurance"
    TEMPO = "tempo"
    INTERVALS = "intervals"
    LONG_RIDE = "long_ride"


class ActivitySource(StrEnum):
    """Systems from which a training activity can originate."""

    SYNTHETIC = "synthetic"
    INTERVALS_ICU = "intervals_icu"
    COROS = "coros"
    MANUAL = "manual"


class TrainingActivity(StrictModel):
    """A completed cycling activity with explicit units and source provenance."""

    activity_id: str = Field(min_length=1, description="Stable internal activity identifier.")
    source: ActivitySource = Field(description="System that supplied the activity record.")
    source_activity_id: str = Field(
        min_length=1,
        description="Activity identifier assigned by the source system.",
    )
    started_at: datetime = Field(description="Timezone-aware activity start date and time.")
    title: str = Field(min_length=1, description="Human-readable activity title.")
    ride_kind: RideKind
    duration_minutes: int = Field(gt=0, le=1_440, description="Elapsed duration in minutes.")
    distance_km: float = Field(gt=0, description="Distance in kilometres.")
    elevation_gain_m: int = Field(ge=0, description="Accumulated elevation gain in metres.")
    average_power_w: int | None = Field(
        default=None,
        gt=0,
        description="Average power in watts, or null when unavailable.",
    )
    normalized_power_w: int | None = Field(
        default=None,
        gt=0,
        description="Normalized power in watts, or null when unavailable.",
    )
    average_heart_rate_bpm: int | None = Field(
        default=None,
        ge=40,
        le=230,
        description="Average heart rate in beats per minute, or null when unavailable.",
    )
    perceived_exertion: int = Field(
        ge=1,
        le=10,
        description="Subjective session intensity on a 1–10 scale.",
    )

    @model_validator(mode="after")
    def activity_values_are_consistent(self) -> "TrainingActivity":
        """Require an unambiguous start time and internally consistent power."""
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("started_at must include a timezone offset")
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


class ToolDefinition(StrictModel):
    """A tool exposed to the model with a JSON object input schema."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    description: str = Field(min_length=1, max_length=1_024)
    input_schema: dict[str, JsonValue]

    @model_validator(mode="after")
    def input_schema_describes_an_object(self) -> "ToolDefinition":
        """Reject schemas that cannot describe a named-argument payload."""
        if self.input_schema.get("type") != "object":
            raise ValueError("input_schema type must be object")
        return self


class ToolRequest(StrictModel):
    """One validated tool call requested by the model."""

    tool_call_id: str = Field(min_length=1)
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    arguments: dict[str, JsonValue]


class ToolResult(StrictModel):
    """A tool result correlated with the request that produced it."""

    tool_call_id: str = Field(min_length=1)
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    content: JsonValue
    is_error: bool = False


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
